import os
import shutil
from celery import shared_task


@shared_task
def cleanup_files(*args, processed_vocal_path, instrumental_path, directories):
    # Remove individual files
    for file_path in [processed_vocal_path, instrumental_path]:
        try:
            os.remove(file_path)
        except OSError as e:
            print(f"Error: {file_path} : {e.strerror}")

    # Remove directories
    for directory in directories:
        try:
            shutil.rmtree(directory, ignore_errors=True)
        except OSError as e:
            print(f"Error: {directory} : {e.strerror}")

    # Remove the .mp3 file
    for directory in directories:
        try:
            os.remove(f"{directory}.mp3")
        except OSError as e:
            print(f"Error: {directory}.mp3 : {e.strerror}")
