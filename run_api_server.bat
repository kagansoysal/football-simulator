@echo off
chcp 65001 > nul
title Football Simulator - API Server (FastAPI + Uvicorn)

echo ======================================================================
echo           FOOTBALL SIMULATOR REST API SERVER
echo ======================================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "UVICORN_EXE=.venv\Scripts\uvicorn.exe"
) else (
    set "UVICORN_EXE=uvicorn"
)

echo [*] Swagger UI Adresi : http://localhost:8000/docs
echo [*] ReDoc Adresi      : http://localhost:8000/redoc
echo [*] Sunucu baslatiliyor (Port: 8000)...
echo [*] Durdurmak icin: Ctrl + C
echo.

"%UVICORN_EXE%" src.main:app --host 0.0.0.0 --port 8000 --reload
pause
