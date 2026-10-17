# Review 3 demo script

No Docker is required.

1. Open PowerShell:

```powershell
cd "c:\Users\preet\Desktop\Data Forge"
py -m src.pipelines.run --mode all
py -m streamlit run src/dashboard.py
```

2. Show the dashboard in the browser (usually http://localhost:8501).
3. Use **Run pipeline** on the dashboard if the teacher asks you to run it live.
4. In the dashboard, show:
   - quality before vs after
   - raw vs clean tables
   - quarantine reasons
5. Backup files if needed:
   - `data/raw/production.csv`
   - `data/processed/production_clean.csv`
   - `reports/quality_report.md`
