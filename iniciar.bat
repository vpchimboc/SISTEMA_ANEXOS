@echo off
chcp 65001 >nul
title Sistema de Anexos de Vinculacion
cd /d "%~dp0"

if not exist ".venv" (
    echo No se encontro el entorno. Ejecuta primero instalar.bat
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
echo Abriendo el sistema en el navegador...
streamlit run app.py
pause
