import sys
import os
from celery import shared_task

# Ensure the path to my_audio_separator is added
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'my_audio_separator')))
from my_audio_separator.do_it import separate_audio

@shared_task
def separate_audio_task(input_path, output_dir):
    result = separate_audio(input_path, output_dir)
    return "Separation complete"
