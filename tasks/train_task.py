# from celery import chain, shared_task
# # from training.preprocess import preprocess_dataset

# import os
# import logging
# import multiprocessing
# from multiprocessing import cpu_count
# from fastapi_rvc.rvc.modules.train.preprocess import preprocess_dataset_internal
# from fastapi_rvc.rvc.modules.train.train import start_training



# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# sr_dict = {
#     "32k": 32000,
#     "40k": 40000,
#     "48k": 48000,
# }

# now_dir = os.getcwd()

# @shared_task
# def preprocess_task(trainset_dir, exp_dir, sr, n_p):
#     logger.info("Starting preprocess_task")
#     logger.info("Starting preprocess_dataset")
#     sr = sr_dict[sr]
#     log_dir = os.path.join(now_dir, "logs", exp_dir)
#     os.makedirs(log_dir, exist_ok=True)
#     log_file_path = os.path.join(log_dir, "preprocess.log")
    
#     with open(log_file_path, "w") as f:
#         f.write("")

#     def process_and_log():
#         try:
#             logger.info("Starting process_and_log")
#             log = preprocess_dataset_internal(trainset_dir, log_dir, sr, n_p, log_file_path=log_file_path)
#             if log:
#                 logger.info("Processing and logging completed successfully.")
#             else:
#                 logger.warning("No log data returned from preprocess_dataset_internal")
#         except Exception as e:
#             logger.error(f"Error in process_and_log: {e}", exc_info=True)

#     process_and_log()

#     with open(log_file_path, "r") as f:
#         final_log = f.read()
#     logger.info(final_log)
#     logger.info("Completed preprocess_task")

# @shared_task
# def extract_f0_task(*args, exp_dir, gpus, if_f0, version):
#     from fastapi_rvc.rvc.modules.train.extract.extract_f0_rmvpe import extract_f0_feature_rmvpe
#     from fastapi_rvc.rvc.modules.train.extract_feature_print import extract_features
#     import torch

#     log_dir = os.path.join(now_dir, "logs", exp_dir)
#     os.makedirs(log_dir, exist_ok=True)
#     log_file = os.path.join(log_dir, "extract_f0_feature.log")
    
#     with open(log_file, "w") as f:
#         f.write("")

#     gpus = gpus.split("-")
#     n_gpus = len(gpus)

#     if if_f0:
#         # F0 extraction using RMVPE (on CPU)
#         for idx, _ in enumerate(gpus):
#             extract_f0_feature_rmvpe(log_dir, n_gpus, idx, "cpu", False)

#         with open(log_file, "a") as f:
#             f.write("F0 extraction completed.\n")

#     # Feature extraction
#     device = "cpu"  # Use CPU as fallback
#     if torch.cuda.is_available():
#         device = "cuda"
#     elif torch.backends.mps.is_available():
#         device = "mps"

#     for idx, _ in enumerate(gpus):
#         extract_features(device, n_gpus, idx, log_dir, version, False, is_half=False)

#     with open(log_file, "a") as f:
#         f.write("Feature extraction completed.")

#     with open(log_file, "r") as f:
#         final_log = f.read()
#     logger.info(final_log)
#     return final_log

# @shared_task
# def train_task(*args, exp_dir, sr, if_f0, save_epoch, total_epoch, batch_size, if_save_latest, gpus, if_cache_gpu, version):
#     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
#     logger = logging.getLogger(__name__)

#     now_dir = os.getcwd()
#     exp_dir_full = f"{now_dir}/logs/{exp_dir}"
#     os.makedirs(exp_dir_full, exist_ok=True)
#     log_file = f"{exp_dir_full}/train.log"
    
#     with open(log_file, "w") as f:
#         f.write("")

#     def process_and_log():
#         try:
#             log = start_training(
#                 model_dir=exp_dir_full,
#                 n_gpus=len(gpus.split('-')),
#                 logger=logger,
#                 save_every_epoch=save_epoch,
#                 total_epoch=total_epoch,
#                 batch_size=batch_size,
#                 experiment_dir=exp_dir,
#                 sample_rate=sr,
#                 if_f0=if_f0,
#                 if_latest=if_save_latest,
#                 if_cache_data_in_gpu=if_cache_gpu,
#                 version=version,
#             )
#             with open(log_file, "w") as f:
#                 f.write(log)
#         except Exception as e:
#             logger.error(f"Error in process_and_log: {e}", exc_info=True)

#     process_and_log()

#     with open(log_file, "r") as f:
#         final_log = f.read()
#     logger.info(final_log)
#     return "Training completed"

# @shared_task
# def train1key_celery(session_dir):
#     # Static parameters
#     exp_dir = os.path.basename(session_dir)
#     sr = "40k"
#     if_f0 = True
#     spk_id = 0
#     np = cpu_count() // 2  # Use half of available CPU cores
#     f0method = "rmvpe_gpu"
#     save_epoch = 5
#     total_epoch = 20
#     batch_size = 4
#     if_save_latest = False
#     pretrained_G = "fastapi_rvc/assets/pretrained_v2/f0G40k.pth"
#     pretrained_D = "fastapi_rvc/assets/pretrained_v2/f0D40k.pth"
#     gpus = "0"
#     if_cache_gpu = False
#     if_save_every_weights = False
#     version = "v2"
#     gpus_rmvpe = "0"

#     exp_dir_full = f"{os.getcwd()}/logs/{exp_dir}"

#     # preprocess_dataset(trainset_dir=session_dir, exp_dir=exp_dir_full, sr=sr, n_p=np)
#     # extract_f0_feature(gpus=gpus, n_p=np, f0method=f0method, if_f0=if_f0, exp_dir=exp_dir_full, version19=version)
#     # click_train(exp_dir1=exp_dir_full, sr2=sr, if_f0_3=if_f0, spk_id5=spk_id, save_epoch10=save_epoch, total_epoch11=total_epoch, batch_size12=batch_size, if_save_latest13=if_save_latest, pretrained_G14=pretrained_G, pretrained_D15=pretrained_D, gpus16=gpus, if_cache_gpu17=if_cache_gpu, if_save_every_weights18=if_save_every_weights, version19=version)    


#     # Create a Celery chain of tasks
#     task_chain = chain(
#         preprocess_task.s(trainset_dir=session_dir, exp_dir=exp_dir_full, sr=sr, n_p=np),
#         extract_f0_task.s(exp_dir=exp_dir_full, gpus=gpus, if_f0=if_f0, version=version),
#         train_task.s(exp_dir=exp_dir, sr=sr, if_f0=if_f0, save_epoch=save_epoch, total_epoch=total_epoch, batch_size=batch_size, if_save_latest=if_save_latest, gpus=gpus, if_cache_gpu=if_cache_gpu, version=version)
#     )

   
   
#     # Execute the chain
#     result = task_chain.apply_async()

#     # Return the task ID
#     return result.id