import sys
import os
import uuid
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from celery import chain
from celery_app import app as celery_app

from tasks.download import download_youtube_audio
from tasks.separate import separate_audio_task
from tasks.convert import convert_vocals
from tasks.merge import merge_audio
from tasks.update_status import update_status
from task_status import task_status

app = FastAPI()

class ProcessRequest(BaseModel):
    youtube_link: str
    model_name: str

import logging

logger = logging.getLogger(__name__)

@app.post("/process/")
async def process(request: ProcessRequest, background_tasks: BackgroundTasks):
    unique_id = str(uuid.uuid4())
    output_path = f"downloads/{unique_id}"
    input_path = f"{output_path}.mp3"
    output_dir = f"outputs/{unique_id}"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    vocal_path = f"{output_dir}/{unique_id}_(Vocals)_MDX23C-8KFFT-InstVoc_HQ.wav"
    instrumental_path = f"{output_dir}/{unique_id}_(Instrumental)_MDX23C-8KFFT-InstVoc_HQ.wav"
    processed_vocal_path = f"{output_dir}/processed_vocal.wav"
    final_output_path = f"{output_dir}/final_output.mp3"

    # Initialize task status
    task_status[unique_id] = "0/4"

    logger.info(f"Starting process with output_path: {output_path} and output_dir: {output_dir}")

    # Create the task chain
    task_chain = (
        download_youtube_audio.s(youtube_url=request.youtube_link, output_path=output_path) |
        update_status.s(task_id=unique_id, status="1/4") |
        separate_audio_task.s(input_path=input_path, output_dir=output_dir) |
        update_status.s(task_id=unique_id, status="2/4") |
        convert_vocals.s(vocal_path=vocal_path, model_name=request.model_name, processed_vocal_path=processed_vocal_path) |
        # convert_vocals.s(vocal_path="outputs/e0d8fe2f-f0e5-4eb6-ad80-6123a4251b79/e0d8fe2f-f0e5-4eb6-ad80-6123a4251b79_(Vocals)_MDX23C-8KFFT-InstVoc_HQ.wav", model_name=request.model_name, processed_vocal_path=processed_vocal_path) |
        update_status.s(task_id=unique_id, status="3/4") |
        merge_audio.s(processed_vocal_path=processed_vocal_path, instrumental_path=instrumental_path, final_output_path=final_output_path) |
        update_status.s(task_id=unique_id, status="4/4")
    )

    task_chain.apply_async()

    background_tasks.add_task(cleanup_files, [output_path, vocal_path, instrumental_path, processed_vocal_path])

    return {"message": "Processing started", "id": unique_id}

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    return {"task_id": task_id, "status": task_status.get(task_id, "Task not found")}

async def cleanup_files(files):
    for file in files:
        if os.path.exists(file):
            os.remove(file)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
