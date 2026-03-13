import jwt
from firebase_admin import auth as firebase_auth
from flask import Blueprint, jsonify, request

from app.services.auth_service import verify_firebase_and_issue_tokens, refresh_access_token

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')


@auth_bp.route('/verify', methods=['POST'])
def verify():
    data = request.get_json(silent=True)
    if not data or not data.get('id_token'):
        return jsonify({'error': 'Missing id_token in request body'}), 400

    try:
        result = verify_firebase_and_issue_tokens(data['id_token'])
        return jsonify(result), 200
    except firebase_auth.InvalidIdTokenError:
        return jsonify({'error': 'Invalid Firebase token'}), 401
    except firebase_auth.ExpiredIdTokenError:
        return jsonify({'error': 'Firebase token has expired'}), 401
    except firebase_auth.RevokedIdTokenError:
        return jsonify({'error': 'Firebase token has been revoked'}), 401
    except firebase_auth.CertificateFetchError:
        return jsonify({'error': 'Could not verify token, please try again'}), 503
    except Exception:
        return jsonify({'error': 'Internal server error'}), 500


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    data = request.get_json(silent=True)
    if not data or not data.get('refresh_token'):
        return jsonify({'error': 'Missing refresh_token in request body'}), 400

    try:
        result = refresh_access_token(data['refresh_token'])
        return jsonify(result), 200
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Refresh token has expired'}), 401
    except jwt.InvalidTokenError as e:
        return jsonify({'error': str(e)}), 401
