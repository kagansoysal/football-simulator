@echo off
chcp 65001 > nul
title Futbol Simulator - Champions League Weekly Update

echo ======================================================================
echo    CHAMPIONS LEAGUE - HAFTALIK GUNCELLEME / WEEKLY UPDATE
echo ======================================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [*] Guncel Fikstur, Elo ve 10.000 Simulasyon Calistiriliyor...
echo [*] Lutfen bekleyin, bu islem yaklasik 60 saniye surer...
echo.

"%PYTHON_EXE%" scripts\run_weekly_pipeline.py -c CL --notepad

echo.
echo ======================================================================
echo Sampiyonlar Ligi islemi tamamlandi. Rapor Notepad uzerinde acildi.
echo Log dosyasi: logs\latest_pipeline_cl.log
echo ======================================================================
pause
