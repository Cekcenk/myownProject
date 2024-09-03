from celery import chain, shared_task
# from training.preprocess import preprocess_dataset
from training.extract_feature import extract_f0_feature
from training.click_train import click_train
from multiprocessing import cpu_count
import os
import logging
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

@shared_task
def preprocess_task(trainset_dir, exp_dir, sr, n_p):
    logger.info("Starting preprocess_task")
    logger.info("Starting preprocess_dataset")
    sr = sr_dict[sr]
    os.makedirs(f"{now_dir}/logs/{exp_dir}", exist_ok=True)
    log_file = f"{now_dir}/logs/{exp_dir}/preprocess.log"
    
    with open(log_file, "w") as f:
        f.write("")

    def process_and_log():
        try:
            logger.info("Starting process_and_log")
            log = preprocess_dataset_internal(trainset_dir, f"{now_dir}/logs/{exp_dir}", sr, n_p)
            with open(log_file, "w") as f:
                f.write(log)
            logger.info("Processing and logging completed successfully.")
        except Exception as e:
            logger.error(f"Error in process_and_log: {e}", exc_info=True)

    thread = threading.Thread(target=process_and_log)
    thread.start()
    logger.info("Thread started.")

    while thread.is_alive():
        sleep(1)

    with open(log_file, "r") as f:
        final_log = f.read()
    logger.info(final_log)
    logger.info("Completed preprocess_task")

@shared_task
def extract_f0_task(*args, gpus, n_p, f0method, if_f0, exp_dir, version):
    extract_f0_feature(gpus, n_p, f0method, if_f0, exp_dir, version)

@shared_task
def train_task(*args, exp_dir, sr, if_f0, spk_id, save_epoch, total_epoch, batch_size, if_save_latest, pretrained_G, pretrained_D, gpus, if_cache_gpu, if_save_every_weights, version):
    click_train(exp_dir, sr, if_f0, spk_id, save_epoch, total_epoch, batch_size, if_save_latest, pretrained_G, pretrained_D, gpus, if_cache_gpu, if_save_every_weights, version)

@shared_task
def train1key_celery(session_dir):
    # Static parameters
    exp_dir = os.path.basename(session_dir)
    sr = "40k"
    if_f0 = True
    spk_id = 0
    np = cpu_count() // 2  # Use half of available CPU cores
    f0method = "rmvpe_gpu"
    save_epoch = 5
    total_epoch = 20
    batch_size = 4
    if_save_latest = False
    pretrained_G = "fastapi_rvc/assets/pretrained_v2/f0G40k.pth"
    pretrained_D = "fastapi_rvc/assets/pretrained_v2/f0D40k.pth"
    gpus = "0"
    if_cache_gpu = False
    if_save_every_weights = False
    version = "v2"
    gpus_rmvpe = "0"

    exp_dir_full = f"{os.getcwd()}/logs/{exp_dir}"

    # preprocess_dataset(trainset_dir=session_dir, exp_dir=exp_dir_full, sr=sr, n_p=np)
    # extract_f0_feature(gpus=gpus, n_p=np, f0method=f0method, if_f0=if_f0, exp_dir=exp_dir_full, version19=version)
    # click_train(exp_dir1=exp_dir_full, sr2=sr, if_f0_3=if_f0, spk_id5=spk_id, save_epoch10=save_epoch, total_epoch11=total_epoch, batch_size12=batch_size, if_save_latest13=if_save_latest, pretrained_G14=pretrained_G, pretrained_D15=pretrained_D, gpus16=gpus, if_cache_gpu17=if_cache_gpu, if_save_every_weights18=if_save_every_weights, version19=version)    


    # Create a Celery chain of tasks
    task_chain = chain(
        preprocess_task.s(trainset_dir=session_dir, exp_dir=exp_dir_full, sr=sr, n_p=np),
        extract_f0_task.s(gpus=gpus, n_p=np, f0method=f0method, if_f0=if_f0, exp_dir=exp_dir, version=version),
        train_task.s(exp_dir=exp_dir, sr=sr, if_f0=if_f0, spk_id=spk_id, save_epoch=save_epoch, total_epoch=total_epoch, batch_size=batch_size, if_save_latest=if_save_latest, pretrained_G=pretrained_G, pretrained_D=pretrained_D, gpus=gpus, if_cache_gpu=if_cache_gpu, if_save_every_weights=if_save_every_weights, version=version)
    )

   
   
    # Execute the chain
    result = task_chain.apply_async()

    # Return the task ID
    return result.id