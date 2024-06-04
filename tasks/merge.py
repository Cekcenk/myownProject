from celery import shared_task
from pydub import AudioSegment

@shared_task
def merge_audio(processed_vocal_path, instrumental_path, final_output_path):
    vocals = AudioSegment.from_file(processed_vocal_path)
    instrumental = AudioSegment.from_file(instrumental_path)
    final_output = instrumental.overlay(vocals)
    final_output.export(final_output_path, format="mp3")
    return None
