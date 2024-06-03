import sys
import os

# Add necessary paths to the PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'my_audio_separator')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'fastapi-rvc')))

from celeryconfig import app

if __name__ == '__main__':
    app.start()
