import time
import tracemalloc
import json
import os
import importlib
import sys
import shutil
import io
import contextlib
        

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_and_profile(module_name, func_name, runs=3):
    results = []
    
    for i in range(1, runs + 1):
        if module_name == 'mapreduce_skills':
            temp_dir = 'data/temp_mapreduce'
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir, exist_ok=True)

        tracemalloc.start()
        start_time = time.perf_counter()
        
        module = importlib.import_module(module_name)
        func = getattr(module, func_name)
        
        with contextlib.redirect_stdout(io.StringIO()):
            func()
        
        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        exec_time = end_time - start_time
        peak_memory_mb = peak / (1024 * 1024)
        
        results.append({
            "run": i, 
            "time_sec": round(exec_time, 2), 
            "peak_memory_mb": round(peak_memory_mb, 2)
        })
        print(f"Время: {exec_time:.2f} сек, Пик памяти: {peak_memory_mb:.2f} МБ")
        
    return results

if __name__ == '__main__':
    mr_results = run_and_profile('mapreduce_skills', 'run_mapreduce', runs=3)
    
    db_results = run_and_profile('duckdb_skills', 'run_duckdb', runs=3)
    
    output = {
        "mapreduce": mr_results,
        "duckdb": db_results
    }
    
    os.makedirs('data/results_profile', exist_ok=True)
    with open('data/results_profile/profiling_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    avg_mr_time = sum(r['time_sec'] for r in mr_results) / 3
    avg_mr_mem = sum(r['peak_memory_mb'] for r in mr_results) / 3
    avg_db_time = sum(r['time_sec'] for r in db_results) / 3
    avg_db_mem = sum(r['peak_memory_mb'] for r in db_results) / 3
    
    print(f"MapReduce: Среднее время = {avg_mr_time:.2f} сек | Средний пик памяти = {avg_mr_mem:.2f} МБ")
    print(f"DuckDB:    Среднее время = {avg_db_time:.2f} сек | Средний пик памяти = {avg_db_mem:.2f} МБ")