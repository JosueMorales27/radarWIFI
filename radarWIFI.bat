@echo off
REM ==========================================================
REM  radarWIFI - launcher click-ready
REM  Arranca el servidor local y abre el radar en el navegador.
REM  >>> NO CIERRES ESTA VENTANA <<<  (si la cierras, se apaga)
REM ==========================================================
title radarWIFI  --  NO CERRAR (esto mantiene el radar prendido)
cd /d "%~dp0"

REM Genera el icono la primera vez (si Pillow esta instalado)
if not exist "radar.ico" (
    python make_icon.py >nul 2>&1
)

REM Elige el interprete de Python disponible
set "PY="
python --version >nul 2>&1 && set "PY=python"
if not defined PY ( py --version >nul 2>&1 && set "PY=py" )

if not defined PY (
    echo.
    echo   [X] No se encontro Python en este equipo.
    echo       Instalalo desde https://python.org  (marca "Add to PATH").
    echo.
    pause
    exit /b 1
)

echo.
echo   ================================================
echo     radarWIFI PRO  //  NeoKali WiFi Analyzer (local)
echo   ================================================
echo     Servidor:  http://127.0.0.1:8777
echo     El navegador se abre solo en unos segundos.
echo.
echo     ^>^>^> DEJA ESTA VENTANA ABIERTA ^<^<^<
echo     (cerrarla apaga el radar)
echo   ================================================
echo.

REM El .bat abre el navegador solo (espera 3s a que el server levante).
REM Marca NOOPEN para que server.py no abra otra pestana (evita duplicados).
set "RADARWIFI_NOOPEN=1"
start "" /min cmd /c "timeout /t 3 /nobreak >nul & start "" http://127.0.0.1:8777/"

%PY% server.py

echo.
echo   El servidor se detuvo. Presiona una tecla para salir.
pause >nul
