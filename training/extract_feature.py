import os
import multiprocessing
import threading
import time
import logging
from fastapi_rvc.rvc.modules.train.extract.extract_f0_rmvpe_dml import extract_f0_rmvpe_dml
from fastapi_rvc.rvc.modules.train.extract.extract_f0_rmvpe import extract_f0_feature_rmvpe
from fastapi_rvc.rvc.modules.train.extract.extract_f0_print import extract_f0_print, extract_f0_feature_print
from fastapi_rvc.rvc.modules.train.extract_feature_print import extract_features

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_rmvpe(exp_dir, n_parts, gpu_index, use_half_precision):
    for i in range(n_parts):
        extract_f0_feature_rmvpe(exp_dir, n_parts, i, gpu_index, use_half_precision)

def extract_f0_feature_method(exp_dir, use_dml=False):
    if use_dml:
        extract_f0_rmvpe_dml(exp_dir)

def extract_f0_feature_method(exp_dir, n_parts, f0method, use_multiprocessing=True):
    if use_multiprocessing:
        extract_f0_print(exp_dir, n_parts, f0method)
    else:
        for i in range(n_parts):
            extract_f0_feature_print(exp_dir, n_parts, i, f0method)



def extract_feature_print(device, n_part, i_part, i_gpu, exp_dir, version, is_half):
    extract_features(device, n_part, i_part, i_gpu, exp_dir, version, is_half)
    

def extract_f0_feature(gpus, n_p, f0method, if_f0, exp_dir, version19):
    gpus = gpus.split("-")
    os.makedirs(f"{exp_dir}/logs", exist_ok=True)
    log_file = f"{exp_dir}/logs/extract_f0_feature.log"
    
    with open(log_file, "w") as f:
        f.write("")

    def process_and_log():
        if if_f0:
            if f0method != "rmvpe_gpu":
                extract_f0_print(exp_dir, n_p, f0method)
            else:
                if gpus_rmvpe != "-":
                    gpus_rmvpe = gpus_rmvpe.split("-")
                    processes = []
                    for idx, n_g in enumerate(gpus_rmvpe):
                        p = multiprocessing.Process(
                            target=extract_rmvpe,
                            args=(len(gpus_rmvpe), idx, n_g, exp_dir, False)
                        )
                        processes.append(p)
                        p.start()
                    for p in processes:
                        p.join()
                else:
                    extract_f0_rmvpe_dml(exp_dir)

            with open(log_file, "a") as f:
                f.write("F0 extraction completed.\n")

        # Feature extraction
        for idx, n_g in enumerate(gpus):
            extract_feature_print(n_g, len(gpus), idx, exp_dir, version19, False)

        with open(log_file, "a") as f:
            f.write("Feature extraction completed.")

    thread = threading.Thread(target=process_and_log)
    thread.start()

    while thread.is_alive():
        with open(log_file, "r") as f:
            yield f.read()
        time.sleep(1)

    with open(log_file, "r") as f:
        final_log = f.read()
    logger.info(final_log)
    yield final_log