#!/usr/bin/env python
"""Script temporal para probar el import de websocket_server"""

import sys
from pathlib import Path

# Agregar el directorio necesario al path
sys.path.insert(0, str(Path(__file__).parent / "gesture_recognition_app" / "python_backend"))

try:
    from websocket_server import HandTrackingServer
    print("✓ Importación exitosa de HandTrackingServer")
    
    # Intentar crear una instancia
    server = HandTrackingServer(host="localhost", port=8765)
    print("✓ Instancia de HandTrackingServer creada correctamente")
    print(f"  - Usando TurboJPEG: {server.use_turbojpeg}")
    
    # Limpiar
    server.tracker.release()
    print("✓ Todo funcionando correctamente")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
