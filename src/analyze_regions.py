import duckdb
import json
import os

INPUT_CSV = 'data/vacancies_mobile_2024.csv'
OUTPUT_DIR = 'data/results_regions'
os.makedirs(OUTPUT_DIR, exist_ok=True)

TARGET_REGIONS = ['Москва', 'Санкт-Петербург', 'Екатеринбург']

def analyze_regions():
    conn = duckdb.connect()
    
    results = {"regions": {}}
    
    salary_query = f"""
        SELECT 
            area,
            COUNT(*) as vacancy_count,
            MEDIAN(CAST(COALESCE(NULLIF(salary_from, ''), NULLIF(salary_to, '')) AS DOUBLE)) as median_salary
        FROM read_csv_auto(?, all_varchar=true)
        WHERE area IN ({','.join([f"'{r}'" for r in TARGET_REGIONS])})
          AND COALESCE(NULLIF(salary_from, ''), NULLIF(salary_to, '')) IS NOT NULL
        GROUP BY area
        ORDER BY median_salary DESC
    """
    salary_data = conn.execute(salary_query, [INPUT_CSV]).fetchall()
    
    for row in salary_data:
        region = row[0]
        results["regions"][region] = {
            "vacancy_count": row[1],
            "median_salary": row[2],
            "top_skills": []
        }
        print(f"{region}: {row[1]} вакансий, медиана ЗП: {row[2]:,.0f} руб.")

    skills_query = f"""
        SELECT 
            area,
            lower(trim(unnested_skill)) as skill,
            COUNT(*) as freq
        FROM read_csv_auto(?, all_varchar=true),
        UNNEST(string_split(COALESCE(key_skills, ''), ';')) AS t(unnested_skill)
        WHERE area IN ({','.join([f"'{r}'" for r in TARGET_REGIONS])})
          AND lower(trim(unnested_skill)) != ''
          AND lower(trim(unnested_skill)) != 'nan'
        GROUP BY area, lower(trim(unnested_skill))
        -- QUALIFY позволяет взять только топ-5 для каждого региона (PARTITION BY area)
        QUALIFY ROW_NUMBER() OVER(PARTITION BY area ORDER BY COUNT(*) DESC) <= 5
        ORDER BY area, freq DESC
    """
    skills_data = conn.execute(skills_query, [INPUT_CSV]).fetchall()
    
    for row in skills_data:
        region = row[0]
        skill = row[1]
        freq = row[2]
        if region in results["regions"]:
            results["regions"][region]["top_skills"].append({
                "skill": skill,
                "frequency": freq
            })

    output_path = os.path.join(OUTPUT_DIR, 'regions_analysis.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print(f"Результаты сохранены в {output_path}")
    conn.close()

if __name__ == '__main__':
    analyze_regions()