import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up the Celery application
from celeryconfig import app

if __name__ == '__main__':
    app.start()
