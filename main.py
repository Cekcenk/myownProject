import sys
import os
import uuid
import logging
import json  # Added this line
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from celery import chain
from celery_app import app as celery_app
from tasks.download import download_youtube_audio
from tasks.separate import separate_audio_task
from tasks.convert import convert_vocals
from tasks.merge import merge_audio
from tasks.update_status import update_status, init_status, finish_status
from task_status import task_status
from dotenv import load_dotenv
from utils import download_model_files
import firebase_admin
from firebase_admin import auth

app = FastAPI()

class ProcessRequest(BaseModel):
    youtube_link: str
    model_name: str
    idToken: str
    imageUrl: str
    artistName: str

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Create directories if they don't exist
DOWNLOADS_DIR = "downloads"
OUTPUTS_DIR = "outputs"
MODELS_DIR = "models"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

load_dotenv()
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

# Load model configuration
with open('models_config.json') as f:
    models_config = json.load(f)

@app.post("/process/")
async def process(request: ProcessRequest, background_tasks: BackgroundTasks):
    try:
        decoded_token = auth.verify_id_token(request.idToken)
        user_id = decoded_token['uid']

        unique_id = str(uuid.uuid4())
        output_path = os.path.join(DOWNLOADS_DIR, unique_id)
        input_path = f"{output_path}.mp3"
        output_dir = os.path.join(OUTPUTS_DIR, unique_id)

        os.makedirs(output_dir, exist_ok=True)

        vocal_path = os.path.join(output_dir, f"{unique_id}_(Vocals)_MDX23C-8KFFT-InstVoc_HQ.wav")
        instrumental_path = os.path.join(output_dir, f"{unique_id}_(Instrumental)_MDX23C-8KFFT-InstVoc_HQ.wav")
        processed_vocal_path = os.path.join(output_dir, "processed_vocal.wav")
        final_output_path = os.path.join(output_dir, "final_output.mp3")

        # Initialize task status
        task_status[unique_id] = "0/4"
        init_status.s(
            user_id=user_id, 
            task_id=unique_id, 
            status="0/4", 
            imageUrl=request.imageUrl, 
            artistName=request.artistName
        ).apply_async()
        logger.info(f"Starting process with output_path: {output_path} and output_dir: {output_dir}")

        # Check if the model exists in the configuration
        if request.model_name not in models_config['models']:
            raise HTTPException(status_code=404, detail="Model not found")

        model_info = models_config['models'][request.model_name]
        local_model_dir = os.path.join(MODELS_DIR, request.model_name)
        os.makedirs(local_model_dir, exist_ok=True)

        # Download the model files if not already cached
        pth_local_path, index_local_path = download_model_files(model_info, local_model_dir)

        # Create the task chain
        task_chain = (
            download_youtube_audio.s(youtube_url=request.youtube_link, output_path=output_path) |
            update_status.s(user_id=user_id, task_id=unique_id, status="1/4") |
            separate_audio_task.s(input_path=input_path, output_dir=output_dir) |
            update_status.s(user_id=user_id, task_id=unique_id, status="2/4") |
            convert_vocals.s(vocal_path=vocal_path, model_name=pth_local_path, processed_vocal_path=processed_vocal_path) |
            update_status.s(user_id=user_id, task_id=unique_id, status="3/4") |
            merge_audio.s(
                processed_vocal_path=processed_vocal_path, 
                instrumental_path=instrumental_path, 
                final_output_path=final_output_path,
                bucket_name=S3_BUCKET_NAME,
                s3_key=f'{unique_id}.mp3'
            ) |
            update_status.s(user_id=user_id, task_id=unique_id, status="4/4") |
            finish_status.s(user_id=user_id, task_id=unique_id, s3_url=f'https://{S3_BUCKET_NAME}.s3.amazonaws.com/{unique_id}.mp3')
        )

        task_chain.apply_async()

        background_tasks.add_task(cleanup_files, [output_path, vocal_path, instrumental_path, processed_vocal_path])

        return {"message": "Processing started", "id": unique_id}
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    status = task_status.get(task_id, "Task not found")
    return {"task_id": task_id, "status": status}

async def cleanup_files(files):
    for file in files:
        if os.path.exists(file):
            os.remove(file)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
