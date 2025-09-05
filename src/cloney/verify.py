import os
import boto3
from google.cloud import storage
from azure.storage.blob import BlobServiceClient
import oss2
from cloney.logger import logging
from cloney.utils import time_logger
from cloney.storage import get_spaces_client

def get_r2_client():
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    account_id = os.getenv("R2_ACCOUNT_ID")

    if not access_key or not secret_key or not account_id:
        raise ValueError("ERROR: R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, and R2_ACCOUNT_ID must be set as environment variables.")

    return boto3.client('s3',
        endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='auto'
    )

def get_s3_objects(bucket_name):
    s3 = boto3.client("s3")
    objects = []

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name):
        if "Contents" in page:
            for obj in page["Contents"]:
                objects.append({
                    "Key": obj["Key"],
                    "Size": obj["Size"]
                })

    return objects

def get_spaces_objects(bucket_name):
    try:
        spaces = get_spaces_client()
        objects = []

        paginator = spaces.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket_name):
            if "Contents" in page:
                for obj in page["Contents"]:
                    objects.append({
                        "Key": obj["Key"],
                        "Size": obj["Size"]
                    })

        return objects
    except Exception as e:
        logging.warning(f"Spaces Error: {e}")
        return []

def get_gcs_objects(bucket_name):
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        objects = []
        for blob in bucket.list_blobs():
            objects.append({
                "Key": blob.name,
                "Size": blob.size
            })
        
        return objects
    except Exception as e:
        logging.warning(f"GCS Error: {e}")
        return []

def get_azure_objects(bucket_name):
    try:
        connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')

        if not connection_string:
            logging.warning("Azure Error: Missing AZURE_STORAGE_CONNECTION_STRING in environment variables.")
            return []

        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(bucket_name)

        objects = []
        for blob in container_client.list_blobs():
            objects.append({
                "Key": blob.name,
                "Size": blob.size
            })
        
        return objects
    except Exception as e:
        logging.warning(f"Azure Error: {e}")
        return []

def get_oss_objects(bucket_name):
    try:
        aliyun_access_key = os.getenv('OSS_ACCESS_KEY_ID')
        aliyun_secret_key = os.getenv('OSS_ACCESS_KEY_SECRET')
        oss_endpoint = os.getenv('OSS_ENDPOINT')

        if not aliyun_access_key or not aliyun_secret_key or not oss_endpoint:
            logging.warning("OSS Error: Missing Alibaba Cloud credentials or endpoint in environment variables.")
            return []

        auth = oss2.Auth(aliyun_access_key, aliyun_secret_key)
        bucket = oss2.Bucket(auth, oss_endpoint, bucket_name)

        objects = []
        for obj in oss2.ObjectIterator(bucket):
            objects.append({
                "Key": obj.key,
                "Size": obj.size
            })

        return objects
    except Exception as e:
        logging.warning(f"OSS Error: {e}")
        return []

def get_r2_objects(bucket_name):
    try:
        r2 = get_r2_client()
        objects = []

        paginator = r2.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket_name):
            if "Contents" in page:
                for obj in page["Contents"]:
                    objects.append({
                        "Key": obj["Key"],
                        "Size": obj["Size"]
                    })

        return objects
    except Exception as e:
        logging.warning(f"R2 Error: {e}")
        return []

@time_logger
def compare_object_lists(source_service, source_bucket, destination_service, destination_bucket):
    source_objects = []
    destination_objects = []
    if source_service == "s3":
        source_objects = get_s3_objects(source_bucket)
    elif source_service == "spaces":
        source_objects = get_spaces_objects(source_bucket)
    elif source_service == "gcs":
        source_objects = get_gcs_objects(source_bucket)
    elif source_service == "oss":
        source_objects = get_oss_objects(source_bucket)
    elif source_service == "azure":
        source_objects = get_azure_objects(source_bucket)
    elif source_service == "r2":
        source_objects = get_r2_objects(source_bucket)
    else:
        raise ValueError(f"Unsupported source service: {source_service}")
    
    if destination_service == "s3":
        destination_objects = get_s3_objects(destination_bucket)
    elif destination_service == "spaces":
        destination_objects = get_spaces_objects(destination_bucket)
    elif destination_service == "gcs":
        destination_objects = get_gcs_objects(destination_bucket)
    elif destination_service == "oss":
        destination_objects = get_oss_objects(destination_bucket)
    elif destination_service == "azure":
        destination_objects = get_azure_objects(destination_bucket)
    elif destination_service == "r2":
        destination_objects = get_r2_objects(destination_bucket)
    else:
        raise ValueError(f"Unsupported destination service: {destination_service}")
    if not source_objects:
        logging.warning("Error: Source bucket is empty or could not be retrieved.")
        return

    if not destination_objects:
        logging.warning("Error: Destination bucket is empty or could not be retrieved.")
        return
    source_dict = {obj["Key"]: obj["Size"] for obj in source_objects}
    destination_dict = {obj["Key"]: obj["Size"] for obj in destination_objects}

    missing_in_destination = {k: v for k, v in source_dict.items() if k not in destination_dict}
    missing_in_source = {k: v for k, v in destination_dict.items() if k not in source_dict}

    size_mismatches = {
        k: (source_dict[k], destination_dict[k])
        for k in source_dict if k in destination_dict and source_dict[k] != destination_dict[k]
    }

    if not missing_in_destination and not missing_in_source and not size_mismatches:
        logging.info("Both buckets are identical.")
    else:
        if missing_in_destination:
            logging.warning("Objects missing in destination:")
            for key, size in missing_in_destination.items():
                logging.warning(f" - {key} ({size} bytes)")

        if missing_in_source:
            logging.warning("Objects missing in source:")
            for key, size in missing_in_source.items():
                logging.warning(f" - {key} ({size} bytes)")

        if size_mismatches:
            logging.warning("Objects with size mismatches:")
            for key, (source_size, dest_size) in size_mismatches.items():
                logging.warning(f" - {key}: Source {source_size} bytes, Destination {dest_size} bytes")