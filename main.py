import sys
import os
import uuid
import logging
import json
import subprocess
from fastapi import FastAPI, BackgroundTasks, HTTPException, File, UploadFile, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from celery_app import app as celery_app
from tasks.process_audio import process_audio_task
from tasks.update_status import get_user_active_tasks, init_status, check_user_subscription, fetch_user_document, subtract_token_if_not_subscribed
from task_status import task_status
from dotenv import load_dotenv
from utils import download_model_files
from firebase_admin import auth
# import sentry_sdk
import time
import re
import torch
from urllib.parse import urlparse, parse_qs
from proxy_manager import proxy_manager
import asyncio
from redis import Redis
import random
from itertools import cycle
import shutil
import requests
import time
import random
import yt_dlp

load_dotenv()

# sentry_sdk.init(
#     dsn="https://8b2b17f95884c214d3459f520db0bbf3@o4507498009788416.ingest.de.sentry.io/4507498011689040",
#     traces_sample_rate=1.0,
#     profiles_sample_rate=1.0,
#     enable_tracing=True,
# )

app = FastAPI()
security = HTTPBearer()

# Add this near the top of your main.py file, after initializing the FastAPI app
redis_client = Redis(host='localhost', port=6379, db=0)

@app.on_event("startup")
async def startup_event():
    try:
        redis_client.ping()
        logger.info("Successfully connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to Redis or load proxies: {str(e)}")
        raise

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

def is_valid_youtube_url(url):
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    match = re.match(youtube_regex, url)
    if not match:
        return False
    
    valid_domains = ['youtube.com', 'youtu.be', 'www.youtube.com']
    parsed_url = urlparse(url)
    if parsed_url.netloc not in valid_domains:
        return False

    query_params = parse_qs(parsed_url.query)
    if 'list' in query_params and query_params['list'][0].startswith('HLS_'):
        return False

    return True

ORIGINAL_COOKIES_FILE = 'original_cookies.txt'
WORKING_COOKIES_FILE = 'cookies.txt'

def refresh_cookies():
    try:
        shutil.copy2(ORIGINAL_COOKIES_FILE, WORKING_COOKIES_FILE)
        logger.info("Cookies refreshed successfully")
    except Exception as e:
        logger.error(f"Error refreshing cookies: {str(e)}")

def extract_video_info(youtube_url, max_retries=3):
    if not is_valid_youtube_url(youtube_url):
        logger.error(f"Invalid YouTube URL: {youtube_url}")
        return 'Unknown Title', 0

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': '%(id)s.%(ext)s',
        'ignoreerrors': True,
        'no_warnings': True,
        'cookiefile': WORKING_COOKIES_FILE,
    }

    proxy = proxy_manager.get_proxy()
    if proxy:
        ydl_opts['proxy'] = proxy

    for attempt in range(max_retries):
        try:
            refresh_cookies()  # Refresh cookies before each attempt
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                if info:
                    title = info.get('title', 'Unknown Title')
                    duration = int(info.get('duration', 0))
                    logger.info(f"Successfully extracted video info: Title: {title}, Duration: {duration} seconds")
                    return title, duration
                else:
                    raise ValueError("No video info returned")
        except Exception as e:
            logger.error(f"Error on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = random.uniform(1, 5)
                logger.info(f"Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                proxy = proxy_manager.get_proxy()
                if proxy:
                    ydl_opts['proxy'] = proxy
            else:
                logger.error("Max retries reached. Returning default values.")
                return 'Unknown Title', 0

    return 'Unknown Title', 0

def is_gpu_idle():
    return torch.cuda.memory_allocated() == 0

@app.get("/status")
async def get_status():
    queue_length = redis_client.llen('chain_queue')
    gpu_idle = is_gpu_idle()
    return {"queue_length": queue_length, "gpu_idle": gpu_idle}


# List of proxies
PROXIES = [
    "38.153.220.205:8800",
    "38.154.97.8:8800",
    "38.152.186.138:8800",
    "38.152.186.117:8800",
    "38.153.220.116:8800",
    "38.154.90.80:8800",
    "38.153.220.8:8800",
    "38.154.90.112:8800",
    "38.154.97.110:8800",
    "38.153.220.94:8800",
]

@app.post("/process/")
async def process(request: ProcessRequest, background_tasks: BackgroundTasks):
    try:
        # Validate YouTube URL
        if not is_valid_youtube_url(request.youtube_link):
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        decoded_token = auth.verify_id_token(request.idToken)
        user_id = decoded_token['uid']

        # Check the number of active tasks for the user
        active_tasks = get_user_active_tasks(user_id)
        if active_tasks >= 2:
            raise HTTPException(status_code=503, detail="You can only process a total of 2 tasks at the same time")

        # Fetch user document from Firestore
        user_ref, token_counter = fetch_user_document(user_id)

        # Check token counter
        if token_counter == 0:
            raise HTTPException(status_code=506, detail="User doesn't have enough tokens left")

        unique_id = str(uuid.uuid4())
        output_path = os.path.join(DOWNLOADS_DIR, unique_id)
        input_path = f"{output_path}.mp3"
        output_dir = os.path.join(OUTPUTS_DIR, unique_id)
        os.makedirs(output_dir, exist_ok=True)

        vocal_path = os.path.join(output_dir, f"{unique_id}_(Vocals)_MDX23C-8KFFT-InstVoc_HQ.wav")
        instrumental_path = os.path.join(output_dir, f"{unique_id}_(Instrumental)_MDX23C-8KFFT-InstVoc_HQ.wav")
        processed_vocal_path = os.path.join(output_dir, "processed_vocal.wav")
        final_output_path = os.path.join(output_dir, "final_output.mp3")

        # Fetch the video title and duration
        video_title, video_duration = extract_video_info(request.youtube_link)

        # Check if the video duration is longer than 7 minutes
        if video_duration > 7 * 60:
            raise HTTPException(status_code=501, detail="Video duration is longer than 7 minutes")


        # Check if the model exists in the configuration
        if request.model_name not in models_config['models']:
            raise HTTPException(status_code=502, detail="Model not found")

        model_info = models_config['models'][request.model_name]
        local_model_dir = os.path.join(MODELS_DIR, request.model_name)
        os.makedirs(local_model_dir, exist_ok=True)

        # Download the model files if not already cached
        pth_local_path, index_local_path = download_model_files(model_info, local_model_dir)

        subbed = check_user_subscription(user_id)
        
        # Subtract one token if not subscribed
        if not subbed:
            subtract_token_if_not_subscribed(user_ref, token_counter)

        # Initialize task status
        task_status[unique_id] = "0/4"
        init_status(
            user_id=user_id, 
            task_id=unique_id, 
            status="0/4", 
            imageUrl=request.imageUrl, 
            artistName=request.artistName,
            songName=video_title
        )
        logger.info(f"Starting process with output_path: {output_path} and output_dir: {output_dir}")

        # Create a single task that handles the entire audio processing chain
        task = process_audio_task.s(
                youtube_url=request.youtube_link,
                output_path=output_path,
                output_dir=output_dir,
                input_path=input_path,
                vocal_path=vocal_path,
                pth_local_path=pth_local_path,
                processed_vocal_path=processed_vocal_path,
                instrumental_path=instrumental_path,
                final_output_path=final_output_path,
                user_id=user_id,
                task_id=unique_id,
                video_title=video_title,
                full_video=subbed,
                S3_BUCKET_NAME=S3_BUCKET_NAME,
                S3_KEY=f'{unique_id}.mp3',
                unique_id=unique_id
        )

        # Apply the task
        task_result = task.apply_async(
            task_id=unique_id,
            queue='chain_queue',
            routing_key='chain'
        )

        logger.info(f"Task applied with result: {task_result}")

        # Add a small delay to allow the task to be queued
        await asyncio.sleep(0.1)

        # Get all keys that start with 'chain_queue'
        all_keys = redis_client.keys('chain_queue*')
        
        queue_lengths = {}
        for key in all_keys:
            decoded_key = key.decode('utf-8')  # Decode bytes to string
            queue_lengths[decoded_key] = redis_client.llen(key)

        logger.info(f"Queue lengths after adding task: {queue_lengths}")

        # Check if any queue has items
        total_queue_length = sum(queue_lengths.values())
        logger.info(f"Total items in queues: {total_queue_length}")

        return {"message": "Processing started", "id": unique_id, "task_id": task_result.id}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error during processing: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

from tasks.train_task import train1key_celery

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        decoded_token = auth.verify_id_token(credentials.credentials)
        return decoded_token['uid']
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# user_id: str = Depends(verify_token)
@app.post("/train/")
async def train(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No audio files provided")

    # Create a unique folder for this training session
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    # Save uploaded files
    for file in files:
        if not file.filename.lower().endswith('.wav'):
            raise HTTPException(status_code=400, detail="Only .wav files are allowed")
        
        file_path = os.path.join(session_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    # Call the Celery task
    task = train1key_celery.delay(session_dir)

    return {"message": "Training started", "session_id": session_id, "task_id": task.id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)