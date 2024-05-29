from celeryconfig import app
import subprocess

@app.task
def separate_audio(input_path, model_name):
    subprocess.run(['audio-separator', input_path, '--model_filename', model_name])
    return "Separation complete"
