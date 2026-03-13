import logging
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

log = logging.getLogger(__name__)


def encode_access_token(user_id: uuid.UUID) -> str:
    key = current_app.config['JWT_SECRET_KEY']
    log.debug('encode_access_token: using key [%s...] (%d bytes)', key[:8], len(key))
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(user_id),
        'type': 'access',
        'iat': now,
        'exp': now + timedelta(seconds=current_app.config['JWT_ACCESS_TOKEN_EXPIRES']),
    }
    return jwt.encode(payload, key, algorithm='HS256')


def encode_refresh_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(user_id),
        'type': 'refresh',
        'iat': now,
        'exp': now + timedelta(seconds=current_app.config['JWT_REFRESH_TOKEN_EXPIRES']),
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError."""
    key = current_app.config['JWT_SECRET_KEY']
    log.debug('decode_token: using key [%s...] (%d bytes)', key[:8], len(key))
    return jwt.decode(token, key, algorithms=['HS256'])


def token_required(f):
    """Decorator for routes that require a valid access token.

    Sets g.current_user_id (str UUID) on success.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            log.warning('token_required: missing or malformed Authorization header')
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401

        token = auth_header.split(' ', 1)[1]
        log.debug('token_required: token starts with %s...', token[:20])
        try:
            payload = decode_token(token)
            log.debug('token_required: decoded payload sub=%s type=%s', payload.get('sub'), payload.get('type'))
        except jwt.ExpiredSignatureError:
            log.warning('token_required: access token expired')
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError as e:
            log.warning('token_required: invalid token — %s', e)
            return jsonify({'error': 'Invalid token'}), 401

        if payload.get('type') != 'access':
            return jsonify({'error': 'Invalid token type'}), 401

        from app.models.user import User
        user = User.query.get(payload['sub'])
        if not user or not user.is_active:
            return jsonify({'error': 'User account is inactive or deleted'}), 401

        g.current_user_id = payload['sub']
        return f(*args, **kwargs)
    return decorated
