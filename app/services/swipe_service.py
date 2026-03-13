import logging

from sqlalchemy.exc import IntegrityError

from app.extensions.db import db
from app.models.match import Match
from app.models.swipe import Swipe

log = logging.getLogger(__name__)

POSITIVE_DIRECTIONS = {'like', 'super_like'}
VALID_DIRECTIONS = {'like', 'dislike', 'super_like'}


def record_swipe(swiper_id: str, target_user_id: str, direction: str) -> dict:
    """Record a swipe and detect mutual matches.

    Returns the spec-compliant response:
        { swipe_id, is_match, duplicate }

    The entire operation (swipe insert + optional match creation) runs in
    a single transaction.  Race conditions are handled by DB constraints:
      - uq_swipe_pair  → prevents duplicate swipes
      - uq_match_pair  → prevents duplicate matches
    """
    if direction not in VALID_DIRECTIONS:
        raise ValueError(f'direction must be one of: {", ".join(sorted(VALID_DIRECTIONS))}')

    if swiper_id == target_user_id:
        raise ValueError('Cannot swipe on yourself')

    # Fast-path: check for existing swipe (app-level dedup)
    existing = Swipe.query.filter_by(
        swiper_id=swiper_id,
        target_user_id=target_user_id,
    ).first()
    if existing:
        return {
            'swipe_id': str(existing.id),
            'is_match': False,
            'duplicate': True,
        }

    # Insert the swipe
    swipe = Swipe(
        swiper_id=swiper_id,
        target_user_id=target_user_id,
        direction=direction,
    )
    try:
        db.session.add(swipe)
        db.session.flush()  # Get swipe.id, stay in same transaction
    except IntegrityError:
        db.session.rollback()
        # Race condition: another request inserted the same swipe
        existing = Swipe.query.filter_by(
            swiper_id=swiper_id,
            target_user_id=target_user_id,
        ).first()
        return {
            'swipe_id': str(existing.id) if existing else None,
            'is_match': False,
            'duplicate': True,
        }

    # Check for mutual like (only if this swipe is positive)
    is_match = False
    if direction in POSITIVE_DIRECTIONS:
        mutual = Swipe.query.filter(
            Swipe.swiper_id == target_user_id,
            Swipe.target_user_id == swiper_id,
            Swipe.direction.in_(POSITIVE_DIRECTIONS),
        ).first()

        if mutual:
            is_match = _create_match_if_not_exists(swiper_id, target_user_id)

    db.session.commit()

    return {
        'swipe_id': str(swipe.id),
        'is_match': is_match,
        'duplicate': False,
    }


def _create_match_if_not_exists(user_a: str, user_b: str) -> bool:
    """Create a match between two users, normalized so user1_id < user2_id.

    Uses a savepoint so that a duplicate match (from a race) doesn't
    blow up the outer transaction.

    Returns True if a match exists (created now or already existed).
    """
    user1 = min(user_a, user_b)
    user2 = max(user_a, user_b)

    # Check if match already exists
    existing = Match.query.filter_by(user1_id=user1, user2_id=user2).first()
    if existing:
        return True

    match = Match(user1_id=user1, user2_id=user2)
    nested = db.session.begin_nested()  # SAVEPOINT
    try:
        db.session.add(match)
        db.session.flush()
        nested.commit()
        log.info('Match created: %s ↔ %s (match_id=%s)', user1, user2, match.id)
        return True
    except IntegrityError:
        nested.rollback()  # Rolls back only this savepoint
        log.info('Match already exists (race): %s ↔ %s', user1, user2)
        return True
