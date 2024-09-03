from fastapi_rvc.rvc.modules.train.preprocess import preprocess_dataset_internal
import threading
import os
import logging
from time import sleep  # Add this import

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sr_dict = {
    "32k": 32000,
    "40k": 40000,
    "48k": 48000,
}

now_dir = os.getcwd()

# def preprocess_dataset(trainset_dir, exp_dir, sr, n_p):
#     logger.info("Starting preprocess_dataset")
#     sr = sr_dict[sr]
#     os.makedirs(f"{now_dir}/logs/{exp_dir}", exist_ok=True)
#     log_file = f"{now_dir}/logs/{exp_dir}/preprocess.log"
    
#     with open(log_file, "w") as f:
#         f.write("")

#     def process_and_log():
#         try:
#             logger.info("Starting process_and_log")
#             log = preprocess_dataset_internal(trainset_dir, f"{now_dir}/logs/{exp_dir}", sr, n_p)
#             with open(log_file, "w") as f:
#                 f.write(log)
#             logger.info("Processing and logging completed successfully.")
#         except Exception as e:
#             logger.error(f"Error in process_and_log: {e}", exc_info=True)

#     # Call process_and_log directly instead of using a thread
#     process_and_log()

#     with open(log_file, "r") as f:
#         final_log = f.read()
#     logger.info(final_log)
#     yield final_log

# def preprocess_dataset(trainset_dir, exp_dir, sr, n_p):
#     logger.info("Starting preprocess_dataset")
#     sr = sr_dict[sr]
#     os.makedirs(f"{now_dir}/logs/{exp_dir}", exist_ok=True)
#     log_file = f"{now_dir}/logs/{exp_dir}/preprocess.log"
    
#     with open(log_file, "w") as f:
#         f.write("")

#     def process_and_log():
#         try:
#             logger.info("Starting process_and_log")
#             log = preprocess_dataset_internal(trainset_dir, f"{now_dir}/logs/{exp_dir}", sr, n_p)
#             with open(log_file, "w") as f:
#                 f.write(log)
#             logger.info("Processing and logging completed successfully.")
#         except Exception as e:
#             logger.error(f"Error in process_and_log: {e}", exc_info=True)

#     thread = threading.Thread(target=process_and_log)
#     thread.start()
#     logger.info("Thread started.")

#     while thread.is_alive():
#         with open(log_file, "r") as f:
#             yield f.read()
#         sleep(1)

#     with open(log_file, "r") as f:
#         final_log = f.read()
#     logger.info(final_log)
#     yield final_log