@echo off
REM ==========================================================
REM  radarWIFI PRO - launcher click-ready (SIN consola negra)
REM  Arranca el server en segundo plano (pythonw) y abre el
REM  navegador solo. No deja ventana colgada.
REM  Para APAGARLO: doble click en "Apagar radarWIFI.bat".
REM ==========================================================
cd /d "%~dp0"

REM Genera el icono la primera vez (si Pillow esta instalado)
if not exist "radar.ico" ( python make_icon.py >nul 2>&1 )

REM Interprete SIN consola: pythonw (preferido) -> pyw -> python /min
set "PYW="
where pythonw >nul 2>&1 && set "PYW=pythonw"
if not defined PYW ( where pyw >nul 2>&1 && set "PYW=pyw" )

REM NOOPEN: el navegador lo abre este .bat, no Python (evita pestana doble)
set "RADARWIFI_NOOPEN=1"

if defined PYW (
    start "" %PYW% server.py
) else (
    REM sin pythonw: consola minimizada para que no estorbe
    start "radarWIFI server (no cerrar)" /min python server.py
)

REM Espera 2s a que el server levante y abre el navegador por defecto
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8777/"

REM El .bat termina aqui: el server sigue vivo en segundo plano.
exit /b 0
