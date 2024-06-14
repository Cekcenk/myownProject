import boto3
import os

def download_file_from_s3(s3_path, local_path):
    if not os.path.exists(local_path):
        s3 = boto3.client('s3')
        bucket, key = s3_path.replace("s3://", "").split("/", 1)
        s3.download_file(bucket, key, local_path)
        print(f"Downloaded {s3_path} to {local_path}")
    else:
        print(f"File already cached at {local_path}")

def download_model_files(model_info, local_model_dir):
    pth_local_path = os.path.join(local_model_dir, os.path.basename(model_info['pth_s3_path']))
    index_local_path = os.path.join(local_model_dir, os.path.basename(model_info['index_s3_path']))

    download_file_from_s3(model_info['pth_s3_path'], pth_local_path)
    download_file_from_s3(model_info['index_s3_path'], index_local_path)

    return pth_local_path, index_local_path

