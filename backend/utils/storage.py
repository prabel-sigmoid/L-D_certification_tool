import os
from azure.storage.blob import BlobServiceClient
from io import BytesIO

# Use connection string directly (works with SAS tokens too)
conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
container_name = os.getenv("AZURE_STORAGE_CONTAINER", "uploads")

if not conn_str:
    raise RuntimeError("Missing AZURE_STORAGE_CONNECTION_STRING in .env")

# Initialize blob service
blob_service_client = BlobServiceClient.from_connection_string(conn_str)
container_client = blob_service_client.get_container_client(container_name)

try:
    container_client.create_container()
except Exception:
    pass  # ignore if already exists


def upload_file_to_blob(file, blob_name: str):
    """Upload file-like object to Azure Blob Storage"""
    blob_client = container_client.get_blob_client(blob_name)
    file.seek(0)
    blob_client.upload_blob(file, overwrite=True)
    return blob_client.url


def download_file_from_blob(blob_name: str):
    """Download blob as BytesIO"""
    blob_client = container_client.get_blob_client(blob_name)
    stream = blob_client.download_blob()
    return BytesIO(stream.readall())


def delete_file_from_blob(blob_name: str):
    """Delete a blob from storage"""
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.delete_blob()
