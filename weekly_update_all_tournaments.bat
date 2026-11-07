@echo off
chcp 65001 > nul
title Futbol Simulator - All Tournaments Weekly Update

echo ======================================================================
echo    TUM TURNUVALAR HAFTALIK GUNCELLEME / ALL TOURNAMENTS UPDATE
echo       (1. Champions League  2. Europa League  3. Conference League)
echo ======================================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" scripts\run_all_weekly_tournaments.py

echo.
echo ======================================================================
echo Tum turnuvalarin guncellemesi ve 10.000'er simülasyonu tamamlandi!
echo Raporlar 'reports/' klasorunde hazirlandi.
echo ======================================================================

:: Eger gorev zamanlayici gibi arka plan ortaminda degilse, pencereyi acik tutmak icin bekle
if "%1" neq "--no-pause" (
    pause
)
