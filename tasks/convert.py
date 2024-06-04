from celery import shared_task
from fastapi_rvc.app.rvc_service import RVCService

@shared_task
def convert_vocals(vocal_path, model_name, processed_vocal_path):
    rvc_service = RVCService()
    rvc_service.convert(vocal_path, model_name, processed_vocal_path)
    return None
