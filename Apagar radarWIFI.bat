@echo off
REM Apaga el server de radarWIFI PRO que corre en segundo plano (puerto 8777).
echo Apagando radarWIFI PRO...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr :8777 ^| findstr LISTENING') do taskkill /f /pid %%p >nul 2>&1
echo radarWIFI apagado. Puedes cerrar esta ventana.
timeout /t 2 /nobreak >nul
exit /b 0
