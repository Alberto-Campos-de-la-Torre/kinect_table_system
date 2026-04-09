"""
Script de diagnostico para Kinect en Ubuntu/Linux
=================================================
Verifica la instalacion de libfreenect y conectividad del Kinect Xbox 360
"""

import os
import sys
import ctypes
from ctypes import c_void_p, c_int, POINTER, byref

print("=" * 60)
print("DIAGNOSTICO DE KINECT - UBUNTU/LINUX")
print("=" * 60)

# Verificar sistema operativo
print(f"\nPython: {sys.version}")
print(f"Plataforma: {sys.platform}")

if sys.platform == 'win32':
    print("\n[ERROR] Este script es para Ubuntu/Linux")
    print("        En Windows usa el SDK de Kinect para Windows")
    sys.exit(1)

# Verificar bibliotecas del sistema
print("\n--- Verificando bibliotecas del sistema ---")

lib_paths = {
    'libfreenect': [
        '/usr/lib/libfreenect.so',
        '/usr/lib/x86_64-linux-gnu/libfreenect.so',
        '/usr/local/lib/libfreenect.so',
        '/usr/lib/libfreenect.so.0',
        '/usr/lib/x86_64-linux-gnu/libfreenect.so.0',
    ],
    'libusb': [
        '/usr/lib/libusb-1.0.so',
        '/usr/lib/x86_64-linux-gnu/libusb-1.0.so',
        '/usr/lib/libusb-1.0.so.0',
        '/usr/lib/x86_64-linux-gnu/libusb-1.0.so.0',
    ]
}

found_libs = {}

for lib_name, paths in lib_paths.items():
    found = False
    for path in paths:
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"  [OK] {lib_name}: {path} ({size:,} bytes)")
            found_libs[lib_name] = path
            found = True
            break
    if not found:
        print(f"  [NO] {lib_name}: No encontrado")
        if lib_name == 'libfreenect':
            print("       Instalar con: sudo apt-get install libfreenect-dev freenect")
        elif lib_name == 'libusb':
            print("       Instalar con: sudo apt-get install libusb-1.0-0-dev")

# Verificar reglas udev
print("\n--- Verificando reglas udev ---")
udev_file = '/etc/udev/rules.d/51-kinect.rules'
if os.path.exists(udev_file):
    print(f"  [OK] Reglas udev encontradas: {udev_file}")
else:
    print(f"  [NO] Reglas udev no encontradas")
    print("       Crear con:")
    print("       sudo bash -c 'cat > /etc/udev/rules.d/51-kinect.rules << EOF")
    print('       SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02b0", MODE="0666"')
    print('       SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02ae", MODE="0666"')
    print('       SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02ad", MODE="0666"')
    print("       EOF'")

# Verificar grupos del usuario
print("\n--- Verificando grupos del usuario ---")
import grp
user_groups = [g.gr_name for g in grp.getgrall() if os.getlogin() in g.gr_mem]
try:
    user_groups.append(grp.getgrgid(os.getgid()).gr_name)
except:
    pass

required_groups = ['plugdev', 'video']
for group in required_groups:
    if group in user_groups:
        print(f"  [OK] Usuario en grupo: {group}")
    else:
        print(f"  [NO] Usuario NO en grupo: {group}")
        print(f"       Agregar con: sudo usermod -a -G {group} $USER")

# Verificar dispositivos USB conectados
print("\n--- Verificando dispositivos USB (Kinect) ---")
try:
    import subprocess
    result = subprocess.run(['lsusb'], capture_output=True, text=True)
    kinect_found = False

    # IDs del Kinect Xbox 360
    kinect_ids = ['045e:02b0', '045e:02ae', '045e:02ad']

    for line in result.stdout.split('\n'):
        for kid in kinect_ids:
            if kid in line.lower():
                print(f"  [OK] Kinect detectado: {line.strip()}")
                kinect_found = True

    if not kinect_found:
        print("  [NO] Kinect no detectado en USB")
        print("       Verificar:")
        print("       - El Kinect esta conectado via USB")
        print("       - El adaptador de corriente AC esta conectado")
        print("       - El LED del Kinect esta encendido")
except Exception as e:
    print(f"  [ERROR] No se pudo verificar USB: {e}")

# Intentar cargar libfreenect
print("\n--- Probando libfreenect ---")

if 'libfreenect' not in found_libs:
    print("  [ERROR] libfreenect no encontrado, no se puede continuar")
else:
    try:
        freenect = ctypes.CDLL(found_libs['libfreenect'])
        print(f"  [OK] libfreenect cargado: {found_libs['libfreenect']}")

        # Configurar funciones
        freenect.freenect_init.argtypes = [POINTER(c_void_p), c_void_p]
        freenect.freenect_init.restype = c_int
        freenect.freenect_num_devices.argtypes = [c_void_p]
        freenect.freenect_num_devices.restype = c_int
        freenect.freenect_shutdown.argtypes = [c_void_p]
        freenect.freenect_shutdown.restype = c_int

        # Inicializar contexto
        ctx = c_void_p()
        ret = freenect.freenect_init(byref(ctx), None)

        if ret >= 0:
            print("  [OK] Contexto freenect inicializado")

            # Contar dispositivos
            num_devices = freenect.freenect_num_devices(ctx)
            print(f"  [OK] Dispositivos Kinect encontrados: {num_devices}")

            if num_devices > 0:
                print("\n  *** KINECT LISTO PARA USAR ***")
            else:
                print("\n  [WARN] No hay Kinect conectado")
                print("         Verificar conexion USB y alimentacion")

            # Cerrar contexto
            freenect.freenect_shutdown(ctx)
            print("  [OK] Contexto cerrado")
        else:
            print(f"  [ERROR] Error inicializando freenect: {ret}")
            print("         Puede ser un problema de permisos USB")
            print("         Intentar: sudo python3 test_kinect_sdk.py")

    except Exception as e:
        print(f"  [ERROR] Error cargando libfreenect: {e}")
        import traceback
        traceback.print_exc()

# Verificar freenect-glview
print("\n--- Verificando herramientas de freenect ---")
try:
    import subprocess
    result = subprocess.run(['which', 'freenect-glview'], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  [OK] freenect-glview: {result.stdout.strip()}")
        print("       Ejecutar: freenect-glview (para probar visualizacion)")
    else:
        print("  [NO] freenect-glview no encontrado")
        print("       Instalar con: sudo apt-get install freenect")
except Exception as e:
    print(f"  [ERROR] No se pudo verificar freenect-glview: {e}")

print("\n" + "=" * 60)
print("FIN DEL DIAGNOSTICO")
print("=" * 60)

print("\n[INFO] POSIBLES SOLUCIONES SI HAY PROBLEMAS:")
print("  1. Instalar dependencias:")
print("     sudo apt-get install libfreenect-dev freenect libusb-1.0-0-dev")
print("  2. Crear reglas udev para permisos USB")
print("  3. Agregar usuario a grupos: sudo usermod -a -G plugdev,video $USER")
print("  4. Cerrar sesion e iniciar de nuevo")
print("  5. Si persiste, probar con: sudo freenect-glview")
print("")
