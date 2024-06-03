from my_audio_separator.do_it import separate_audio
from celery import shared_task

@shared_task
def separate_audio_task(input_path, output_dir):
    result = separate_audio(input_path, output_dir)
    return "Separation complete"
