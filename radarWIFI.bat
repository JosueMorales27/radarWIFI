@echo off
REM ==========================================================
REM  radarWIFI - launcher click-ready
REM  Arranca el servidor local y abre el radar en el navegador.
REM ==========================================================
title radarWIFI
cd /d "%~dp0"

REM Genera el icono la primera vez (si Pillow esta instalado)
if not exist "radar.ico" (
    python make_icon.py >nul 2>&1
)

echo.
echo   ================================================
echo     radarWIFI  //  radar de redes 100%% local
echo   ================================================
echo.

REM Intenta con 'python', si no, con 'py'
python --version >nul 2>&1
if %errorlevel%==0 (
    python server.py
) else (
    py server.py
)

echo.
echo   El servidor se detuvo. Presiona una tecla para salir.
pause >nul
