import duckdb
import json
import os

INPUT_CSV = 'data/vacancies_mobile_2024.csv'
OUTPUT_DIR = 'data/results_salary'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def analyze_salary():
    conn = duckdb.connect()
    
    conn.execute("""
        CREATE OR REPLACE TABLE vacancy_salary AS
        SELECT 
            vacancy_id,
            CAST(COALESCE(NULLIF(salary_from, ''), NULLIF(salary_to, '')) AS DOUBLE) as salary
        FROM read_csv_auto(?, all_varchar=true)
        WHERE COALESCE(NULLIF(salary_from, ''), NULLIF(salary_to, '')) IS NOT NULL
    """, [INPUT_CSV])
    
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
    
    global_median = conn.execute("SELECT median(salary) FROM vacancy_salary").fetchone()[0]
    print(f"Глобальная медианная зарплата: {global_median:,.0f} руб.")
    
    results = {"global_median": global_median, "singles": [], "pairs": [], "triples": []}
    
    singles = conn.execute("""
        SELECT 
            skill, 
            count(*) as freq, 
            median(salary) as med_salary,
            median(salary) - ? as delta
        FROM unique_skills us
        JOIN vacancy_salary vs ON us.vacancy_id = vs.vacancy_id
        GROUP BY skill
        HAVING count(*) >= 500
        ORDER BY freq DESC
        LIMIT 20
    """, [global_median]).fetchall()
    
    results["singles"] = [{"skill": row[0], "freq": row[1], "median": row[2], "delta": row[3]} for row in singles]
    
    pairs = conn.execute("""
        WITH pair_data AS (
            SELECT 
                t1.skill as skill1, 
                t2.skill as skill2,
                vs.salary
            FROM vacancy_salary vs
            JOIN unique_skills t1 ON vs.vacancy_id = t1.vacancy_id
            JOIN unique_skills t2 ON vs.vacancy_id = t2.vacancy_id AND t1.skill < t2.skill
        ),
        pair_stats AS (
            SELECT 
                skill1, skill2,
                count(*) as freq,
                median(salary) as med_salary_pair
            FROM pair_data
            GROUP BY skill1, skill2
            HAVING count(*) >= 100
        ),
        single_stats AS (
            SELECT skill, median(salary) as med_salary_single
            FROM unique_skills us
            JOIN vacancy_salary vs ON us.vacancy_id = vs.vacancy_id
            GROUP BY skill
        )
        SELECT 
            ps.skill1, ps.skill2, ps.freq, ps.med_salary_pair,
            COALESCE(ss.med_salary_single, ?) as baseline_median,
            ps.med_salary_pair - COALESCE(ss.med_salary_single, ?) as delta
        FROM pair_stats ps
        LEFT JOIN single_stats ss ON ps.skill1 = ss.skill
        ORDER BY ps.freq DESC
        LIMIT 20
    """, [global_median, global_median]).fetchall()
    
    results["pairs"] = [{
        "skills": [row[0], row[1]], "freq": row[2], "median": row[3], 
        "baseline_median": row[4], "delta": row[5]
    } for row in pairs]
    
    triples = conn.execute("""
        WITH triple_data AS (
            SELECT 
                t1.skill as skill1, t2.skill as skill2, t3.skill as skill3, vs.salary
            FROM vacancy_salary vs
            JOIN unique_skills t1 ON vs.vacancy_id = t1.vacancy_id
            JOIN unique_skills t2 ON vs.vacancy_id = t2.vacancy_id AND t1.skill < t2.skill
            JOIN unique_skills t3 ON vs.vacancy_id = t3.vacancy_id AND t2.skill < t3.skill
        ),
        triple_stats AS (
            SELECT 
                skill1, skill2, skill3,
                count(*) as freq,
                median(salary) as med_salary_triple
            FROM triple_data
            GROUP BY skill1, skill2, skill3
            HAVING count(*) >= 30
        ),
        pair_stats AS (
            SELECT 
                t1.skill as skill1, t2.skill as skill2,
                median(vs.salary) as med_salary_pair
            FROM vacancy_salary vs
            JOIN unique_skills t1 ON vs.vacancy_id = t1.vacancy_id
            JOIN unique_skills t2 ON vs.vacancy_id = t2.vacancy_id AND t1.skill < t2.skill
            GROUP BY t1.skill, t2.skill
        )
        SELECT 
            ts.skill1, ts.skill2, ts.skill3, ts.freq, ts.med_salary_triple,
            COALESCE(ps.med_salary_pair, ?) as baseline_median,
            ts.med_salary_triple - COALESCE(ps.med_salary_pair, ?) as delta
        FROM triple_stats ts
        LEFT JOIN pair_stats ps ON ts.skill1 = ps.skill1 AND ts.skill2 = ps.skill2
        ORDER BY ts.freq DESC
        LIMIT 20
    """, [global_median, global_median]).fetchall()
    
    results["triples"] = [{
        "skills": [row[0], row[1], row[2]], "freq": row[3], "median": row[4], 
        "baseline_median": row[5], "delta": row[6]
    } for row in triples]
    
    output_path = os.path.join(OUTPUT_DIR, 'salary_analysis.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print(f"Результаты сохранены в {output_path}")
    conn.close()

if __name__ == '__main__':
    analyze_salary()