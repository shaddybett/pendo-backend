from flask import Blueprint, g, jsonify, request

from app.extensions.jwt import token_required
from app.models.user import User
from app.services.swipe_service import record_swipe

swipes_bp = Blueprint('swipes', __name__, url_prefix='/api/v1/swipes')


@swipes_bp.route('', methods=['POST'])
@token_required
def create_swipe():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Missing JSON body'}), 400

    target_user_id = data.get('target_user_id')
    direction = data.get('direction')

    if not target_user_id or not direction:
        return jsonify({'error': 'target_user_id and direction are required'}), 400

    # Verify target user exists
    target = User.query.get(target_user_id)
    if not target or not target.is_active:
        return jsonify({'error': 'Target user not found'}), 404

    try:
        result = record_swipe(g.current_user_id, target_user_id, direction)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
