import boto3
import pandas as pd
import itertools
import json
import os
from collections import defaultdict
from common import get_s3_client, BUCKET_NAME

INPUT_S3_KEY = 'raw/vacancies_mobile_2024.csv'
OUTPUT_DIR_S3 = 'results/mapreduce/'
TEMP_DIR = 'data/temp_mapreduce'
os.makedirs(TEMP_DIR, exist_ok=True)

def clean_skill(skill: str) -> str:
    return str(skill).strip().lower()

def run_mapreduce():
    s3_client = get_s3_client()
    
    temp_csv_path = os.path.join(TEMP_DIR, 'temp_vacancies.csv')
    print(f"Загрузка файла из s3://{BUCKET_NAME}/{INPUT_S3_KEY}...")
    s3_client.download_file(BUCKET_NAME, INPUT_S3_KEY, temp_csv_path)
     
    chunk_size = 100_000
    chunk_id = 0
    total_lines = 0
    
    for chunk in pd.read_csv(temp_csv_path, chunksize=chunk_size, low_memory=False, on_bad_lines='skip'):
        chunk_id += 1
        print(f"Обработка чанка {chunk_id} ({len(chunk)} строк)")
        total_lines += len(chunk)
        
        combiner = defaultdict(int)
        
        for _, row in chunk.iterrows():
            skills_str = str(row.get('key_skills', ''))
            if not skills_str or skills_str.lower() == 'nan':
                continue
                
            raw_skills = [s for s in skills_str.split(';')]
            skills = list(set([clean_skill(s) for s in raw_skills if clean_skill(s)]))
            
            for r in [1, 2, 3]:
                for combo in itertools.combinations(skills, r):
                    sorted_combo = tuple(sorted(combo))
                    combiner[sorted_combo] += 1
                    
        temp_file = os.path.join(TEMP_DIR, f'chunk_{chunk_id}.json')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump({json.dumps(k): v for k, v in combiner.items()}, f)
            
    print(f"MAP+COMBINE завершён. Обработано строк: {total_lines}. Чанков: {chunk_id}")
    
    if os.path.exists(temp_csv_path):
        os.remove(temp_csv_path)
        
    final_counts = {1: defaultdict(int), 2: defaultdict(int), 3: defaultdict(int)}
    
    for i in range(1, chunk_id + 1):
        temp_file = os.path.join(TEMP_DIR, f'chunk_{i}.json')
        with open(temp_file, 'r', encoding='utf-8') as f:
            chunk_data = json.load(f)
            for key_str, count in chunk_data.items():
                key_tuple = tuple(json.loads(key_str))
                final_counts[len(key_tuple)][key_tuple] += count

    results_to_upload = []
    
    for r, data in final_counts.items():
        sorted_data = sorted(data.items(), key=lambda x: (-x[1], str(x[0])))
        output_data = [{"skills": list(k), "count": v} for k, v in sorted_data]
        
        filename = f'skills_{r}.json'
        local_path = os.path.join('data', f'results_v1_{filename}')
        os.makedirs('data', exist_ok=True)
        
        with open(local_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
            
        s3_key = f"{OUTPUT_DIR_S3}{filename}"
        results_to_upload.append((local_path, s3_key))
        print(f"Локально сохранено: {local_path} (уникальных комбинаций: {len(output_data)})")

    for local_path, s3_key in results_to_upload:
        with open(local_path, 'rb') as f:
            s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=f)
        print(f"Загружено в s3://{BUCKET_NAME}/{s3_key}")
        
    print("MapReduce завершён")

if __name__ == '__main__':
    run_mapreduce()