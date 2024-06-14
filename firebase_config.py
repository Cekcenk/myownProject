import firebase_admin
from firebase_admin import credentials, firestore

# Use a service account
cred = credentials.Certificate("sing-ai-4381a-firebase-adminsdk-1yv4h-724e2489c4.json")
firebase_admin.initialize_app(cred)

db = firestore.client()