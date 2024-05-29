from pathlib import Path
from scipy.io import wavfile
from rvc.modules.vc.modules import VC
from dotenv import load_dotenv
import os

class RVCService:
    def __init__(self, model_path: str, env_path: str):
        load_dotenv(env_path)
        self.model_path = model_path
        self.vc = VC()

        # Debugging: Print all environment variables
        print("Loaded .env variables:")
        for key, value in os.environ.items():
            print(f"{key}: {value}")

        # Verify specific variables
        index_root = os.getenv("index_root")
        if not index_root:
            raise ValueError("index_root is not set in the environment variables")
        print(f"index_root: {index_root}")

        self.vc.get_vc(model_path)

    def convert_voice(self, input_path: str, output_path: str):
        tgt_sr, audio_opt, times, _ = self.vc.vc_inference(1, Path(input_path))
        wavfile.write(output_path, tgt_sr, audio_opt)
        return output_path
