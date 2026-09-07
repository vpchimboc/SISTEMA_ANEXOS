@echo off
chcp 65001 >nul
title Instalacion - Sistema de Anexos de Vinculacion
cd /d "%~dp0"

echo ============================================================
echo  Sistema de Anexos de Vinculacion - Instalacion
echo ============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se encontro Python.
    echo Instalalo desde https://www.python.org/downloads/
    echo IMPORTANTE: marca la casilla "Add Python to PATH".
    pause
    exit /b 1
)

echo [1/3] Creando entorno virtual...
if not exist ".venv" python -m venv .venv

echo [2/3] Instalando dependencias...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de dependencias.
    pause
    exit /b 1
)

echo [3/3] Construyendo las plantillas desde los anexos oficiales...
python herramientas\construir_plantillas.py
if errorlevel 1 (
    echo.
    echo [AVISO] Revisa los mensajes de arriba: alguna regla no encontro su texto.
    echo Puede que el formato oficial haya cambiado.
)

echo.
echo ============================================================
echo  Listo. Ejecuta iniciar.bat para abrir el sistema.
echo ============================================================
pause
