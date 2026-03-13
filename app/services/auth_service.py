from datetime import datetime, timezone

from firebase_admin import auth as firebase_auth
from jwt import InvalidTokenError

from app.extensions.db import db
from app.extensions.jwt import encode_access_token, encode_refresh_token, decode_token
from app.models.user import User


def verify_firebase_and_issue_tokens(id_token: str) -> dict:
    """Verify a Firebase ID token, create or find the user, and return a JWT pair.

    Returns the exact shape the frontend expects:
        { access_token, refresh_token, user_id, is_new_user }
    """
    decoded = firebase_auth.verify_id_token(id_token)

    firebase_uid = decoded['uid']
    email = decoded.get('email')
    phone = decoded.get('phone_number')
    name = decoded.get('name', '')

    user = User.query.filter_by(firebase_uid=firebase_uid).first()
    is_new_user = user is None

    if is_new_user:
        user = User(
            firebase_uid=firebase_uid,
            display_name=name,
            email=email,
            phone=phone,
        )
        db.session.add(user)
    else:
        # Keep profile data in sync with Firebase on every login
        if email and user.email != email:
            user.email = email
        if phone and user.phone != phone:
            user.phone = phone
        user.last_active_at = datetime.now(timezone.utc)

    db.session.commit()

    return {
        'access_token': encode_access_token(user.id),
        'refresh_token': encode_refresh_token(user.id),
        'user_id': str(user.id),
        'is_new_user': is_new_user,
    }


def refresh_access_token(refresh_token: str) -> dict:
    """Validate a refresh token and return a new access token.

    Returns: { access_token }
    Raises: jwt exceptions on invalid/expired token.
    """
    payload = decode_token(refresh_token)

    if payload.get('type') != 'refresh':
        raise InvalidTokenError('Token is not a refresh token')

    user_id = payload['sub']

    user = User.query.get(user_id)
    if not user or not user.is_active:
        raise InvalidTokenError('User account is inactive or deleted')

    return {
        'access_token': encode_access_token(user_id),
    }
