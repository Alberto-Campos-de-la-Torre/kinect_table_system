@echo off
echo ====================================================
echo   HAND GESTURE RECOGNITION - INICIO RAPIDO
echo ====================================================
echo.

echo [1/2] Iniciando servidor Python...
start "Python Backend" cmd /k "cd python_backend && python websocket_server.py"

timeout /t 3 /nobreak >nul

echo [2/2] Iniciando aplicacion Tauri...
start "Tauri Frontend" cmd /k "npm run tauri:dev"

echo.
echo ====================================================
echo   Aplicacion iniciada!
echo   - Servidor Python: ws://localhost:8765
echo   - Frontend Tauri: http://localhost:1420
echo ====================================================
echo.
echo Presiona cualquier tecla para cerrar este mensaje...
pause >nul
