import firebase_admin
from firebase_admin import auth as firebase_auth
from app.models.user import User
from app.extensions.db import db


def verify_firebase_token(id_token):
    # Remove 'Bearer ' prefix if present
    if id_token.startswith('Bearer '):
        id_token = id_token.split(' ', 1)[1]
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        firebase_uid = decoded_token['uid']
        email = decoded_token.get('email')
        name = decoded_token.get('name', '')
        # Check if user exists
        user = User.query.filter_by(firebase_uid=firebase_uid).first()
        is_new_user = False
        if not user:
            user = User(firebase_uid=firebase_uid,
                        display_name=name, email=email)
            db.session.add(user)
            db.session.commit()
            is_new_user = True
        # Build response
        return {
            'id': str(user.id),
            'display_name': user.display_name,
            'email': user.email,
            'is_new_user': is_new_user
        }
    except Exception as e:
        print('Firebase token verification error:', e)
        raise Exception('Invalid Firebase token')
