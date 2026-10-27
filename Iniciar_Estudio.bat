@echo off
setlocal
chcp 65001 >nul
title Entorno de Estudio - Universidad UTe
cd /d "%~dp0"

set "PY=C:\Users\kenny\miniconda3\python.exe"
set "APP=scripts\streamlit_app.py"

echo ============================================================
echo   Entorno de Estudio - Psicologia Clinica (Universidad UTe)
echo ============================================================
echo.

if not exist "%PY%" (
    echo [ERROR] No se encontro Python de miniconda en:
    echo         %PY%
    echo.
    echo Instala las dependencias o edita la variable PY de este archivo.
    pause
    exit /b 1
)

"%PY%" -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Streamlit no esta instalado en ese Python.
    echo.
    echo Ejecuta:
    echo     "%PY%" -m pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "%APP%" (
    echo [ERROR] No se encontro la aplicacion:
    echo         %CD%\%APP%
    pause
    exit /b 1
)

echo Carpeta:  %CD%
echo Python:   %PY%
echo.
echo Abriendo la aplicacion en el navegador...
echo Para cerrarla, cierra esta ventana o pulsa Ctrl+C.
echo.

"%PY%" -m streamlit run "%APP%" --browser.gatherUsageStats false %*

if errorlevel 1 (
    echo.
    echo [ERROR] La aplicacion termino con un error. Revisa el mensaje de arriba.
    pause
)

endlocal
