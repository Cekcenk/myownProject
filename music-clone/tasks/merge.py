from celeryconfig import app
from scripts.merge import overlay_audio_files

@app.task
def merge_audio(vocal_path, instrumental_path, output_path):
    overlay_audio_files(vocal_path, instrumental_path, output_path)
    return "Merge complete"
