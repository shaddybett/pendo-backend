import os

import firebase_admin
from firebase_admin import credentials, storage

cred = credentials.Certificate("firebase_service_account.json")

bucket_name = os.getenv('FIREBASE_STORAGE_BUCKET')

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'storageBucket': bucket_name,
    })


def get_storage_bucket():
    """Return the default Firebase Storage bucket."""
    return storage.bucket()
