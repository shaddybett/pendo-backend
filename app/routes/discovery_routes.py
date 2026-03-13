from flask import Blueprint, g, jsonify, request

from app.extensions.jwt import token_required
from app.models.user import User
from app.services.discovery_service import discover_profiles

discover_bp = Blueprint('discover', __name__, url_prefix='/api/v1')


@discover_bp.route('/discover', methods=['GET'])
@token_required
def discover():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 20

    current_user = User.query.get(g.current_user_id)
    if not current_user:
        return jsonify({'error': 'User not found'}), 404

    result = discover_profiles(current_user, page, per_page)
    return jsonify(result), 200
