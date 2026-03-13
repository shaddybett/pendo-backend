import logging
import uuid
from datetime import date, datetime

from flask import Blueprint, g, jsonify, request

from app.extensions.db import db
from app.extensions.jwt import token_required
from app.models.photo import UserPhoto
from app.models.user import User
from app.utils.firebase import get_storage_bucket

log = logging.getLogger(__name__)

users_bp = Blueprint('users', __name__, url_prefix='/api/v1/users')

VALID_GENDERS = {'male', 'female', 'non-binary'}
VALID_LOOKING_FOR = {'male', 'female', 'everyone'}
UPDATABLE_FIELDS = {
    'display_name', 'bio', 'date_of_birth', 'gender',
    'looking_for', 'discovery_radius_km', 'age_min', 'age_max',
}
ALLOWED_IMAGE_TYPES = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/webp': 'webp',
}
MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 MB
PHOTO_MAX_WIDTH = 1080
PHOTO_JPEG_QUALITY = 85


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


@users_bp.route('/me/photos', methods=['POST'])
@token_required
def upload_photo():
    from io import BytesIO
    from PIL import Image

    user = User.query.get(g.current_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if 'photo' not in request.files:
        return jsonify({'error': 'Missing photo field'}), 400

    file = request.files['photo']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    content_type = file.content_type or ''
    if content_type not in ALLOWED_IMAGE_TYPES:
        return jsonify({'error': f'Invalid image type. Allowed: {", ".join(ALLOWED_IMAGE_TYPES.keys())}'}), 400

    # Read file data and check size
    file_data = file.read()
    if len(file_data) > MAX_PHOTO_SIZE:
        return jsonify({'error': 'Photo must be 10 MB or smaller'}), 400

    # Resize and compress — output always JPEG for consistency and small size
    try:
        img = Image.open(BytesIO(file_data))
        img.exif_transpose(in_place=True) if hasattr(img, 'exif_transpose') else None
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        if img.width > PHOTO_MAX_WIDTH:
            ratio = PHOTO_MAX_WIDTH / img.width
            img = img.resize((PHOTO_MAX_WIDTH, int(img.height * ratio)), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=PHOTO_JPEG_QUALITY, optimize=True)
        file_data = buf.getvalue()
        content_type = 'image/jpeg'
    except Exception as e:
        log.warning('Image processing failed, uploading original: %s', e)
        # Fall through with original file_data if processing fails

    photo_id = uuid.uuid4()
    ext = ALLOWED_IMAGE_TYPES[content_type]
    blob_path = f'users/{user.id}/photos/{photo_id}.{ext}'

    # Upload to Firebase Storage with a persistent download token
    try:
        from urllib.parse import quote

        download_token = str(uuid.uuid4())
        bucket = get_storage_bucket()
        blob = bucket.blob(blob_path)
        blob.upload_from_string(
            file_data,
            content_type=content_type,
        )
        # Set metadata and cache after upload in a single patch — guaranteed to persist
        blob.metadata = {'firebaseStorageDownloadTokens': download_token}
        blob.cache_control = 'public, max-age=31536000'
        blob.patch()

        # Permanent Firebase download URL — never expires
        encoded_path = quote(blob_path, safe='')
        download_url = (
            f'https://firebasestorage.googleapis.com/v0/b/{bucket.name}'
            f'/o/{encoded_path}?alt=media&token={download_token}'
        )
    except Exception as e:
        log.exception('Photo upload to Firebase Storage failed: %s', e)
        return jsonify({'error': 'Photo upload failed'}), 500

    # Determine position and is_primary
    max_pos = db.session.query(db.func.max(UserPhoto.position)).filter_by(user_id=user.id).scalar()
    position = 0 if max_pos is None else max_pos + 1
    is_primary = position == 0

    # Store the blob path so we can always re-sign or delete reliably
    photo = UserPhoto(
        id=photo_id,
        user_id=user.id,
        url=download_url,
        position=position,
        is_primary=is_primary,
    )
    db.session.add(photo)
    db.session.commit()

    return jsonify({
        'id': str(photo.id),
        'url': photo.url,
        'position': photo.position,
        'is_primary': photo.is_primary,
        'created_at': photo.created_at.isoformat() if photo.created_at else None,
    }), 200


@users_bp.route('/me/photos/<photo_id>', methods=['DELETE'])
@token_required
def delete_photo(photo_id):
    user = User.query.get(g.current_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    photo = UserPhoto.query.filter_by(id=photo_id, user_id=user.id).first()
    if not photo:
        return jsonify({'error': 'Photo not found'}), 404

    # Delete from Firebase Storage — try each possible extension
    try:
        bucket = get_storage_bucket()
        deleted = False
        for ext in ('jpg', 'png', 'webp'):
            blob_path = f'users/{user.id}/photos/{photo.id}.{ext}'
            blob = bucket.blob(blob_path)
            if blob.exists():
                blob.delete()
                deleted = True
                break
        if not deleted:
            log.warning('Photo blob not found in storage for photo_id=%s', photo.id)
    except Exception as e:
        log.warning('Failed to delete photo from storage (continuing): %s', e)

    was_primary = photo.is_primary
    db.session.delete(photo)
    db.session.flush()

    # If deleted photo was primary, promote the lowest-position remaining photo
    if was_primary:
        next_photo = (UserPhoto.query
                      .filter_by(user_id=user.id)
                      .order_by(UserPhoto.position)
                      .first())
        if next_photo:
            next_photo.is_primary = True

    db.session.commit()
    return jsonify({'message': 'Photo deleted'}), 200


@users_bp.route('/<user_id>', methods=['GET'])
@token_required
def get_public_profile(user_id):
    user = User.query.get(user_id)
    if not user or not user.is_active:
        return jsonify({'error': 'User not found'}), 404

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

    return jsonify({
        'id': str(user.id),
        'display_name': user.display_name,
        'bio': user.bio,
        'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None,
        'gender': user.gender,
        'is_active': user.is_active,
        'is_verified': user.is_verified,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'photos': photos,
    }), 200
