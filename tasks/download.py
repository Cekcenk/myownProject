import logging
from celery import shared_task
from scripts.ytdwnld import download_mp3

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@shared_task
def download_youtube_audio(youtube_url, output_path):
    logger.info(f"Starting download: {youtube_url} to {output_path}")
    download_mp3(youtube_url, output_path)
    logger.info(f"Download complete: {output_path}")
    return "Download complete"
