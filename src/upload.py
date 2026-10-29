import pandas as pd
import os
from common import get_s3_client, ensure_bucket_exists, BUCKET_NAME

INPUT_CSV = '../vacancies_2024.csv'
OUTPUT_CSV = 'data/vacancies_mobile_2024.csv'
S3_KEY = 'raw/vacancies_mobile_2024.csv'

def filter_mobile_vacancies():
    
    chunk_size = 500_000
    total_filtered = 0
    first_chunk = True
    
    for chunk in pd.read_csv(INPUT_CSV, chunksize=chunk_size, low_memory=False, on_bad_lines='skip'):
        role_mask = chunk['role'].fillna('').str.contains('программист|разработчик|developer|engineer', case=False, na=False)
        
        tech_mask = (
            chunk['name'].fillna('').str.contains('android|ios|swift|kotlin|flutter|react native', case=False, na=False) |
            chunk['key_skills'].fillna('').str.contains('android|ios|swift|kotlin|flutter|react native', case=False, na=False)
        )
        
        mask = role_mask & tech_mask
        filtered_chunk = chunk[mask]
        
        if not filtered_chunk.empty:
            total_filtered += len(filtered_chunk)
            filtered_chunk.to_csv(
                OUTPUT_CSV, 
                mode='a' if not first_chunk else 'w', 
                header=first_chunk, 
                index=False
            )
            first_chunk = False
            print(f"Найдено {len(filtered_chunk)} IT-вакансий в чанке. Всего: {total_filtered}")

    print(f"Всего вакансий мобильных разработчиков: {total_filtered}")
    print(f"Локальный файл сохранен: {OUTPUT_CSV}")
    return total_filtered

def upload_to_rustfs():
    client = get_s3_client()
    ensure_bucket_exists()
    
    with open(OUTPUT_CSV, 'rb') as f:
        client.put_object(Bucket=BUCKET_NAME, Key=S3_KEY, Body=f)
    print(f"Успешно загружено в s3://{BUCKET_NAME}/{S3_KEY}")

if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    count = filter_mobile_vacancies()
    if count > 0:
        upload_to_rustfs()
    else:
        print("Вакансии не найдены")