# DataForge system architecture

```text
 Production | Sensors | Inventory | Maintenance | Quality inspection
                              |
                     Python ingestion layer
                              |
              Local streaming topics
                              |
                 pandas ETL
                              |
              Repair + standardize + validate
                     /                    \
            Validated clean data     Quarantine (reason codes)
                     |
        SQLite warehouse (results/dataforge.db)
                     |
        Quality report, charts, Streamlit dashboard, Power BI CSV
```

## Source systems

All sources belong to one plant (`PLANT-HYD-01`) so Review 3 can show integration of heterogeneous departmental data rather than unrelated public datasets.

## Quality dimensions

Weighted overall score (see `config/pipeline.yaml`):

- Completeness 25%
- Uniqueness 20%
- Validity 25%
- Consistency 20%
- Timeliness 10%

Raw data is scored before ETL and clean data is scored after ETL. Only validated rows are loaded to the warehouse tables.
