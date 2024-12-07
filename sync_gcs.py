from google.cloud import storage
import os

BUCKET_NAME = "my-legal-data"
LOCAL_FOLDER = "./data"

def download_from_gcs(folder_name):
    client = storage.Client()
    bucket = client.get_bucket(BUCKET_NAME)
    blobs = bucket.list_blobs(prefix=folder_name)

    os.makedirs(LOCAL_FOLDER, exist_ok=True)

    for blob in blobs:
        file_name = os.path.basename(blob.name)
        local_path = os.path.join(LOCAL_FOLDER, file_name)
        blob.download_to_filename(local_path)
        print(f"Downloaded: {file_name} to {local_path}")

if __name__ == "__main__":
    download_from_gcs("pdfs/")
