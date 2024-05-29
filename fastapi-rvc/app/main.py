from fastapi import FastAPI, UploadFile, File
from app.rvc_service import RVCService
from pathlib import Path

app = FastAPI()

# Initialize the RVCService with the model and .env path
rvc_service = RVCService(model_path="dio.pth", env_path=".env")

@app.post("/convert")
async def convert_voice(file: UploadFile = File(...)):
    input_path = f"{file.filename}"
    output_path = f"output/converted_{file.filename}"

    # Save the uploaded file
    with open(input_path, "wb") as f:
        f.write(await file.read())

    # Convert the voice
    rvc_service.convert_voice(input_path, output_path)

    return {"output_file": output_path}
