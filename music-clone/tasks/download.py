from celeryconfig import app
from scripts.ytdwnld import download_mp3

@app.task
def download_youtube_audio(youtube_url, output_path):
    download_mp3(youtube_url, output_path)
    return "Download complete"
