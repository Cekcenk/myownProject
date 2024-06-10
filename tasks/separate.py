from celery import shared_task
import sys
import os
import logging

logger = logging.getLogger(__name__)

# Ensure the path to my_audio_separator is added
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'my_audio_separator')))
from my_audio_separator.do_it import separate_audio

@shared_task
def separate_audio_task(*args, input_path, output_dir, ):
    print(input_path, output_dir)
    logger.info(f"Received input_path: {input_path}, output_dir: {output_dir}")
    result = separate_audio(input_path, output_dir)
