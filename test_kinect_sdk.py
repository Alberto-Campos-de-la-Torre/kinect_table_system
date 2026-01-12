"""
Script de diagnÃ³stico para Kinect SDK 1.8
=========================================
"""

import ctypes
import os
import sys

# Forzar UTF-8 en la salida
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 60)
print("DIAGNOSTICO DE KINECT SDK 1.8")
print("=" * 60)

# Verificar arquitectura de Python
print(f"\nPython: {sys.version}")
print(f"Arquitectura: {'64-bit' if sys.maxsize > 2**32 else '32-bit'}")

# Buscar DLLs
print("\n--- Buscando DLLs de Kinect ---")

dlls_to_check = [
    (r"C:\Windows\System32\Kinect10.dll", "Kinect10.dll (System32)"),
    (r"C:\Windows\SysWOW64\Kinect10.dll", "Kinect10.dll (SysWOW64)"),
    (r"C:\Windows\System32\Kinect20.dll", "Kinect20.dll (SDK 2.0)"),
]

for path, name in dlls_to_check:
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"  [OK] {name}: {path} ({size:,} bytes)")
    else:
        print(f"  [NO] {name}: No encontrado")

# Verificar variables de entorno
print("\n--- Variables de entorno ---")
env_vars = ["KINECTSDK10_DIR", "KINECTSDK20_DIR"]
for var in env_vars:
    value = os.environ.get(var, "No definida")
    print(f"  {var}: {value}")

# Intentar cargar el SDK
print("\n--- Probando SDK 1.8 ---")

try:
    dll_path = r"C:\Windows\System32\Kinect10.dll"
    if not os.path.exists(dll_path):
        dll_path = r"C:\Windows\SysWOW64\Kinect10.dll"
    
    kinect = ctypes.WinDLL(dll_path)
    print(f"  [OK] DLL cargada: {dll_path}")
    
    # Contar sensores
    NuiGetSensorCount = kinect.NuiGetSensorCount
    NuiGetSensorCount.argtypes = [ctypes.POINTER(ctypes.c_int)]
    NuiGetSensorCount.restype = ctypes.c_long
    
    count = ctypes.c_int(0)
    hr = NuiGetSensorCount(ctypes.byref(count))
    
    if hr == 0:
        print(f"  [OK] Sensores detectados: {count.value}")
    else:
        print(f"  [ERROR] Error contando sensores: 0x{hr & 0xFFFFFFFF:08X}")
    
    if count.value > 0:
        # Intentar crear sensor
        print("\n--- Intentando crear sensor ---")
        
        NuiCreateSensorByIndex = kinect.NuiCreateSensorByIndex
        NuiCreateSensorByIndex.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
        NuiCreateSensorByIndex.restype = ctypes.c_long
        
        sensor_ptr = ctypes.c_void_p()
        hr = NuiCreateSensorByIndex(0, ctypes.byref(sensor_ptr))
        
        if hr == 0:
            print(f"  [OK] Sensor creado: {sensor_ptr.value}")
            
            # Obtener estado del sensor
            # NuiStatus estÃ¡ en la vtable del sensor
            vtable_ptr = ctypes.cast(sensor_ptr, ctypes.POINTER(ctypes.c_void_p))
            vtable = ctypes.cast(vtable_ptr[0], ctypes.POINTER(ctypes.c_void_p * 25)).contents
            
            # NuiStatus estÃ¡ en Ã­ndice 4
            try:
                NuiStatus = ctypes.cast(
                    vtable[4],
                    ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_void_p)
                )
                status = NuiStatus(sensor_ptr)
                print(f"  Estado del sensor: 0x{status & 0xFFFFFFFF:08X}")
                
                if status == 0:
                    print("  [OK] Sensor listo para usar")
                elif status == 0x83010001:
                    print("  [WARN] Sensor no conectado")
                elif status == 0x83010002:
                    print("  [WARN] Sensor no inicializado")
                else:
                    print(f"  [WARN] Estado desconocido")
            except Exception as e:
                print(f"  [WARN] No se pudo obtener estado: {e}")
            
            # Intentar inicializar con diferentes flags
            print("\n--- Probando inicializaciÃ³n ---")
            
            flag_tests = [
                (0x00000010, "Solo COLOR"),
                (0x00000020, "Solo DEPTH"),
                (0x00000030, "COLOR + DEPTH"),
            ]
            
            for flags, desc in flag_tests:
                # NuiInitialize del sensor estÃ¡ en Ã­ndice 3
                try:
                    NuiSensorInit = ctypes.cast(
                        vtable[3],
                        ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_uint32)
                    )
                    hr = NuiSensorInit(sensor_ptr, flags)
                    
                    if hr == 0:
                        print(f"  [OK] {desc}: OK")
                        
                        # Shutdown
                        NuiSensorShutdown = ctypes.cast(
                            vtable[5],
                            ctypes.CFUNCTYPE(None, ctypes.c_void_p)
                        )
                        NuiSensorShutdown(sensor_ptr)
                    else:
                        hr_unsigned = hr & 0xFFFFFFFF
                        print(f"  [ERROR] {desc}: 0x{hr_unsigned:08X}")
                except Exception as e:
                    print(f"  [ERROR] {desc}: Error - {e}")
            
            # Liberar sensor
            Release = ctypes.cast(
                vtable[2],
                ctypes.CFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
            )
            Release(sensor_ptr)
            
        else:
            hr_unsigned = hr & 0xFFFFFFFF
            print(f"  [ERROR] Error creando sensor: 0x{hr_unsigned:08X}")
    
    # Probar NuiInitialize global
    print("\n--- Probando NuiInitialize global ---")
    
    NuiInitialize = kinect.NuiInitialize
    NuiInitialize.argtypes = [ctypes.c_uint32]
    NuiInitialize.restype = ctypes.c_long
    
    NuiShutdown = kinect.NuiShutdown
    NuiShutdown.argtypes = []
    NuiShutdown.restype = None
    
    for flags, desc in [(0x10, "COLOR"), (0x20, "DEPTH"), (0x30, "COLOR+DEPTH")]:
        hr = NuiInitialize(flags)
        if hr == 0:
            print(f"  [OK] NuiInitialize({desc}): OK")
            NuiShutdown()
        else:
            hr_unsigned = hr & 0xFFFFFFFF
            print(f"  [ERROR] NuiInitialize({desc}): 0x{hr_unsigned:08X}")

except Exception as e:
    print(f"  [ERROR] Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("FIN DEL DIAGNÃ“STICO")
print("=" * 60)

print("\n[INFO] POSIBLES SOLUCIONES:")
print("  1. Reiniciar el PC")
print("  2. Desinstalar SDK 2.0 si no lo necesitas")
print("  3. Ejecutar 'Kinect for Windows Developer Toolkit v1.8'")
print("  4. Reinstalar SDK 1.8")
print("  5. Verificar en Device Manager que el Kinect aparece correctamente")

