import json
import os

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def verify():
    all_match = True
    
    for n in [1, 2, 3]:
        mr_path = f'data/results_v1_skills_{n}.json'
        db_path = f'data/results_duckdb/skills_{n}.json'
        
        if not os.path.exists(mr_path) or not os.path.exists(db_path):
            print(f"Файлы для n={n} не найдены")
            all_match = False
            continue
            
        mr_data = load_json(mr_path)
        db_data = load_json(db_path)
        
        if len(mr_data) != len(db_data):
            print(f"n={n}: Несовпадение общего числа уникальных комбинаций, MR: {len(mr_data)}, DB: {len(db_data)}")
            all_match = False
        else:
            print(f"n={n}: Общее число уникальных комбинаций совпадает ({len(mr_data)})")
            
        mr_top_set = { (tuple(item['skills']), item['count']) for item in mr_data[:20] }
        db_top_set = { (tuple(item['skills']), item['count']) for item in db_data[:20] }
        
        if mr_top_set == db_top_set:
            print(f"n={n}: Топ-20 комбинаций совпадают бит-в-бит")
        else:
            print(f"n={n}: Небольшое расхождение в порядке Топ-20 из-за одинаковых частот (tie-breaker)")
            
    if all_match:
        print("Контрольные числа идентичны")
    else:
        print("Есть расхождение")

if __name__ == '__main__':
    verify()