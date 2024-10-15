from celery import chain, shared_task
import os
import logging
import multiprocessing
from multiprocessing import cpu_count
import numpy as np
from sklearn.cluster import MiniBatchKMeans
import faiss
import torch
import traceback
from subprocess import Popen, PIPE
import threading
from time import sleep
from rvc_webui.configs.config import Config

config = Config()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

now_dir = os.getcwd()

sr_dict = {
    "32k": 32000,
    "40k": 40000,
    "48k": 48000,
}

def if_done(done, p):
    while 1:
        if p.poll() is None:
            sleep(0.5)
        else:
            break
    done[0] = True

def if_done_multi(done, ps):
    while 1:
        flag = 1
        for p in ps:
            if p.poll() is None:
                flag = 0
                sleep(0.5)
                break
        if flag == 1:
            break
    done[0] = True

@shared_task
def preprocess_task(trainset_dir, exp_dir, sr, n_p):
    sr = sr_dict[sr]
    os.makedirs(exp_dir, exist_ok=True)
    log_file = os.path.join(exp_dir, "preprocess.log")
    
    cmd = f'"{config.python_cmd}" rvc_webui/infer/modules/train/preprocess.py "{trainset_dir}" {sr} {n_p} "{exp_dir}" {config.noparallel} {config.preprocess_per}'
    logger.info(f"Execute: {cmd}")
    
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, text=True)
    done = [False]
    threading.Thread(target=if_done, args=(done, p)).start()
    
    while not done[0]:
        output = p.stdout.readline()
        if output:
            logger.info(output.strip())
            with open(log_file, "a") as f:
                f.write(output)
        sleep(0.1)
    
    with open(log_file, "r") as f:
        log = f.read()
    logger.info(log)
    return "Preprocessing completed"

@shared_task
def extract_f0_task(*args, exp_dir, gpus, if_f0, version):
    log_file = os.path.join(exp_dir, "extract_f0_feature.log")
    
    if if_f0:
        f0_method = "rmvpe_gpu"  # You can make this configurable if needed
        cmd = f'"{config.python_cmd}" rvc_webui/infer/modules/train/extract/extract_f0_print.py "{exp_dir}" 4 {f0_method}'
        logger.info(f"Execute: {cmd}")
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, text=True)
        done = [False]
        threading.Thread(target=if_done, args=(done, p)).start()
        
        while not done[0]:
            output = p.stdout.readline()
            if output:
                logger.info(output.strip())
                with open(log_file, "a") as f:
                    f.write(output)
            sleep(0.1)
    
    gpus = gpus.split("-")
    ps = []
    for idx, n_g in enumerate(gpus):
        cmd = f'"{config.python_cmd}" rvc_webui/infer/modules/train/extract_feature_print.py {config.device} {len(gpus)} {idx} {n_g} "{exp_dir}" {version} {config.is_half}'
        logger.info(f"Execute: {cmd}")
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, text=True)
        ps.append(p)
    
    done = [False]
    threading.Thread(target=if_done_multi, args=(done, ps)).start()
    
    while not done[0]:
        for p in ps:
            output = p.stdout.readline()
            if output:
                logger.info(output.strip())
                with open(log_file, "a") as f:
                    f.write(output)
        sleep(0.1)
    
    with open(log_file, "r") as f:
        log = f.read()
    logger.info(log)
    return "F0 and feature extraction completed"

@shared_task
def train_task(*args, exp_dir, sr, if_f0, save_epoch, total_epoch, batch_size, if_save_latest, gpus, if_cache_gpu, version):
    log_file = os.path.join(exp_dir, "train.log")
    
    cmd = f'"{config.python_cmd}" rvc_webui/infer/modules/train/train.py -e "{exp_dir}" -sr {sr} -f0 {1 if if_f0 else 0} -bs {batch_size} -g {gpus} -te {total_epoch} -se {save_epoch} -l {1 if if_save_latest else 0} -c {1 if if_cache_gpu else 0} -v {version}'
    logger.info(f"Execute: {cmd}")
    
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, text=True)
    done = [False]
    threading.Thread(target=if_done, args=(done, p)).start()
    
    while not done[0]:
        output = p.stdout.readline()
        if output:
            logger.info(output.strip())
            with open(log_file, "a") as f:
                f.write(output)
        sleep(0.1)
    
    with open(log_file, "r") as f:
        log = f.read()
    logger.info(log)
    return "Training completed"

@shared_task
def train1key_celery(session_dir):
    exp_dir = os.path.join(now_dir, "logs", os.path.basename(session_dir))
    sr = "40k"
    if_f0 = True
    np = cpu_count() // 2
    save_epoch = 5
    total_epoch = 20
    batch_size = 4
    if_save_latest = False
    gpus = "0"
    if_cache_gpu = False
    version = "v2"

    # Create a Celery chain of tasks
    task_chain = chain(
        preprocess_task.s(trainset_dir=session_dir, exp_dir=exp_dir, sr=sr, n_p=np),
        extract_f0_task.s(exp_dir=exp_dir, gpus=gpus, if_f0=if_f0, version=version),
        train_task.s(exp_dir=exp_dir, sr=sr, if_f0=if_f0, save_epoch=save_epoch, 
                     total_epoch=total_epoch, batch_size=batch_size, 
                     if_save_latest=if_save_latest, gpus=gpus, 
                     if_cache_gpu=if_cache_gpu, version=version)
    )
    
    # Execute the chain
    result = task_chain.apply_async()
    
    # Return the task ID
    return result.id
