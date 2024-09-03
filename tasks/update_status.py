from celery import shared_task
from task_status import task_status
from firebase_config import db
from datetime import datetime
import logging
from google.cloud.firestore import SERVER_TIMESTAMP, FieldFilter
from firebase_admin import messaging

logger = logging.getLogger(__name__)


@shared_task
def update_status(*args, user_id, task_id, status):
    try:
        doc_ref = db.collection("users").document(user_id).collection("library").document(task_id)
        update_data = {"status": status}
        doc_ref.update(update_data)
    except Exception as e:
        print(f"Error updating status in Firestore: {e}")
    task_status[task_id] = status
    print(f"Updating status to {status} for task ID {task_id}")

@shared_task
def init_status(user_id, task_id, status, imageUrl, artistName, songName):
    try:
        doc_ref = db.collection("users").document(user_id).collection("library").document(task_id)
        doc_ref.set({
            "status": status,
            "artistName": artistName,
            "image": imageUrl,
            "isGenerating": True,
            "songName": songName,
            "soundUrl": "",
            "videoUrl": "",
            "timestamp": SERVER_TIMESTAMP,
            "isPulished" : False,
            "listenCount" : 0  
        })
    except Exception as e:
        print(f"Error setting status in Firestore: {e}")

@shared_task
def finish_status(*args, user_id, task_id, s3_url):
    try:
        doc_ref = db.collection("users").document(user_id).collection("library").document(task_id)
        doc_ref.update({
            "soundUrl": s3_url,
            "status": "4/4",
            "isGenerating": False
        })
    except Exception as e:
        print(f"Error updating soundUrl in Firestore: {e}")

@shared_task
def send_fcm_notification(*args, user_id, message_title, message_body):
    try:
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            fcm_token = user_data.get("fcm")
            if fcm_token:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=message_title,
                        body=message_body,
                    ),
                    token=fcm_token,
                )
                response = messaging.send(message)
                print(f"Successfully sent message: {response}")
            else:
                print(f"No FCM token found for user {user_id}")
        else:
            print(f"No user document found for user {user_id}")
    except Exception as e:
        print(f"Error sending FCM notification: {e}")

def check_user_subscription(user_id):
    try:
        user_doc_ref = db.collection("users").document(user_id)
        user_doc = user_doc_ref.get()
        
        if not user_doc.exists:
            return False
        
        data = user_doc.to_dict()
        
        if not data:
            logger.warning(f"User {user_id} exists but has no fields.")
            return False
        
        entitlements = data.get("entitlements")
        if not entitlements or "subscription" not in entitlements:
            logger.info(f"User {user_id} does not have a subscription.")
            return False
        
        subscription = entitlements.get("subscription")
        if not subscription:
            logger.warning(f"User {user_id} has no subscription information.")
            return False
        
        expires_date = subscription.get("expires_date")
        
        if expires_date is None:
            logger.info(f"User {user_id} has no expiration date.")
            return True
        
        expires_date = datetime.strptime(expires_date, "%Y-%m-%dT%H:%M:%SZ")
        if expires_date < datetime.now():
            logger.info(f"Subscription for user {user_id} has expired.")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error checking user subscription for user {user_id}: {e}")
        return False

def fetch_user_document(user_id):
    user_ref = db.collection('users').document(user_id)
    user_doc = user_ref.get()
    if not user_doc.exists:
        user_ref.set({'tokenCounter': 3})
        token_counter = 3
    else:
        token_counter = user_doc.to_dict().get('tokenCounter', 3)
    return user_ref, token_counter

def subtract_token_if_not_subscribed(user_ref, token_counter):
    user_ref.update({'tokenCounter': token_counter - 1})

def get_user_active_tasks(user_id):
    active_tasks = 0
    user_tasks = db.collection("users").document(user_id).collection("library").where(
        filter=FieldFilter("isGenerating", "==", True)
    ).get()
    active_tasks = len(user_tasks)
    return active_tasks