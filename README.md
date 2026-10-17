# DataForge – Intelligent ETL & Data Quality Platform for Manufacturing

**Course:** Fundamentals of Data Engineering  
**Course Code:** 24DEA3101R  
**Academic Year:** 2026–2027  
**Team:** 11 | **Section:** 7  

| S. No. | University ID | Name |
|---|---|---|
| 1 | 2420030302 | V. Preetham Nikil |
| 2 | 2420030291 | V. Chandra |
| 3 | 2420030461 | G. Khethana |

**Guide:** Dr. N. Shirisha, Associate Professor, KLH University Hyderabad

---

## 1. Project overview

Manufacturing plants generate data from production lines, machine sensors, inventory, maintenance, and quality inspection. That data is often fragmented and dirty: missing readings, duplicate records, invalid measurements, and inconsistent formats.

DataForge is an automated ETL and data-quality platform that turns raw manufacturing data into clean, validated, structured, analysis-ready tables.

## 2. Proposed pipeline

```text
Manufacturing Data Sources
          ↓
     Data Ingestion
          ↓
     Apache Kafka (or local file bus)
          ↓
     Apache PySpark / pandas ETL
          ↓
     Data Cleaning + Quality Validation
          ↓
     Clean data / Quarantine
          ↓
     MySQL or SQLite
          ↓
     Results, charts, dashboard
```

## 3. Repository structure

```text
DataForge/
├── config/                 # pipeline and data-quality rules
├── src/                    # ingestion, ETL, quality, storage, pipelines
├── data/raw|staging|processed
├── docs/
├── results/                # scores, charts, run log
├── reports/                # Review 3 quality report
├── sql/                    # MySQL schema
├── tests/
└── README.md
```

## 4. Review 3 – what is implemented

| Pipeline | Module | What it does |
|---|---|---|
| Data generation | `src/generate_data.py` | Creates dirty data for 5 manufacturing sources |
| Ingest | `src/pipelines/ingest.py` | Reads files and publishes to Kafka/file topics |
| Stream | `src/pipelines/stream.py` | Consumes topics as a streaming layer |
| Transform | `src/pipelines/transform.py` | Cleans and standardizes with pandas or PySpark |
| Quality | `src/pipelines/quality.py` | Scores completeness, uniqueness, validity, consistency, timeliness |
| Load | `src/pipelines/load.py` | Stores only validated rows; quarantine + metrics tables |
| Orchestrator | `src/pipelines/run.py` | Runs the full Review 3 flow |
| Dashboard | `src/dashboard.py` | Streamlit view of before/after quality |

Quality issues handled: missing values, duplicates, invalid values, inconsistent formats, incorrect types, out-of-range measurements.

## 5. Setup

### Prerequisites

- Python 3.11+
- Git

```powershell
cd "c:\Users\preet\Desktop\Data Forge"
copy .env.example .env
py -m pip install pandas numpy PyYAML python-dotenv SQLAlchemy matplotlib streamlit
```

## 6. Run the pipeline and dashboard

No Docker, Kafka broker, or MySQL server is required.

```powershell
cd "c:\Users\preet\Desktop\Data Forge"
py -m src.pipelines.run --mode all
py -m streamlit run src/dashboard.py
```

The dashboard also has a **Run pipeline now** button.

Clean data is stored in `results/dataforge.db` and `data/processed/`.

## 7. Outputs to show in Review 3

- `reports/quality_report.md` – before/after scores
- `results/quality_before_after.png` – comparison chart
- `results/quality_dimensions.png` – completeness, uniqueness, validity, consistency, timeliness
- `data/processed/*_clean.csv` – analytics-ready extracts (Power BI)
- `data/processed/quarantine/` – rejected records with reason codes
- `results/dataforge.db` – `fact_*`, `dq_metrics`, `quarantine_records`, `pipeline_runs`

## 8. Data security

Do not commit `.env`, passwords, API keys, or confidential plant data. This repository uses synthetic manufacturing data only.

## 9. Tests

```powershell
py -m unittest tests.test_quality
```

## 10. Current phase status

**Current phase:** Review 3 – ETL pipeline implementation  

Implemented: repository structure, synthetic multi-source manufacturing data, ingestion, Kafka/file streaming, PySpark/pandas ETL, data-quality validation, storage, evaluation report, and dashboard.

---

Team members should commit from their own GitHub accounts. Tag this milestone as `review-3` when the faculty submission is ready.
