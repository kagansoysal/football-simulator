@echo off
chcp 65001 > nul
title Futbol Simulator - Gorev Zamanlayici Kurulumu

echo ======================================================================
echo    FUTBOL SIMULATOR - WINDOWS GOREV ZAMANLAYICI OTOMATIK KURULUM
echo ======================================================================
echo.
echo Bu script, simülasyon sistemini her Cuma sabahi saat 10:00'da
echo arka planda otomatik calisacak sekilde Windows'a kaydeder.
echo.

cd /d "%~dp0"
set "TASK_NAME=FutbolSimulator_HaftalikRapor"
set "BAT_PATH=%~dp0haftalik_guncelleme.bat"

echo [*] Gorev Adi   : %TASK_NAME%
echo [*] Calisacak   : Her Cuma saat 10:00
echo [*] Hedef Dosya : %BAT_PATH%
echo.

:: Windows Task Scheduler gorevini olustur
schtasks /create /tn "%TASK_NAME%" /tr "\"%BAT_PATH%\"" /sc weekly /d FRI /st 10:00 /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [BASARILI] Gorev basariyla kaydedildi!
    echo Her Cuma saat 10:00'da sistem otomatik calisip raporu hazirlayacaktir.
) else (
    echo.
    echo [BILGI] Yonetici izinleri gerekebilir. 
    echo Lutfen bu dosyaya sag tiklayip "Yonetici Olarak Calistir" secenegini deneyin.
)

echo.
pause
