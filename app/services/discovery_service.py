import math
from datetime import datetime, timezone

from sqlalchemy import case, func, literal

from app.extensions.db import db
from app.models.block import Block
from app.models.photo import UserPhoto
from app.models.swipe import Swipe
from app.models.user import User

# Weights for ranking score
W_RECENCY = 0.6
W_COMPLETENESS = 0.4
RECENCY_CAP_HOURS = 168  # 7 days — users inactive longer than this get score 0

# 1 degree of latitude ≈ 111.32 km
KM_PER_DEGREE = 111.32


def discover_profiles(current_user: User, page: int, per_page: int) -> dict:
    """Build and execute the discovery query.

    Returns: { profiles, page, pages, total }
    """

    # ── Stage 1: Base ──────────────────────────────────────────────
    query = User.query.filter(User.is_active.is_(True))

    # ── Stage 2: Exclusions ────────────────────────────────────────
    query = _apply_exclusions(query, current_user.id)

    # ── Stage 3: Preference filters ───────────────────────────────
    query = _apply_preference_filters(query, current_user)

    # ── Stage 4: Ranking ──────────────────────────────────────────
    #   We need the ranking_score as a column for both ordering and output,
    #   so we compute it as a SQL expression.
    recency_score = _recency_expression()
    completeness_score = _completeness_expression(current_user.id)
    ranking_expr = (literal(W_RECENCY) * recency_score +
                    literal(W_COMPLETENESS) * completeness_score)

    # Add ranking_score as a labeled column
    query = query.add_columns(ranking_expr.label('ranking_score'))

    # Deterministic ordering: score DESC, then id ASC as tiebreaker
    query = query.order_by(ranking_expr.desc(), User.id)

    # ── Stage 5: Pagination ───────────────────────────────────────
    #   Build a count query from the filtered base (before ranking columns)
    #   to avoid re-evaluating ranking expressions just for the count.
    count_query = _apply_exclusions(
        User.query.filter(User.is_active.is_(True)), current_user.id
    )
    count_query = _apply_preference_filters(count_query, current_user)
    total = count_query.count()
    pages = math.ceil(total / per_page) if per_page > 0 else 0

    rows = query.offset((page - 1) * per_page).limit(per_page).all()

    # Batch-load primary photos for all users in one query (avoid N+1)
    user_ids = [user.id for user, _ in rows]
    primary_photos = {}
    if user_ids:
        photos = (UserPhoto.query
                  .filter(UserPhoto.user_id.in_(user_ids), UserPhoto.is_primary.is_(True))
                  .all())
        primary_photos = {p.user_id: p.url for p in photos}

    profiles = [
        _serialize_profile(user, score, primary_photos.get(user.id))
        for user, score in rows
    ]

    return {
        'profiles': profiles,
        'page': page,
        'pages': pages,
        'total': total,
    }


# ── Private helpers ────────────────────────────────────────────────


def _apply_exclusions(query, current_user_id):
    """Exclude: self, swiped, blocked (both directions), incomplete profiles."""

    # Self
    query = query.filter(User.id != current_user_id)

    # Already swiped
    swiped_ids = (
        db.session.query(Swipe.target_user_id)
        .filter(Swipe.swiper_id == current_user_id)
    )
    query = query.filter(User.id.not_in(swiped_ids))

    # Blocked by me
    blocked_by_me = (
        db.session.query(Block.blocked_id)
        .filter(Block.blocker_id == current_user_id)
    )
    query = query.filter(User.id.not_in(blocked_by_me))

    # Blocked me
    blocked_me = (
        db.session.query(Block.blocker_id)
        .filter(Block.blocked_id == current_user_id)
    )
    query = query.filter(User.id.not_in(blocked_me))

    # Incomplete profiles — minimum: display_name, date_of_birth, gender
    query = query.filter(
        User.display_name != '',
        User.date_of_birth.is_not(None),
        User.gender.is_not(None),
    )

    return query


def _apply_preference_filters(query, current_user: User):
    """Filter by gender, age range, and distance based on current user prefs."""

    # Gender preference
    if current_user.looking_for and current_user.looking_for != 'everyone':
        query = query.filter(User.gender == current_user.looking_for)

    # Age range — compute age from date_of_birth
    if current_user.age_min is not None or current_user.age_max is not None:
        today = func.current_date()
        age_expr = func.date_part('year', func.age(today, User.date_of_birth))

        if current_user.age_min is not None:
            query = query.filter(age_expr >= current_user.age_min)
        if current_user.age_max is not None:
            query = query.filter(age_expr <= current_user.age_max)

    # Distance — bounding box filter (only if current user has location)
    if (current_user.latitude is not None
            and current_user.longitude is not None
            and current_user.discovery_radius_km is not None):
        lat = current_user.latitude
        lng = current_user.longitude
        radius = current_user.discovery_radius_km

        # Bounding box edges
        lat_delta = radius / KM_PER_DEGREE
        lng_delta = radius / (KM_PER_DEGREE * max(math.cos(math.radians(lat)), 0.01))

        query = query.filter(
            User.latitude.is_not(None),
            User.longitude.is_not(None),
            User.latitude.between(lat - lat_delta, lat + lat_delta),
            User.longitude.between(lng - lng_delta, lng + lng_delta),
        )

    return query


def _recency_expression():
    """SQL expression: 0.0–1.0 score based on how recently the user was active.

    1.0 = active right now, 0.0 = inactive for RECENCY_CAP_HOURS or more.
    Falls back to created_at if last_active_at is NULL.
    """
    now = func.now()
    active_at = func.coalesce(User.last_active_at, User.created_at)
    hours_ago = func.extract('epoch', now - active_at) / 3600.0

    return case(
        (hours_ago >= RECENCY_CAP_HOURS, literal(0.0)),
        else_=literal(1.0) - hours_ago / literal(float(RECENCY_CAP_HOURS)),
    )


def _completeness_expression(current_user_id):
    """SQL expression: 0.0–1.0 score based on profile completeness.

    Factors (each worth 0.25):
      - bio is not null/empty
      - has at least 1 photo
      - looking_for is set
      - date_of_birth is set (always true after exclusions, but scored anyway)
    """
    bio_score = case((User.bio.is_not(None) & (User.bio != ''), literal(0.25)), else_=literal(0.0))

    has_photo = (
        db.session.query(literal(1))
        .filter(UserPhoto.user_id == User.id)
        .correlate(User)
        .exists()
    )
    photo_score = case((has_photo, literal(0.25)), else_=literal(0.0))

    looking_for_score = case((User.looking_for.is_not(None), literal(0.25)), else_=literal(0.0))

    dob_score = case((User.date_of_birth.is_not(None), literal(0.25)), else_=literal(0.0))

    return bio_score + photo_score + looking_for_score + dob_score


def _serialize_profile(user: User, ranking_score: float, photo_url: str = None) -> dict:
    """Serialize a user to the DiscoveryProfile spec shape."""
    age = None
    if user.date_of_birth:
        today = datetime.now(timezone.utc).date()
        age = (today.year - user.date_of_birth.year -
               ((today.month, today.day) < (user.date_of_birth.month, user.date_of_birth.day)))

    return {
        'id': str(user.id),
        'display_name': user.display_name,
        'bio': user.bio,
        'age': age,
        'gender': user.gender,
        'photo_url': photo_url,
        'is_verified': user.is_verified,
        'ranking_score': round(ranking_score, 4) if ranking_score is not None else 0.0,
    }
