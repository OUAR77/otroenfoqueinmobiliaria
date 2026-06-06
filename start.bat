@echo off
title Otro Enfoque Inmobiliaria
cd /d "%~dp0"

echo ============================================
echo   Otro Enfoque Inmobiliaria - Servidor Web
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado.
    echo Descargalo desde: https://www.python.org/downloads/
    pause
    exit /b
)

:: Create venv if needed
if not exist "venv" (
    echo Instalando entorno virtual...
    python -m venv venv
)

:: Install requirements
echo Instalando dependencias...
call venv\Scripts\pip install -q -r requirements.txt

:: Start server
echo.
echo Servidor iniciado en: http://localhost:8022
echo Abrelo en el navegador.
echo Presiona CTRL+C para cerrar.
echo.
call venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8022

pause
