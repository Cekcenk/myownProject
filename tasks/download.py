import logging
from celery import shared_task
from scripts.ytdwnld import download_mp3

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def download_youtube_audio(self, youtube_url, output_path, full_video):
    logger.info(f"Starting download: {youtube_url} to {output_path}")
    try:
        success = download_mp3(youtube_url, output_path, full_video)
        if success:
            logger.info(f"Download complete: {output_path}")
            return output_path
        else:
            raise Exception("Download failed")
    except Exception as exc:
        logger.error(f"Error downloading {youtube_url}: {str(exc)}")
        try:
            self.retry(exc=exc, countdown=60)  # Retry after 60 seconds
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for {youtube_url}")
            raise
    return None