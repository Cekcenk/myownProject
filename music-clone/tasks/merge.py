from celery import shared_task
from scripts.merge import overlay_audio_files

@shared_task
def merge_audio(vocal_path, instrumental_path, output_path):
    overlay_audio_files(vocal_path, instrumental_path, output_path)
    return "Merge complete"
