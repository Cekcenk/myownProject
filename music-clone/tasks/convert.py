from celeryconfig import app
from app.rvc_service import RVCService
import os

@app.task
def convert_vocals(input_vocal_path, model_name):
    model_path = os.path.join("path_to_your_models", model_name)  # Update with the correct path to your models
    env_path = "path_to_your_env_file"  # Update with the correct path to your .env file

    rvc_service = RVCService(model_path, env_path)
    output_path = "processed_vocal.wav"
    rvc_service.convert_voice(input_vocal_path, output_path)
    return "Conversion complete"
