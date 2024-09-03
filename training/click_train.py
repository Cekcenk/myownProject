from fastapi_rvc.rvc.modules.train.train import start_training
import threading
import os
from time import sleep
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def click_train(
    exp_dir1,
    sr2,
    if_f0_3,
    spk_id5,
    save_epoch10,
    total_epoch11,
    batch_size12,
    if_save_latest13,
    pretrained_G14,
    pretrained_D15,
    gpus16,
    if_cache_gpu17,
    if_save_every_weights18,
    version19,
):
    exp_dir = f"{now_dir}/logs/{exp_dir1}"
    os.makedirs(exp_dir, exist_ok=True)
    log_file = f"{exp_dir}/train.log"
    
    with open(log_file, "w") as f:
        f.write("")

    def process_and_log():
        log = start_training(
            model_dir=exp_dir,
            n_gpus=len(gpus16.split('-')),
            logger=logger,
            save_every_epoch=save_epoch10,
            total_epoch=total_epoch11,
            batch_size=batch_size12,
            experiment_dir=exp_dir1,
            sample_rate=sr2,
            if_f0=if_f0_3,
            if_latest=if_save_latest13,
            if_cache_data_in_gpu=if_cache_gpu17,
            version=version19
        )
        with open(log_file, "w") as f:
            f.write(log)

    thread = threading.Thread(target=process_and_log)
    thread.start()

    while thread.is_alive():
        with open(log_file, "r") as f:
            yield f.read()
        sleep(1)

    with open(log_file, "r") as f:
        final_log = f.read()
    logger.info(final_log)
    yield final_log