$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir

# Python calistiricisi (.venv)
$pythonExe = Join-Path $projectDir ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python.exe"
}

$scriptPath = Join-Path $projectDir "scripts\run_all_weekly_tournaments.py"

# 1. Eski gorevi kaldir
$taskName = "FutbolSimulator_TumTurnuvalar_HaftalikRapor"
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "FutbolSimulator_HaftalikRapor" -Confirm:$false -ErrorAction SilentlyContinue

# 2. Dogrudan Python uzerinden arka planda sessiz ve garantili calisacak gorev tanimla
$action = New-ScheduledTaskAction -Execute $pythonExe -Argument "`"$scriptPath`"" -WorkingDirectory $projectDir
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Friday -At 10:00AM

# Bilgisayar o saatte kapaliysa acildiginda hemen calismasi icin StartWhenAvailable = $true
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)

# Kullanici oturum tipi (Standart yetki)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Futbol Simulator Tum Turnuvalar (CL, UEL, ECL) Haftalik Guncelleme ve Raporu" -Force

Write-Host "`n[BASARILI] Windows Gorev Zamanlayici gorevi kaydedildi:" -ForegroundColor Green
Write-Host "  * Gorev Adi : $taskName"
Write-Host "  * Calisacak : $pythonExe $scriptPath"
Write-Host "  * Dizin     : $projectDir"
Write-Host "  * Zaman     : Her Cuma saat 10:00 (Kacirilirsa PC acilinca calisir)`n"
