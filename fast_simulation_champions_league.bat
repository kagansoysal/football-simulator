@echo off
title Football Simulator - Champions League Fast Simulation
cd /d "%~dp0"

echo ======================================================================
echo    CHAMPIONS LEAGUE - HIZLI SIMULASYON / FAST SIMULATION
echo          (API Cagrilari Atlanir, Mevcut Verilerle Calisir)
echo ======================================================================
echo.

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [*] API cagrilari yapilmadan 10.000 CL simulasyonu baslatiliyor...
echo [*] Bu islem yaklasik 60-80 saniye surer, lutfen bekleyin...
echo.

"%PYTHON_EXE%" scripts\run_weekly_pipeline.py -c CL --skip-fetch --notepad

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [HATA] Simulasyon calisirken bir hata olustu! Hata Kodu: %ERRORLEVEL%
) else (
    echo.
    echo ======================================================================
    echo Hizli CL simulasyonu tamamlandi. Rapor Notepad uzerinde acildi.
    echo Log dosyasi: logs\latest_pipeline_cl.log
    echo ======================================================================
)

pause
