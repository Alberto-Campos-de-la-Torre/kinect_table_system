#!/bin/bash

echo "===================================================="
echo "  HAND GESTURE RECOGNITION - INICIO RAPIDO"
echo "===================================================="
echo ""

echo "[1/2] Iniciando servidor Python..."
cd python_backend
gnome-terminal -- bash -c "python websocket_server.py; exec bash" 2>/dev/null || \
xterm -e "python websocket_server.py; bash" 2>/dev/null || \
osascript -e 'tell app "Terminal" to do script "cd \"$(pwd)\" && python websocket_server.py"' 2>/dev/null &

sleep 3

echo "[2/2] Iniciando aplicacion Tauri..."
cd ..
gnome-terminal -- bash -c "npm run tauri:dev; exec bash" 2>/dev/null || \
xterm -e "npm run tauri:dev; bash" 2>/dev/null || \
osascript -e 'tell app "Terminal" to do script "cd \"$(pwd)\" && npm run tauri:dev"' 2>/dev/null &

echo ""
echo "===================================================="
echo "  Aplicacion iniciada!"
echo "  - Servidor Python: ws://localhost:8765"
echo "  - Frontend Tauri: http://localhost:1420"
echo "===================================================="
