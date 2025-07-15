import os
import boto3
from google.cloud import storage as gcs_storage
import oss2
from azure.storage.blob import BlobServiceClient
import concurrent.futures
from cloney.logger import logging
from cloney.utils import time_logger
import posixpath
import logging as python_logging
import time


python_logging.getLogger('s3transfer').setLevel(python_logging.WARNING)
python_logging.getLogger('botocore.utils').setLevel(python_logging.WARNING)
python_logging.getLogger('botocore.checksums').setLevel(python_logging.WARNING)

_spaces_client = None

def get_spaces_client():
    global _spaces_client
    
    if _spaces_client is not None:
        return _spaces_client

    access_key = os.getenv("SPACES_ACCESS_KEY")
    secret_key = os.getenv("SPACES_SECRET_KEY")
    region = os.getenv("SPACES_REGION", "nyc3")  # Default to NYC3 region

    if not access_key or not secret_key:
        raise ValueError("ERROR: SPACES_ACCESS_KEY and SPACES_SECRET_KEY must be set as environment variables.")

    if not os.getenv("SPACES_REGION"):
        logging.warning("SPACES_REGION environment variable is not set, defaulting to 'nyc3'")

    session = boto3.session.Session()
    _spaces_client = session.client('s3',
        region_name=region,
        endpoint_url=f"https://{region}.digitaloceanspaces.com",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )
    return _spaces_client

@time_logger
def download_from_source(source_service, source_bucket, local_dir):
    if source_service == "s3":
        download_s3_bucket(source_bucket, local_dir)
    elif source_service == "spaces":
        download_spaces_bucket(source_bucket, local_dir)
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
    elif destination_service == "spaces":
        upload_to_spaces_bucket(destination_bucket, local_dir)
    elif destination_service == "gcs":
        upload_to_gcs_bucket(destination_bucket, local_dir)
    elif destination_service == "oss":
        upload_to_oss_bucket(destination_bucket, local_dir)
    elif destination_service == "azure":
        upload_to_azure_bucket(destination_bucket, local_dir)
    else:
        raise ValueError(f"Unsupported destination service: {destination_service}")

# --- Download Functions ---
def download_s3_file(s3_client, bucket_name, object_key, local_dir, worker_id, max_retries=3):
    local_path = os.path.join(local_dir, object_key)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    for attempt in range(max_retries):
        try:
            s3_client.download_file(bucket_name, object_key, local_path)
            logging.info(f"Worker {worker_id}: downloaded {object_key} from S3.")
            return
        except Exception as e:
            if attempt == max_retries - 1:
                logging.warning(f"Worker {worker_id}: Failed to download {object_key} from S3 after {max_retries} attempts - {e}")
            else:
                logging.info(f"Worker {worker_id}: Retry {attempt + 1} for {object_key} - {e}")
                time.sleep(2 ** attempt)

def download_s3_bucket(bucket_name, local_dir, max_workers=50):
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        worker_id = 0
        for page in paginator.paginate(Bucket=bucket_name):
            futures = []
            for obj in page.get("Contents", []):
                object_key = obj["Key"]
                s3_client = boto3.client("s3")
                futures.append(executor.submit(download_s3_file, s3_client, bucket_name, object_key, local_dir, worker_id))
                worker_id += 1
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

    local_path = os.path.join(local_dir, *object_key.split("/"))
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    try:
        bucket.get_object_to_file(object_key, local_path)
        logging.info(f"Worker {worker_id}: Downloaded {object_key} -> {local_path}")
    except Exception as e:
        logging.warning(f"Worker {worker_id}: Failed to download {object_key} from OSS - {e}")

def download_oss_bucket(bucket_name, local_dir):
    access_key_id = os.getenv("OSS_ACCESS_KEY_ID")
    access_key_secret = os.getenv("OSS_ACCESS_KEY_SECRET")
    oss_endpoint = os.getenv("OSS_ENDPOINT")

    if not access_key_id or not access_key_secret or not oss_endpoint:
        raise ValueError("ERROR: OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, and OSS_ENDPOINT must be set as environment variables.")

    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, oss_endpoint, bucket_name)

    marker = "" 
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        while True:
            result = bucket.list_objects(marker=marker, max_keys=1000)

            for obj in result.object_list:
                if obj.key.endswith("/"):
                    continue

                worker_id = len(futures)
                futures.append(executor.submit(download_oss_file, bucket_name, obj.key, local_dir, worker_id))

            if not result.is_truncated:
                break
            marker = result.next_marker 

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
        logging.info(f"Worker {worker_id}: downloaded {blob_name}.")
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

# --- Digital Ocean Spaces Functions ---

def download_spaces_file(bucket_name, object_key, local_dir, worker_id):
    spaces = get_spaces_client()
    local_path = os.path.join(local_dir, object_key)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    try:
        spaces.download_file(bucket_name, object_key, local_path)
        logging.info(f"Worker {worker_id}: downloaded {object_key} from Spaces.")
    except Exception as e:
        logging.warning(f"Worker {worker_id}: Failed to download {object_key} from Spaces - {e}")

def download_spaces_bucket(bucket_name, local_dir):
    spaces = get_spaces_client()
    response = spaces.list_objects_v2(Bucket=bucket_name)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for obj in response.get("Contents", []):
            object_key = obj["Key"]
            worker_id = len(futures)
            futures.append(executor.submit(download_spaces_file, bucket_name, object_key, local_dir, worker_id))
        concurrent.futures.wait(futures)

# --- Upload Functions ---

def upload_s3_file(s3_client, bucket_name, local_path, local_dir, worker_id, max_retries=3):
    object_key = posixpath.join(*os.path.relpath(local_path, local_dir).split(os.sep))
    
    for attempt in range(max_retries):
        try:
            s3_client.upload_file(local_path, bucket_name, object_key)
            logging.info(f"Worker {worker_id}: Uploaded {local_path} to S3 as {object_key}.")
            return
        except Exception as e:
            if attempt == max_retries - 1:
                logging.warning(f"Worker {worker_id}: Failed to upload {local_path} to S3 after {max_retries} attempts - {e}")
            else:
                logging.info(f"Worker {worker_id}: Retry {attempt + 1} for {local_path} - {e}")
                time.sleep(2 ** attempt)

def upload_to_s3_bucket(bucket_name, local_dir, max_workers=50):
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        worker_id = 0
        for root, _, files in os.walk(local_dir):
            for file in files:
                local_path = os.path.join(root, file)
                s3_client = boto3.client("s3")
                futures.append(executor.submit(upload_s3_file, s3_client, bucket_name, local_path, local_dir, worker_id))
                worker_id += 1
        concurrent.futures.wait(futures)

# --- Google Cloud Storage Functions ---

def upload_gcs_file(bucket_name, local_path, local_dir, worker_id):
    client = gcs_storage.Client()
    bucket = client.get_bucket(bucket_name)
    
    # Normalize object key for GCS (always use forward slashes)
    object_key = posixpath.join(*os.path.relpath(local_path, local_dir).split(os.sep))

    blob = bucket.blob(object_key)
    
    try:
        blob.upload_from_filename(local_path)
        logging.info(f"Worker {worker_id}: Uploaded {local_path} to GCS as {object_key}.")
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

    # Normalize object key for OSS (always use forward slashes)
    object_key = posixpath.join(*os.path.relpath(local_path, local_dir).split(os.sep))

    try:
        bucket.put_object_from_file(object_key, local_path)
        logging.info(f"Worker {worker_id}: Uploaded {local_path} to OSS as {object_key}.")
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
        logging.info(f"Worker {worker_id}: uploaded {local_path} to Azure.")
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


# --- Digital Ocean Spaces Functions ---

def upload_spaces_file(bucket_name, local_path, local_dir, worker_id):
    spaces = get_spaces_client()
    object_key = posixpath.join(*os.path.relpath(local_path, local_dir).split(os.sep))
    try:
        spaces.upload_file(local_path, bucket_name, object_key)
        logging.info(f"Worker {worker_id}: Uploaded {local_path} to Spaces as {object_key}.")
    except Exception as e:
        logging.warning(f"Worker {worker_id}: Failed to upload {local_path} to Spaces - {e}")

def upload_to_spaces_bucket(bucket_name, local_dir):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for root, _, files in os.walk(local_dir):
            for file in files:
                local_path = os.path.join(root, file)
                worker_id = len(futures)
                futures.append(executor.submit(upload_spaces_file, bucket_name, local_path, local_dir, worker_id))
        concurrent.futures.wait(futures)
