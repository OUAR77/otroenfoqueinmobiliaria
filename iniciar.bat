@echo off
title OtroEnfoque Inmobiliaria
echo ========================================
echo   Otro Enfoque Inmobiliaria - Web Local
echo ========================================
echo.
cd /d "%~dp0"
start "" "%~dp0OtroEnfoque\OtroEnfoque.exe"
timeout /t 4 >nul
start "" "http://localhost:8022"
echo.
echo Servidor iniciado en http://localhost:8022
echo.
pause
