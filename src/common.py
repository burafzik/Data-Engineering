import boto3
import os

S3_ENDPOINT = 'http://localhost:9000'
S3_ACCESS_KEY = 'rustfsadmin'
S3_SECRET_KEY = 'rustfsadmin'
BUCKET_NAME = 'hh-lake'

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name='us-east-1'
    )

def ensure_bucket_exists():
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=BUCKET_NAME)
        print(f"[OK] Бакет '{BUCKET_NAME}' уже существует.")
    except Exception:
        print(f"[INFO] Создаем бакет '{BUCKET_NAME}'...")
        client.create_bucket(Bucket=BUCKET_NAME)
        print(f"[OK] Бакет '{BUCKET_NAME}' успешно создан.")