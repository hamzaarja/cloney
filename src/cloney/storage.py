import os
import boto3
from google.cloud import storage as gcs_storage
import oss2
from azure.storage.blob import BlobServiceClient

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

def download_s3_bucket(bucket_name, local_dir):
    s3 = boto3.client("s3")
    response = s3.list_objects_v2(Bucket=bucket_name)
    for obj in response.get("Contents", []):
        object_key = obj["Key"]
        local_path = os.path.join(local_dir, object_key)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        s3.download_file(bucket_name, object_key, local_path)

def download_gcs_bucket(bucket_name, local_dir):
    client = gcs_storage.Client()
    bucket = client.get_bucket(bucket_name)
    blobs = bucket.list_blobs()
    for blob in blobs:
        local_path = os.path.join(local_dir, blob.name)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        blob.download_to_filename(local_path)

def download_oss_bucket(bucket_name, local_dir):
    access_key_id = os.getenv("OSS_ACCESS_KEY_ID")
    access_key_secret = os.getenv("OSS_ACCESS_KEY_SECRET")
    oss_endpoint = os.getenv("OSS_ENDPOINT")

    if not access_key_id or not access_key_secret or not oss_endpoint:
        raise ValueError("ERROR: OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, and OSS_ENDPOINT must be set as environment variables.")

    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, oss_endpoint, bucket_name)

    objects = bucket.list_objects()

    if not objects.object_list:
        print(f"No objects found in bucket: {bucket_name}")
        return

    for obj in objects.object_list:
        local_path = os.path.join(local_dir, obj.key)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        bucket.get_object_to_file(obj.key, local_path)

def download_azure_bucket(container_name, local_dir):
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

    if not connection_string:
        raise ValueError("ERROR: AZURE_STORAGE_CONNECTION_STRING must be set as an environment variable.")

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)

    blobs = container_client.list_blobs()
    for blob in blobs:
        local_path = os.path.join(local_dir, blob.name)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        blob_client = container_client.get_blob_client(blob.name)
        with open(local_path, "wb") as file:
            file.write(blob_client.download_blob().readall())
        

def upload_to_s3_bucket(bucket_name, local_dir):
    s3 = boto3.client("s3")
    for root, _, files in os.walk(local_dir):
        for file in files:
            local_path = os.path.join(root, file)
            s3.upload_file(local_path, bucket_name, os.path.relpath(local_path, local_dir))

def upload_to_gcs_bucket(bucket_name, local_dir):
    client = gcs_storage.Client()
    bucket = client.get_bucket(bucket_name)
    for root, _, files in os.walk(local_dir):
        for file in files:
            local_path = os.path.join(root, file)
            blob = bucket.blob(os.path.relpath(local_path, local_dir))
            blob.upload_from_filename(local_path)

def upload_to_oss_bucket(bucket_name, local_dir):
    access_key_id = os.getenv("OSS_ACCESS_KEY_ID")
    access_key_secret = os.getenv("OSS_ACCESS_KEY_SECRET")
    oss_endpoint = os.getenv("OSS_ENDPOINT")

    if not access_key_id or not access_key_secret or not oss_endpoint:
        raise ValueError("OERROR: OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, and OSS_ENDPOINT must be set as environment variables.")

    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, oss_endpoint, bucket_name)
    for root, _, files in os.walk(local_dir):
        for file in files:
            local_path = os.path.join(root, file)
            bucket.put_object_from_file(os.path.relpath(local_path, local_dir), local_path)

def upload_to_azure_bucket(container_name, local_dir):
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

    if not connection_string:
        raise ValueError("ERROR: AZURE_STORAGE_CONNECTION_STRING must be set as an environment variable.")

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)

    try:
        container_client.create_container()
    except Exception:
        pass

    for root, _, files in os.walk(local_dir):
        for file in files:
            local_path = os.path.join(root, file)
            blob_name = os.path.relpath(local_path, local_dir).replace("\\", "/") 

            blob_client = container_client.get_blob_client(blob_name)
            with open(local_path, "rb") as data:
                try:
                    blob_client.upload_blob(data, overwrite=True)
                except Exception as e:
                    print(f"Failed to upload {blob_name}: {e}")
