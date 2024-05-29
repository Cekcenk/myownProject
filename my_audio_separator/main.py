from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import shutil
import os
from do_it import separate_audio
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

UPLOAD_DIR = "./uploads"
OUTPUT_DIR = "./static"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.post("/separate/")
async def separate(file: UploadFile = File(...)):
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.debug("File saved at: %s", file_location)

        vocals_path, instrumentals_path = separate_audio(file_location, OUTPUT_DIR)

        logger.debug("Separation paths: Vocals - %s, Instrumentals - %s", vocals_path, instrumentals_path)

        return {
            "vocals": os.path.basename(vocals_path),
            "instrumentals": os.path.basename(instrumentals_path)
        }
    except Exception as e:
        logger.error("Error in API endpoint: %s", e)
        return {"error": str(e)}
    finally:
        if os.path.exists(file_location):
            os.remove(file_location)

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = f"{OUTPUT_DIR}/{filename}"
    return FileResponse(path=file_path, filename=filename)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down gracefully")
