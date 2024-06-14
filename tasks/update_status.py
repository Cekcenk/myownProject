from celery import shared_task
from task_status import task_status
from firebase_config import db


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
def init_status(user_id, task_id, status, imageUrl, artistName):
    try:
        doc_ref = db.collection("users").document(user_id).collection("library").document(task_id)
        doc_ref.set({
            "status": status,
            "artistName": artistName,
            "image": imageUrl,
            "isGenerating": True,
            "songName": "testSong",
            "soundUrl": "",
            "videoUrl": ""
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
