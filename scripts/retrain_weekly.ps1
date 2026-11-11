# Trochiá weekly retrain job -- registered as a Windows Scheduled Task
# (see scripts/setup_scheduled_retrain.ps1). Run manually any time with:
#   powershell -File scripts\retrain_weekly.ps1

$ErrorActionPreference = "Continue"
Set-Location (Join-Path $PSScriptRoot "..")

$ts  = Get-Date -Format "yyyyMMdd_HHmmss"
$log = "outputs\retrain_log_$ts.txt"
New-Item -ItemType Directory -Force -Path "outputs" | Out-Null

"=== Trochia weekly retrain started $(Get-Date) ===" | Tee-Object -FilePath $log

# 1. Refresh raw FRED/USDA data.
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

# 6. Publish: the live site (Streamlit Cloud) redeploys from GitHub, so push
# the refreshed data -- data files only, never code -- or the public site
# keeps showing last week's forecasts. Skipped if the trust tests failed, so a
# broken run never reaches the public site.
& .\.venv\Scripts\python.exe tests\test_trust.py *> $null
if ($LASTEXITCODE -eq 0) {
    git add outputs/forecasts.csv outputs/forecast_history.csv outputs/validation_report.csv `
            outputs/second_source_report.csv docs/backtest.md data/raw *>> $log
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        git commit -q -m "Weekly forecast refresh $(Get-Date -Format yyyy-MM-dd)" *>> $log
        $env:GIT_TERMINAL_PROMPT = "0"
        git push -q origin main *>> $log
        if ($LASTEXITCODE -eq 0) { "Published to GitHub -> live site" | Tee-Object -FilePath $log -Append }
        else { "!!! PUSH TO GITHUB FAILED -- live site not updated !!!" | Tee-Object -FilePath $log -Append }
    }
} else {
    "!!! NOT PUBLISHED: trust tests failed -- live site keeps last good forecasts !!!" | Tee-Object -FilePath $log -Append
}

"=== Trochia weekly retrain finished $(Get-Date) ===" | Tee-Object -FilePath $log -Append
