@echo off
title Football Simulator - Celery Worker
cd /d "%~dp0"

echo ======================================================================
echo           FOOTBALL SIMULATOR - CELERY WORKER PROCESS
echo ======================================================================
echo.

if exist ".venv\Scripts\celery.exe" (
    set "CELERY_EXE=.venv\Scripts\celery.exe"
) else (
    set "CELERY_EXE=celery"
)

echo [*] Redis Baglantisi : redis://localhost:6379/0
echo [*] Worker baslatiliyor (Windows Solo Pool)...
echo [*] Durdurmak icin: Ctrl + C
echo.

"%CELERY_EXE%" -A src.worker.celery_app.celery_app worker --loglevel=info -P solo
pause
