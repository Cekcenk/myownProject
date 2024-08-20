from celery import shared_task
from celery.utils.log import get_task_logger
from tasks.download import download_youtube_audio
from tasks.separate import separate_audio_task
from tasks.convert import convert_vocals
from tasks.merge import merge_audio
from tasks.cleanup_files import cleanup_files
from tasks.update_status import update_status, finish_status, send_fcm_notification
import torch

logger = get_task_logger(__name__)

@shared_task(bind=True)
def process_audio_task(self, youtube_url, output_path, output_dir, input_path, vocal_path, 
                       pth_local_path, processed_vocal_path, instrumental_path, final_output_path, 
                       user_id, task_id, video_title, full_video, S3_BUCKET_NAME, S3_KEY, unique_id ):
    try:
        # Download
        download_youtube_audio(youtube_url=youtube_url, output_path=output_path, full_video=full_video)
        update_status(user_id=user_id, task_id=task_id, status="1/4")

        # Separate
        separate_audio_task(input_path=input_path, output_dir=output_dir)
        update_status(user_id=user_id, task_id=task_id, status="2/4")

        # Convert
        try:
            convert_vocals(vocal_path=vocal_path, pth_local_path=pth_local_path, processed_vocal_path=processed_vocal_path)
        except ValueError as e:
            logger.error(f"Error in convert_vocals: {str(e)}")
            raise
        update_status(user_id=user_id, task_id=task_id, status="3/4")

        # Merge
        merge_audio(
                processed_vocal_path=processed_vocal_path,
                instrumental_path=instrumental_path,
                final_output_path=final_output_path,
                bucket_name=S3_BUCKET_NAME,
                s3_key=f'{unique_id}.mp3'
            )
        # Finish and cleanup
        finish_status(user_id=user_id, task_id=unique_id, s3_url=f'https://{S3_BUCKET_NAME}.s3.amazonaws.com/{unique_id}.mp3')
        cleanup_files(processed_vocal_path=processed_vocal_path, instrumental_path=instrumental_path, directories=[output_dir, output_path])
        send_fcm_notification(
                user_id=user_id,
                message_title="Generation Complete",
                message_body=f"Your audio processing task {video_title} is complete."
            )
        update_status(user_id=user_id, task_id=task_id, status="4/4")

        # GPU memory cleanup
        torch.cuda.empty_cache()
        
        return "Processing completed successfully"
    except Exception as e:
        logger.error(f"Error in process_audio_task: {str(e)}", exc_info=True)
        self.update_state(state='FAILURE', meta={
            'exc_type': type(e).__name__,
            'exc_message': str(e),
        })
        raise