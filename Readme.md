# HW#3 Data Engineering - Вариант 9 (Мобильная разработка)

Лабораторная работа №3 по курсу Data Engineering (ITMO).  
**Вариант 9:** Программист, разработчик на мобильных платформах.

Полный аналитический пайплайн: RustFS в MapReduce (v1 naive + v2 optimized) в DuckDB в анализ навыков в анализ зарплат в региональный анализ в профилирование в бонусная оптимизация.

## Датасет

В бакет `hh-lake` грузится отфильтрованный файл `vacancies_mobile_2024.csv` по S3-ключу `raw/vacancies_mobile_2024.csv`.

**Фильтрация для Варианта 9 (строгая IT-фильтрация):**
- Поле `role`: содержит `программист` ИЛИ `разработчик` ИЛИ `developer` ИЛИ `engineer`.
- Поле `name` ИЛИ `key_skills`: содержит `android` ИЛИ `ios` ИЛИ `swift` ИЛИ `kotlin` ИЛИ `flutter` ИЛИ `react native`.

Такая двойная фильтрация отсеивает нерелевантные вакансии (логистика, продажи, мерчандайзинг) и оставляет только вакансии мобильных разработчиков.

Разделитель в `key_skills` - `;`. Навыки нормализуются: `lower()` + `strip()`, дубликаты внутри вакансии удаляются.

## Схема CSV (23 колонки)

```
source, vacancy_id, status, snapshot_date, published_at, area,
employer_id, employer_inn, employer_ogrn, employer_name, name, role,
sphere, salary_from, salary_to, currency, gross, experience, schedule,
employment, key_skills, description, url
```

## Структура репозитория

```
.
├── README.md
├── requirements.txt            # boto3, pandas, duckdb, psutil
├── .gitignore
│
├── src/
│   ├── common.py              # S3-клиент для RustFS (endpoint, credentials)
│   ├── upload.py              # Фильтрация + загрузка в raw/vacancies_mobile_2024.csv
│   ├── upload_only.py         # Только загрузка готового файла (без фильтрации)
│   ├── mapreduce_skills.py    # Оптимизированный MapReduce (v2: chunked + combiner)
│   ├── mapreduce_v1.py        # Наивный MapReduce (v1: baseline для бонуса)
│   ├── duckdb_skills.py       # DuckDB SQL через read_csv_auto
│   ├── verify.py              # Строгое сравнение MapReduce == DuckDB
│   ├── analyze_salary.py      # Анализ влияния навыков на зарплату (singles/pairs/triples)
│   ├── analyze_regions.py     # Сравнение регионов (Москва, СПб, Екатеринбург)
│   └── profile.py             # 3×3 профайлинг: v1/v2/duckdb (время + память)
│
├── data/
│   ├── vacancies_mobile_2024.csv  # отфильтрованный датасет (~5000 вакансий)
│   ├── temp_mapreduce/            # временные файлы MapReduce
│   ├── results_v1_skills_*.json   # результаты MapReduce (singles/pairs/triples)
│   ├── results_duckdb/            # результаты DuckDB
│   ├── results_salary/            # анализ зарплат
│   ├── results_regions/           # региональный анализ
│   └── results_profile/           # профилирование
│
└── report/
    └── report.pdf                 # итоговый отчёт
```

## Отчёт (`report/report.pdf`)

Отчёт собирается вручную в PDF из таблиц `data/results_*/` и скриншотов:
- RustFS Web UI (http://localhost:9001)
- Вывод `python src/verify.py` (совпадение контрольных чисел)
- Вывод `python src/profile.py` (сравнение времени и памяти)
- Таблицы из `salary_analysis.json` и `regions_analysis.json`

## Запуск пайплайна

### 1. Поднять RustFS

```powershell
docker run -d --name rustfs -e RUSTFS_UNSAFE_BYPASS_DISK_CHECK=true `
  -p 9000:9000 -p 9001:9001 `
  -v "$PWD/disk1:/data/disk1" -v "$PWD/disk2:/data/disk2" `
  -v "$PWD/disk3:/data/disk3" -v "$PWD/disk4:/data/disk4" `
  rustfs/rustfs:latest server /data/disk1 /data/disk2 /data/disk3 /data/disk4 `
  --console-address ":9001"

# Проверка
docker ps --filter "name=rustfs"
```

### 2. Установить зависимости

```powershell
pip install boto3 pandas duckdb psutil
```

### 3. Загрузить данные (фильтрация + загрузка в S3)

```powershell
cd C:\github\ingdan\Data-Engineering
python src/upload.py
```

### 4. Запустить MapReduce (оптимизированный)

```powershell
python src/mapreduce_skills.py
```

### 5. Запустить DuckDB

```powershell
python src/duckdb_skills.py
```

### 6. Верификация

```powershell
python src/verify.py
```

### 7. Анализ зарплат

```powershell
python src/analyze_salary.py
```

### 8. Региональный анализ

```powershell
python src/analyze_regions.py
```

### 9. Профилирование (3 запуска каждого подхода)

```powershell
python src/profile.py
```

### 10. Бонус: сравнение наивного и оптимизированного MapReduce

```powershell
# Запустить наивный MapReduce (v1)
python src/mapreduce_v1.py

# Запустить профилирование v1 vs v2
python src/profile.py
```

## Регионы

По умолчанию: **Москва, Санкт-Петербург, Екатеринбург**.

Скрипт `analyze_regions.py` фильтрует по полю `area` и считает:
- Количество вакансий
- Медианную зарплату
- Топ-5 навыков (через `QUALIFY ROW_NUMBER()`)

## Аналитические инсайты

**Анализ зарплат (`analyze_salary.py`):**
- Глобальная медиана: ~150 000 руб. (после строгой IT-фильтрации)
- Навыки, повышающие зарплату: `kotlin + coroutines`, `swift + ci/cd` (маркеры Middle/Senior)
- Навыки, понижающие зарплату: `грамотная речь`, `пользователь пк` (маркеры Junior/стажировок)

**Региональный анализ (`analyze_regions.py`):**
- Москва: 180 000 руб. (752 вакансии)
- Санкт-Петербург: 140 000 руб. (261 вакансия)
- Екатеринбург: 140 000 руб. (85 вакансий)
- Вывод: разрыв между Москвой и Екатеринбургом <20%, что говорит о зрелости регионального IT-рынка

**Бонусное задание (оптимизация MapReduce):**
- v1 (наивный): читает весь файл в память, нет combiner
- v2 (оптимизированный): chunked reading + combiner + детерминированная сортировка
- Результат: v2 потребляет в ~2 раза меньше памяти и работает стабильнее на больших файлах