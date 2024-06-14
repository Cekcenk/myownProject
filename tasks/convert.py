from celery import shared_task
from fastapi_rvc.app.rvc_service import RVCService

@shared_task
def convert_vocals(*args, vocal_path, model_name, processed_vocal_path):
    rvc_service = RVCService(model_path=model_name, env_path="fastapi_rvc/.env")
    rvc_service.convert_voice(vocal_path, processed_vocal_path)

# def convert_vocals(*args, vocal_path, model_name, processed_vocal_path):
#     rvc_service = RVCService()
#     rvc_service.convert(vocal_path, model_name, processed_vocal_path)

