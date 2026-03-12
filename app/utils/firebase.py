import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate("firebase_service_account.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)