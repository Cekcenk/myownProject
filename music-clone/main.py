from fastapi import FastAPI, BackgroundTasks
from tasks.download import download_youtube_audio
from tasks.separate import separate_audio
from tasks.convert import convert_vocals
from tasks.merge import merge_audio
from celery import chain

app = FastAPI()

@app.post("/process/")
async def process(youtube_link: str, model_name: str, background_tasks: BackgroundTasks):
    output_path = "output.mp3"
    chain(
        download_youtube_audio.s(youtube_link, output_path),
        separate_audio.s(output_path, model_name),
        convert_vocals.s("vocal.wav", model_name),
        merge_audio.s("processed_vocal.wav", "instrumental.wav", "final_output.mp3")
    ).apply_async()
    return {"message": "Processing started"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
