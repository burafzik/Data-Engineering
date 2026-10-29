import duckdb
import json
import os

INPUT_CSV = 'data/vacancies_mobile_2024.csv'
OUTPUT_DIR = 'data/results_duckdb'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_duckdb():
    conn = duckdb.connect()
    
    conn.execute("""
        CREATE OR REPLACE TABLE unique_skills AS
        SELECT 
            vacancy_id, 
            lower(trim(unnested_skill)) as skill
        FROM read_csv_auto(?, all_varchar=true),
        UNNEST(string_split(COALESCE(key_skills, ''), ';')) AS t(unnested_skill)
        WHERE lower(trim(unnested_skill)) != '' 
          AND lower(trim(unnested_skill)) != 'nan'
        GROUP BY vacancy_id, lower(trim(unnested_skill))
    """, [INPUT_CSV])
    
    queries = {
        1: """
            SELECT [skill] as combo, count(*) as cnt
            FROM unique_skills
            GROUP BY skill 
            ORDER BY cnt DESC, combo ASC
        """,
        2: """
            SELECT list_sort([t1.skill, t2.skill]) as combo, count(*) as cnt
            FROM unique_skills t1
            JOIN unique_skills t2 
              ON t1.vacancy_id = t2.vacancy_id AND t1.skill < t2.skill
            GROUP BY 1 
            ORDER BY cnt DESC, combo ASC
        """,
        3: """
            SELECT list_sort([t1.skill, t2.skill, t3.skill]) as combo, count(*) as cnt
            FROM unique_skills t1
            JOIN unique_skills t2 
              ON t1.vacancy_id = t2.vacancy_id AND t1.skill < t2.skill
            JOIN unique_skills t3 
              ON t1.vacancy_id = t3.vacancy_id AND t2.skill < t3.skill
            GROUP BY 1 
            ORDER BY cnt DESC, combo ASC
        """
    }
    
    for n, query in queries.items():
        result = conn.execute(query).fetchall()
        
        output_data = [{"skills": list(row[0]), "count": row[1]} for row in result]
        
        filename = f'skills_{n}.json'
        local_path = os.path.join(OUTPUT_DIR, filename)
        
        with open(local_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
            
        print(f"Сохранено: {local_path} (уникальных комбинаций: {len(output_data)})")
        
    conn.close()
    print("DuckDB завершён")

if __name__ == '__main__':
    run_duckdb()