Set-StrictMode -Version Latest
Set-Location (Split-Path -Parent $PSScriptRoot)
Write-Host "Running DataForge pipeline..."
py -m src.pipelines.run --mode all
Write-Host "Opening dashboard..."
py -m streamlit run src/dashboard.py
