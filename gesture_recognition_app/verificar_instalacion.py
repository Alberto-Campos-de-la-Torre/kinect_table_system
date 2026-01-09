"""
Script de Verificación - Gesture Recognition App
=================================================
Verifica que todo esté instalado correctamente
"""

import sys
from pathlib import Path

print("=" * 60)
print("VERIFICACIÓN DE INSTALACIÓN")
print("=" * 60)
print()

# Verificar versión de Python
print(f"✓ Python: {sys.version}")
print()

# Verificar dependencias
print("Verificando dependencias...")
print()

dependencies = {
    'cv2': 'opencv-python',
    'mediapipe': 'mediapipe',
    'numpy': 'numpy',
    'websockets': 'websockets'
}

missing = []
installed = []

for module, package in dependencies.items():
    try:
        __import__(module)
        print(f"  ✓ {package}")
        installed.append(package)
    except ImportError:
        print(f"  ✗ {package} - NO INSTALADO")
        missing.append(package)

print()

if missing:
    print("❌ Faltan dependencias:")
    print()
    print("Ejecuta:")
    print(f"  pip install {' '.join(missing)}")
    print()
    print("O instala todo:")
    print("  pip install -r requirements.txt")
    sys.exit(1)
else:
    print("✅ Todas las dependencias están instaladas")
    print()

# Verificar estructura de archivos
print("Verificando estructura de archivos...")
print()

current_dir = Path(__file__).parent.parent
required_files = [
    'hand_tracking.py',
    'python_backend/websocket_server.py',
    'python_backend/test_hand_tracking.py',
    'src/App.jsx',
    'package.json'
]

missing_files = []
for file in required_files:
    file_path = current_dir / file
    if file_path.exists():
        print(f"  ✓ {file}")
    else:
        print(f"  ✗ {file} - NO ENCONTRADO")
        missing_files.append(file)

print()

if missing_files:
    print("❌ Faltan archivos:")
    print()
    for file in missing_files:
        print(f"  - {file}")
    print()
    print("Asegúrate de descomprimir todo el ZIP correctamente")
    sys.exit(1)
else:
    print("✅ Todos los archivos están presentes")
    print()

# Verificar que se puede importar hand_tracking
print("Verificando importación de hand_tracking...")
print()

try:
    sys.path.insert(0, str(current_dir))
    from hand_tracking import HandTracker, HandGesture
    print("  ✓ hand_tracking importado correctamente")
    print()
    print("✅ Sistema listo para usar")
    print()
except Exception as e:
    print(f"  ✗ Error al importar: {e}")
    print()
    print("❌ Hay un problema con hand_tracking.py")
    sys.exit(1)

# Intentar detectar cámara
print("Verificando cámara...")
print()

try:
    import cv2
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        print("  ✓ Cámara detectada")
        cap.release()
    else:
        print("  ⚠ No se detectó cámara")
        print("  (Puedes continuar, pero necesitarás una cámara para usar la app)")
except Exception as e:
    print(f"  ⚠ Error al verificar cámara: {e}")

print()
print("=" * 60)
print("PRÓXIMOS PASOS")
print("=" * 60)
print()
print("1. Probar el tracking standalone:")
print("   python python_backend/test_hand_tracking.py")
print()
print("2. Iniciar servidor WebSocket:")
print("   python python_backend/websocket_server.py")
print()
print("3. En otra terminal, iniciar Tauri:")
print("   npm run tauri:dev")
print()
print("=" * 60)
