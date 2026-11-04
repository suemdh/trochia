# Trochiá weekly retrain job -- registered as a Windows Scheduled Task
# (see scripts/setup_scheduled_retrain.ps1). Run manually any time with:
#   powershell -File scripts\retrain_weekly.ps1

$ErrorActionPreference = "Continue"
Set-Location (Join-Path $PSScriptRoot "..")

$ts  = Get-Date -Format "yyyyMMdd_HHmmss"
$log = "outputs\retrain_log_$ts.txt"
New-Item -ItemType Directory -Force -Path "outputs" | Out-Null

"=== Trochia weekly retrain started $(Get-Date) ===" | Tee-Object -FilePath $log

# 1. Refresh raw FRED/USDA data (yfinance is fetched on demand by train_pipeline.py itself).
& .\.venv\Scripts\python.exe main.py *>> $log

# 2. Re-forecast every commodity. --fresh skips the resume-and-skip behavior
# and builds the new set in forecasts_partial.csv, swapping it in only once
# complete -- so the dashboard keeps showing the last full set the whole time,
# instead of "unavailable" and then a half-built table for hours.
if (Test-Path "outputs\forecasts.csv") {
    Copy-Item "outputs\forecasts.csv" "outputs\forecasts_previous.csv" -Force
}
& .\.venv\Scripts\python.exe src\models\train_pipeline.py --fresh *>> $log

# 3. Recompute the sector-wide volatility check across the freshly written
# rows (train_pipeline.py's own run() already does this, but this line is a
# harmless, cheap safety net if the run above ever partially fails and a
# manual backfill is needed instead).
& .\.venv\Scripts\python.exe src\models\backfill_volatility.py *>> $log

# 4. Score any past forecasts that have now come due against what actually
# happened -- the real track-record evidence for forecast trustworthiness.
& .\.venv\Scripts\python.exe src\models\track_record.py *>> $log

# 5. Data-health check (plausible-range + continuity on every price) and
# refresh the published backtest summary from the new numbers.
& .\.venv\Scripts\python.exe src\models\validate_prices.py *>> $log
if ($LASTEXITCODE -ne 0) { "!!! DATA HEALTH CHECK FAILED -- see validation_report.csv !!!" | Tee-Object -FilePath $log -Append }
& .\.venv\Scripts\python.exe tests\test_trust.py *>> $log
if ($LASTEXITCODE -ne 0) { "!!! TRUST TESTS FAILED -- see log above !!!" | Tee-Object -FilePath $log -Append }
& .\.venv\Scripts\python.exe scripts\write_backtest_doc.py *>> $log

"=== Trochia weekly retrain finished $(Get-Date) ===" | Tee-Object -FilePath $log -Append
