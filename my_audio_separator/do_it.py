from python_audio_separator.audio_separator.separator import Separator
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def separate_audio(input_file: str, output_dir: str):
    try:
        logger.debug("Initializing Separator")
        separator = Separator(output_dir=output_dir)

        logger.debug("Loading model")
        separator.load_model(model_filename="MDX23C-8KFFT-InstVoc_HQ.ckpt")

        logger.debug("Checking model instance")
        if separator.model_instance is None:
            logger.error("Model instance is None after loading the model")
            raise ValueError("Model instance is None")

        logger.debug("Starting separation")
        result = separator.separate(input_file)

        logger.debug("Separation complete")
        return result
    except Exception as e:
        logger.error("Error during separation: %s", e)
        raise
