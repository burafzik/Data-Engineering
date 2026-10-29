import os
from common import get_s3_client, ensure_bucket_exists, BUCKET_NAME

LOCAL_FILE = 'data/vacancies_mobile_2024.csv'
S3_KEY = 'raw/vacancies_mobile_2024.csv'

def upload_to_rustfs():
    if not os.path.exists(LOCAL_FILE):
        print(f"Файл {LOCAL_FILE} не найден.")
        return

    print(f"Загружаем готовый файл {LOCAL_FILE} в RustFS...")
    client = get_s3_client()
    ensure_bucket_exists()
    
    file_size_mb = os.path.getsize(LOCAL_FILE) / (1024 * 1024)
    print(f"Размер файла: {file_size_mb:.2f} МБ")
    
    with open(LOCAL_FILE, 'rb') as f:
        client.put_object(
            Bucket=BUCKET_NAME,
            Key=S3_KEY,
            Body=f
        )
    print(f"Успешно загружено в s3://{BUCKET_NAME}/{S3_KEY}")

if __name__ == '__main__':
    upload_to_rustfs()