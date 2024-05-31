import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../my_audio_separator'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../fastapi-rvc'))


from fastapi import FastAPI, BackgroundTasks
from tasks.download import download_youtube_audio
from tasks.separate import separate_audio_task
from tasks.convert import convert_vocals
from tasks.merge import merge_audio
from celery import chain

app = FastAPI()

@app.post("/process/")
async def process(youtube_link: str, model_name: str, background_tasks: BackgroundTasks):
    output_path = "output.mp3"
    output_dir = "path_to_output_dir"  # Update with the correct path to your output directory
    chain(
        download_youtube_audio.s(youtube_link, output_path),
        separate_audio_task.s(output_path, output_dir),
        convert_vocals.s(os.path.join(output_dir, "vocals.wav"), model_name),
        merge_audio.s("processed_vocal.wav", os.path.join(output_dir, "instrumental.wav"), "final_output.mp3")
    ).apply_async()
    return {"message": "Processing started"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
