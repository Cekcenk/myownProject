from dotenv import load_dotenv
import os

load_dotenv('.env')

print("Loaded .env variables:")
for key, value in os.environ.items():
    print(f"{key}: {value}")

index_root = os.getenv("index_root")
print(f"index_root: {index_root}")
