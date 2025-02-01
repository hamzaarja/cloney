import boto3
from google.cloud import storage
from azure.storage.blob import BlobServiceClient
import oss2
import os

def check_source_bucket(source_service, source_bucket):
    if source_service == "s3":
        s3_client = boto3.client('s3')
        try:
            s3_client.head_bucket(Bucket=source_bucket)
            return True
        except Exception as e:
            print(f"S3 Bucket {source_bucket} not found: {e}")
            return False
    elif source_service == "gcs":
        client = storage.Client()
        try:
            bucket = client.get_bucket(source_bucket)
            return True
        except Exception as e:
            print(f"GCS Bucket {source_bucket} not found: {e}")
            return False
    elif source_service == "azure":
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

        if not connection_string:
            raise ValueError("ERROR: AZURE_STORAGE_CONNECTION_STRING must be set as an environment variable.")
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        try:
            container_client = blob_service_client.get_container_client(source_bucket)
            container_client.get_container_properties()
            return True
        except Exception as e:
            print(f"Azure Blob Storage Bucket {source_bucket} not found: {e}")
            return False
    elif source_service == "oss":
        try:
            access_key_id = os.getenv("OSS_ACCESS_KEY_ID")
            access_key_secret = os.getenv("OSS_ACCESS_KEY_SECRET")
            endpoint = os.getenv("OSS_ENDPOINT")
            if not access_key_id or not access_key_secret or not endpoint:
                raise ValueError("Missing environment variables: OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, or OSS_ENDPOINT")
            auth = oss2.Auth(access_key_id, access_key_secret)
            bucket = oss2.Bucket(auth, endpoint, source_bucket)
            bucket.get_bucket_info()
            return True
        except oss2.exceptions.NoSuchBucket as e:
            print(f"OSS Bucket '{source_bucket}' does not exist: {e}")
            return False
        except oss2.exceptions.AccessDenied:
            print(f"Access denied to OSS Bucket '{source_bucket}'. Check your permissions.")
            return False
        except Exception as e:
            print(f"An error occurred while checking the OSS bucket: {e}")
            return False
    else:
        print(f"Unsupported source service: {source_service}, did you mean s3, gcs, azure or oss?")
        return False


def check_destination_bucket(destination_service, destination_bucket, create_if_missing=False):
    if destination_service == "s3":
        s3_client = boto3.client('s3')
        try:
            s3_client.head_bucket(Bucket=destination_bucket)
            return True
        except Exception:
            if create_if_missing:
                s3_client.create_bucket(Bucket=destination_bucket)
                print(f"Created S3 Bucket {destination_bucket}")
                return True
            else:
                print(f"S3 Bucket {destination_bucket} not found, pass --create-destination-bucket to create distination bucket.")
                return False
    elif destination_service == "gcs":
        client = storage.Client()
        try:
            bucket = client.get_bucket(destination_bucket)
            return True
        except Exception:
            if create_if_missing:
                client.create_bucket(destination_bucket)
                print(f"Created GCS Bucket {destination_bucket}")
                return True
            else:
                print(f"GCS Bucket {destination_bucket} not found, pass --create-destination-bucket to create distination bucket.")
                return False
    elif destination_service == "azure":
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

        if not connection_string:
            raise ValueError("ERROR: AZURE_STORAGE_CONNECTION_STRING must be set as an environment variable.")
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(destination_bucket)
        try:
            container_client.get_container_properties()
            return True
        except Exception:
            if create_if_missing:
                blob_service_client.create_container(destination_bucket)
                print(f"Created Azure Blob Storage Bucket {destination_bucket}")
                return True
            else:
                print(f"Azure Blob Storage Bucket {destination_bucket} not found, pass --create-destination-bucket to create distination bucket.")
                return False
    elif destination_service == "oss":
        try:
            access_key_id = os.getenv("OSS_ACCESS_KEY_ID")
            access_key_secret = os.getenv("OSS_ACCESS_KEY_SECRET")
            endpoint = os.getenv("OSS_ENDPOINT")
            if not access_key_id or not access_key_secret or not endpoint:
                raise ValueError("Missing environment variables: OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, or OSS_ENDPOINT")
            auth = oss2.Auth(access_key_id, access_key_secret)
            bucket = oss2.Bucket(auth, endpoint, destination_bucket)
            bucket.get_bucket_info()
            return True
        except oss2.exceptions.NoSuchBucket:
            if create_if_missing:
                bucket.create_bucket(oss2.BUCKET_ACL_PRIVATE)
                print(f"Created OSS Bucket {destination_bucket}")
                return True
            print(f"OSS Bucket '{destination_bucket}' not found, pass --create-destination-bucket to create distination bucket.")
            return False
        except oss2.exceptions.AccessDenied:
            print(f"Access denied to OSS Bucket '{destination_bucket}'. Check your permissions.")
            return False
        except Exception as e:
            print(f"An error occurred while checking the OSS bucket: {e}")
            return False
    else:
        print(f"Unsupported source service: {destination_service}")
        return False
