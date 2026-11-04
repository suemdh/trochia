# One-time setup: registers a Windows Scheduled Task that runs
# retrain_weekly.ps1 every Sunday at 3:00 AM. Run this once, manually:
#   powershell -File scripts\setup_scheduled_retrain.ps1
#
# To remove it later:
#   Unregister-ScheduledTask -TaskName "TrochiaWeeklyRetrain" -Confirm:$false

$TaskName   = "TrochiaWeeklyRetrain"
$ScriptPath = Join-Path $PSScriptRoot "retrain_weekly.ps1"

$Action  = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3am
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 6) -DontStopOnIdleEnd

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger `
    -Settings $Settings -Description "Weekly Trochia commodity forecast retrain" -Force

Write-Output "Registered scheduled task '$TaskName' -- runs every Sunday at 3:00 AM."
Write-Output "Remove it with: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
