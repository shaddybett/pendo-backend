from flask import Blueprint, request, jsonify
from app.services.auth_service import verify_firebase_token

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')

@auth_bp.route('/verify', methods=['POST'])
def verify():
    try:
        id_token = request.headers.get('Authorization')
        if not id_token:
            return jsonify({'error': 'Missing Authorization header'}), 400
        user = verify_firebase_token(id_token)
        return jsonify(user), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 401
