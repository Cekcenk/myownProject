from celery import shared_task
from fastapi_rvc.app.rvc_service  import RVCService
import os

@shared_task
def convert_vocals(input_vocal_path, model_name):
    env_path = ".env"  # Update with the correct path to your .env file
    rvc_service = RVCService("dio.pth", env_path)
    output_path = "processed_vocal.wav"
    rvc_service.convert_voice(input_vocal_path, output_path)
    return "Conversion complete"
