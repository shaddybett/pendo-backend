from datetime import date, datetime

from flask import Blueprint, g, jsonify, request

from app.extensions.db import db
from app.extensions.jwt import token_required
from app.models.user import User

users_bp = Blueprint('users', __name__, url_prefix='/api/v1/users')

VALID_GENDERS = {'male', 'female', 'non-binary'}
VALID_LOOKING_FOR = {'male', 'female', 'everyone'}
UPDATABLE_FIELDS = {
    'display_name', 'bio', 'date_of_birth', 'gender',
    'looking_for', 'discovery_radius_km', 'age_min', 'age_max',
}


def serialize_user(user: User) -> dict:
    """Serialize a User to the full UserModel JSON shape from the spec."""
    photos = [
        {
            'id': str(p.id),
            'url': p.url,
            'position': p.position,
            'is_primary': p.is_primary,
            'created_at': p.created_at.isoformat() if p.created_at else None,
        }
        for p in user.photos.order_by('position').all()
    ]

    return {
        'id': str(user.id),
        'display_name': user.display_name,
        'email': user.email,
        'phone': user.phone,
        'bio': user.bio,
        'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None,
        'gender': user.gender,
        'looking_for': user.looking_for,
        'discovery_radius_km': user.discovery_radius_km,
        'age_min': user.age_min,
        'age_max': user.age_max,
        'is_active': user.is_active,
        'is_verified': user.is_verified,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        'last_active_at': user.last_active_at.isoformat() if user.last_active_at else None,
        'photos': photos,
    }


@users_bp.route('/me', methods=['GET'])
@token_required
def get_me():
    user = User.query.get(g.current_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(serialize_user(user)), 200


@users_bp.route('/me', methods=['PUT'])
@token_required
def update_me():
    user = User.query.get(g.current_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Missing JSON body'}), 400

    errors = []

    # Only process whitelisted fields
    for field in UPDATABLE_FIELDS & data.keys():
        value = data[field]

        if field == 'display_name':
            if not isinstance(value, str) or not value.strip():
                errors.append('display_name must be a non-empty string')
                continue
            user.display_name = value.strip()

        elif field == 'bio':
            if value is not None and not isinstance(value, str):
                errors.append('bio must be a string or null')
                continue
            if isinstance(value, str) and len(value) > 500:
                errors.append('bio must be 500 characters or fewer')
                continue
            user.bio = value

        elif field == 'date_of_birth':
            if value is None:
                user.date_of_birth = None
                continue
            try:
                user.date_of_birth = date.fromisoformat(value)
            except (ValueError, TypeError):
                errors.append('date_of_birth must be YYYY-MM-DD format')

        elif field == 'gender':
            if value is not None and value not in VALID_GENDERS:
                errors.append(f'gender must be one of: {", ".join(sorted(VALID_GENDERS))}')
                continue
            user.gender = value

        elif field == 'looking_for':
            if value is not None and value not in VALID_LOOKING_FOR:
                errors.append(f'looking_for must be one of: {", ".join(sorted(VALID_LOOKING_FOR))}')
                continue
            user.looking_for = value

        elif field in ('discovery_radius_km', 'age_min', 'age_max'):
            if not isinstance(value, int) or isinstance(value, bool):
                errors.append(f'{field} must be an integer')
                continue
            if field == 'age_min' and value < 18:
                errors.append('age_min must be at least 18')
                continue
            setattr(user, field, value)

    if errors:
        return jsonify({'error': '; '.join(errors)}), 400

    # Cross-field validation after all assignments
    if user.age_min is not None and user.age_max is not None and user.age_max < user.age_min:
        return jsonify({'error': 'age_max must be greater than or equal to age_min'}), 400

    db.session.commit()
    return jsonify(serialize_user(user)), 200


@users_bp.route('/me/location', methods=['PUT'])
@token_required
def update_location():
    user = User.query.get(g.current_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Missing JSON body'}), 400

    lat = data.get('latitude')
    lng = data.get('longitude')

    if lat is None or lng is None:
        return jsonify({'error': 'Both latitude and longitude are required'}), 400

    if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
        return jsonify({'error': 'latitude and longitude must be numbers'}), 400

    if not (-90 <= lat <= 90):
        return jsonify({'error': 'latitude must be between -90 and 90'}), 400

    if not (-180 <= lng <= 180):
        return jsonify({'error': 'longitude must be between -180 and 180'}), 400

    user.latitude = lat
    user.longitude = lng
    db.session.commit()

    return jsonify({'message': 'Location updated'}), 200
