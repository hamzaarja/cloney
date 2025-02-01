import sys
import argparse
from cloney.storage import download_from_source, upload_to_destination
from cloney.utils import create_temp_directory, cleanup_temp_directory
from cloney.check_buckets import check_source_bucket, check_destination_bucket

def main():
    parser = argparse.ArgumentParser(description="Cloney - Cloud Storage Migration Tool")
    parser.add_argument("source_service", help="Source storage service (s3, gcs, oss, azure)")
    parser.add_argument("source_bucket", help="Source bucket name")
    parser.add_argument("destination_service", help="Destination storage service (s3, gcs, oss, azure)")
    parser.add_argument("destination_bucket", help="Destination bucket name")
    
    parser.add_argument('--create-destination-bucket', action='store_true', help="Create the destination bucket if it doesn't exist")


    args = parser.parse_args()

    temp_dir = create_temp_directory()

    try:
        if not check_source_bucket(args.source_service, args.source_bucket):
            print(f"Source bucket {args.source_bucket} does not exist. Exiting.")
            return

        if not check_destination_bucket(args.destination_service, args.destination_bucket, create_if_missing=args.create_destination_bucket):
            print(f"Destination bucket {args.destination_bucket} does not exist or could not be created. Exiting.")
            return           
        print(f"Downloading files from {args.source_service}://{args.source_bucket} to local directory...")
        download_from_source(args.source_service, args.source_bucket, temp_dir)

        print(f"Uploading files from local directory to {args.destination_service}://{args.destination_bucket}...")
        upload_to_destination(args.destination_service, args.destination_bucket, temp_dir)

        print(f"Migration from {args.source_service}://{args.source_bucket} to {args.destination_service}://{args.destination_bucket} completed successfully!")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    finally:
        print(f"Cleaning up temporary directory: {temp_dir}")
        cleanup_temp_directory(temp_dir)

if __name__ == "__main__":
    main()
