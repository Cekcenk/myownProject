from celery import shared_task
from pydub import AudioSegment
import boto3
import os

@shared_task
def merge_audio(*args, processed_vocal_path, instrumental_path, final_output_path, bucket_name, s3_key):
    vocals = AudioSegment.from_file(processed_vocal_path)
    instrumental = AudioSegment.from_file(instrumental_path)
    final_output = instrumental.overlay(vocals)
    final_output.export(final_output_path, format="mp3")

    # Rename the final output file to unique_id.mp3
    unique_id = os.path.basename(final_output_path).split('.')[0]
    renamed_output_path = os.path.join(os.path.dirname(final_output_path), f"{unique_id}.mp3")
    os.rename(final_output_path, renamed_output_path)

    # Upload to S3
    s3 = boto3.client('s3')
    s3.upload_file(renamed_output_path, bucket_name, s3_key)
