# Cloney - Storage Migration CLI

Cloney is a lightweight command-line tool designed to migrate files between different cloud storage providers seamlessly. It supports AWS S3, Google Cloud Storage (GCS), Alibaba Cloud OSS, DigitalOcean Spaces, and Azure Blob Storage, allowing you to move data efficiently.

## Features

🔄 Migrate files between S3, GCS, OSS, Spaces and Azure Blob

⚡ Fast and efficient transfer with minimal configuration

🔧 Simple CLI usage for easy automation

✅ Supports large file transfers

🔐 Secure authentication using environment variables or config files

## Installation

From Source (Python)

```sh
pip install cloney
```

## Usage

### Same Cloud Transfers

Migrate data within the same cloud provider:

**AWS S3 to AWS S3**

```sh
cloney s3 my-source-bucket s3 my-destination-bucket
```

**Google Cloud Storage to Google Cloud Storage**

```sh
cloney gcs my-source-bucket gcs my-destination-bucket
```

**Azure Blob Storage to Azure Blob Storage**

```sh
cloney azure my-source-container azure my-destination-container
```

**Alibaba Cloud OSS to Alibaba Cloud OSS**

```sh
cloney oss my-source-bucket oss my-destination-bucket
```


### Cross-Cloud Transfers

Migrate data between different cloud providers:

**AWS S3 to Google Cloud Storage**

```sh
cloney s3 my-s3-bucket gcs my-gcs-bucket
```

**Google Cloud Storage to Azure Blob Storage**

```sh
cloney gcs my-gcs-bucket azure my-azure-container
```

**Azure Blob Storage to Alibaba Cloud OSS**

```sh
cloney azure my-azure-container oss my-oss-bucket
```

**AWS S3 to DigitalOcean Spaces**

```sh
cloney s3 my-source-bucket spaces my-destination-bucket
```


If you would like to create the destination bucket automatically, use the `--create-destination-bucket` flag:

```sh
cloney s3 my-source-bucket gcs my-destination-bucket --create-destination-bucket
```

If you want to verify the files between the source and destination buckets, use the --verify flag:

```sh
cloney s3 my-source-bucket gcs my-destination-bucket --verify
```
This will check for any mismatched or missing files between the two buckets.

## Authentication

Cloney supports authentication via environment variables or configuration files:

### Linux/macOS

**AWS S3**

```sh
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
```

**Google Cloud Storage (GCS)**

```sh
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/gcs-key.json
```

**Alibaba Cloud OSS**

```sh
export OSS_ENDPOINT=your-endpoint
export OSS_ACCESS_KEY_ID=your-access-key
export OSS_ACCESS_KEY_SECRET=your-secret-key
```

**Azure Blob Storage**

```sh
export AZURE_STORAGE_CONNECTION_STRING="your-connection-string"
```
**DigitalOcean Spaces**

```sh
export SPACES_ACCESS_KEY=your-access-key
export SPACES_SECRET_KEY=your-secret-key
export SPACES_REGION=your-region
```

### Windows (PowerShell)

**AWS S3**

```sh
$env:AWS_ACCESS_KEY_ID="your-access-key"
$env:AWS_SECRET_ACCESS_KEY="your-secret-key"
```

**Google Cloud Storage (GCS)**

```sh
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\your\gcs-key.json"
```

**Alibaba Cloud OSS**

```sh
$env:OSS_ENDPOINT="your-endpoint"
$env:OSS_ACCESS_KEY_ID="your-access-key"
$env:OSS_ACCESS_KEY_SECRET="your-secret-key"
```

**Azure Blob Storage**

```sh
$env:AZURE_STORAGE_CONNECTION_STRING="your-connection-string"
```

**DigitalOcean Spaces**

```sh
$env:SPACES_ACCESS_KEY="your-access-key"
$env:SPACES_SECRET_KEY="your-secret-key"
$env:SPACES_REGION="your-region"
```

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

Cloney is licensed under the MIT License.

## Contact

For questions or support, open an issue on GitHub.
