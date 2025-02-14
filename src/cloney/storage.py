import os
import boto3
from google.cloud import storage as gcs_storage
import oss2
from azure.storage.blob import BlobServiceClient
import concurrent.futures
from cloney.logger import logging
from cloney.utils import time_logger


@time_logger
def download_from_source(source_service, source_bucket, local_dir):
    if source_service == "s3":
        download_s3_bucket(source_bucket, local_dir)
    elif source_service == "gcs":
        download_gcs_bucket(source_bucket, local_dir)
    elif source_service == "oss":
        download_oss_bucket(source_bucket, local_dir)
    elif source_service == "azure":
        download_azure_bucket(source_bucket, local_dir)
    else:
        raise ValueError(f"Unsupported source service: {source_service}")

@time_logger
def upload_to_destination(destination_service, destination_bucket, local_dir):
    if destination_service == "s3":
        upload_to_s3_bucket(destination_bucket, local_dir)
    elif destination_service == "gcs":
        upload_to_gcs_bucket(destination_bucket, local_dir)
    elif destination_service == "oss":
        upload_to_oss_bucket(destination_bucket, local_dir)
    elif destination_service == "azure":
        upload_to_azure_bucket(destination_bucket, local_dir)
    else:
        raise ValueError(f"Unsupported destination service: {destination_service}")

# --- Download Functions ---
def download_s3_file(bucket_name, object_key, local_dir, worker_id):
    s3 = boto3.client("s3")
    local_path = os.path.join(local_dir, object_key)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    try:
        s3.download_file(bucket_name, object_key, local_path)
    except Exception as e:
        logging.warning(f"Worker {worker_id}: Failed to download {object_key} from S3 - {e}")

def download_s3_bucket(bucket_name, local_dir):
    s3 = boto3.client("s3")
    response = s3.list_objects_v2(Bucket=bucket_name)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for obj in response.get("Contents", []):
            object_key = obj["Key"]
            worker_id = len(futures)  # Assigning worker ID
            futures.append(executor.submit(download_s3_file, bucket_name, object_key, local_dir, worker_id))
        concurrent.futures.wait(futures)

# --- Google Cloud Storage Functions ---

def download_gcs_file(bucket_name, blob_name, local_dir, worker_id):
    client = gcs_storage.Client()
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    # Ensure forward slashes are used in GCS blob names
    local_path = os.path.join(local_dir, blob_name.replace('/', os.sep))
    
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    try:
        blob.download_to_filename(local_path)
        logging.info(f"Worker {worker_id}: Successfully downloaded {blob_name}")
    except Exception as e:
        logging.warning(f"Worker {worker_id}: Failed to download {blob_name} from GCS - {e}")

def download_gcs_bucket(bucket_name, local_dir):
    client = gcs_storage.Client()
    bucket = client.get_bucket(bucket_name)
    blobs = bucket.list_blobs()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for blob in blobs:
            worker_id = len(futures)  # Assigning worker ID
            futures.append(executor.submit(download_gcs_file, bucket_name, blob.name, local_dir, worker_id))
        concurrent.futures.wait(futures)

# --- Alibaba Cloud OSS Functions ---

def download_oss_file(bucket_name, object_key, local_dir, worker_id):
    access_key_id = os.getenv("OSS_ACCESS_KEY_ID")
    access_key_secret = os.getenv("OSS_ACCESS_KEY_SECRET")
    oss_endpoint = os.getenv("OSS_ENDPOINT")

    if not access_key_id or not access_key_secret or not oss_endpoint:
        raise ValueError("ERROR: OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, and OSS_ENDPOINT must be set as environment variables.")

    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, oss_endpoint, bucket_name)

    local_path = os.path.join(local_dir, object_key)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    try:
        bucket.get_object_to_file(object_key, local_path)
    except Exception as e:
        logging.warning(f"Worker {worker_id}: Failed to download {object_key} from OSS - {e}")

def download_oss_bucket(bucket_name, local_dir):
    access_key_id = os.getenv("OSS_ACCESS_KEY_ID")
    access_key_secret = os.getenv("OSS_ACCESS_KEY_SECRET")
    oss_endpoint = os.getenv("OSS_ENDPOINT")

    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, oss_endpoint, bucket_name)

    objects = bucket.list_objects()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for obj in objects.object_list:
            worker_id = len(futures)  # Assigning worker ID
            futures.append(executor.submit(download_oss_file, bucket_name, obj.key, local_dir, worker_id))
        concurrent.futures.wait(futures)

# --- Azure Blob Storage Functions ---

def download_azure_file(container_name, blob_name, local_dir, worker_id):
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)

    local_path = os.path.join(local_dir, blob_name)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    try:
        blob_client = container_client.get_blob_client(blob_name)
        with open(local_path, "wb") as file:
            file.write(blob_client.download_blob().readall())
    except Exception as e:
        logging.warning(f"Worker {worker_id}: Failed to download {blob_name} from Azure - {e}")

def download_azure_bucket(container_name, local_dir):
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)

    blobs = container_client.list_blobs()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for blob in blobs:
            worker_id = len(futures)  # Assigning worker ID
            futures.append(executor.submit(download_azure_file, container_name, blob.name, local_dir, worker_id))
        concurrent.futures.wait(futures)

# --- Upload Functions ---

def upload_s3_file(bucket_name, local_path, local_dir, worker_id):
    s3 = boto3.client("s3")
    object_key = os.path.relpath(local_path, local_dir)
    try:
        s3.upload_file(local_path, bucket_name, object_key)
    except Exception as e:
        logging.warning(f"Worker {worker_id}: Failed to upload {local_path} to S3 - {e}")

def upload_to_s3_bucket(bucket_name, local_dir):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for root, _, files in os.walk(local_dir):
            for file in files:
                local_path = os.path.join(root, file)
                worker_id = len(futures)  # Assigning worker ID
                futures.append(executor.submit(upload_s3_file, bucket_name, local_path, local_dir, worker_id))
        concurrent.futures.wait(futures)

# --- Google Cloud Storage Functions ---

def upload_gcs_file(bucket_name, local_path, local_dir, worker_id):
    client = gcs_storage.Client()
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(os.path.relpath(local_path, local_dir))
    try:
        blob.upload_from_filename(local_path)
    except Exception as e:
        logging.warning(f"Worker {worker_id}: Failed to upload {local_path} to GCS - {e}")

def upload_to_gcs_bucket(bucket_name, local_dir):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for root, _, files in os.walk(local_dir):
            for file in files:
                local_path = os.path.join(root, file)
                worker_id = len(futures)  # Assigning worker ID
                futures.append(executor.submit(upload_gcs_file, bucket_name, local_path, local_dir, worker_id))
        concurrent.futures.wait(futures)

# --- Alibaba Cloud OSS Functions ---

def upload_oss_file(bucket_name, local_path, local_dir, worker_id):
    access_key_id = os.getenv("OSS_ACCESS_KEY_ID")
    access_key_secret = os.getenv("OSS_ACCESS_KEY_SECRET")
    oss_endpoint = os.getenv("OSS_ENDPOINT")

    if not access_key_id or not access_key_secret or not oss_endpoint:
        raise ValueError("ERROR: OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, and OSS_ENDPOINT must be set as environment variables.")

    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, oss_endpoint, bucket_name)
    object_key = os.path.relpath(local_path, local_dir)

    try:
        bucket.put_object_from_file(object_key, local_path)
    except Exception as e:
        logging.warning(f"Worker {worker_id}: Failed to upload {local_path} to OSS - {e}")

def upload_to_oss_bucket(bucket_name, local_dir):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for root, _, files in os.walk(local_dir):
            for file in files:
                local_path = os.path.join(root, file)
                worker_id = len(futures)  # Assigning worker ID
                futures.append(executor.submit(upload_oss_file, bucket_name, local_path, local_dir, worker_id))
        concurrent.futures.wait(futures)

# --- Azure Blob Storage Functions ---

def upload_azure_file(container_name, local_path, local_dir, worker_id):
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)

    blob_name = os.path.relpath(local_path, local_dir).replace("\\", "/") 
    blob_client = container_client.get_blob_client(blob_name)

    try:
        with open(local_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
    except Exception as e:
        logging.warning(f"Worker {worker_id}: Failed to upload {local_path} to Azure - {e}")

def upload_to_azure_bucket(container_name, local_dir):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for root, _, files in os.walk(local_dir):
            for file in files:
                local_path = os.path.join(root, file)
                worker_id = len(futures)  # Assigning worker ID
                futures.append(executor.submit(upload_azure_file, container_name, local_path, local_dir, worker_id))
        concurrent.futures.wait(futures)
