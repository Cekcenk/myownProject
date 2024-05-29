from celeryconfig import app
import subprocess

@app.task
def convert_vocals(input_vocal_path, model_name):
    subprocess.run(['python', 'scripts/fastapi-rvc.py', input_vocal_path, model_name])
    return "Conversion complete"
