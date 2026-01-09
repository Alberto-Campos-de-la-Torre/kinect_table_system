#!/usr/bin/env python3
"""
Iniciar Servidor de API de Gestos
===================================
Inicia el servidor WebSocket y HTTP REST para comunicación con Tauri

Uso:
    python examples/start_api_server.py
"""

import sys
from pathlib import Path

# Agregar módulos al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.gesture_api_server import main

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SERVIDOR DE API DE GESTOS")
    print("=" * 60)
    print("\nEste servidor proporciona:")
    print("  1. WebSocket en ws://localhost:8765 - Stream en tiempo real")
    print("  2. REST API en http://localhost:8000 - Endpoints HTTP")
    print("\nPara conectar desde Tauri:")
    print("  cd tauri-app")
    print("  npm install")
    print("  npm run tauri dev")
    print("\n" + "=" * 60 + "\n")
    
    main()
