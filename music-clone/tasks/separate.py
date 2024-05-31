from celery import shared_task
from do_it import separate_audio

@shared_task
def separate_audio_task(input_path, output_dir):
    result = separate_audio(input_path, output_dir)
    return "Separation complete"
