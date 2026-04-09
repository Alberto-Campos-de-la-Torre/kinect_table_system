# Guia de Inicio Rapido (Ubuntu/Linux)

## Instalacion en 5 Pasos

### 1. Clonar el Repositorio
```bash
git clone https://github.com/tu-usuario/kinect_table_system.git
cd kinect_table_system
```

### 2. Crear Entorno Virtual
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependencias Python
```bash
pip install -r requirements.txt
```

### 4. Instalar Drivers del Kinect Xbox 360

```bash
# Actualizar repositorios
sudo apt-get update

# Instalar libfreenect y dependencias
sudo apt-get install -y libfreenect-dev freenect libusb-1.0-0-dev python3-freenect

# Agregar usuario al grupo plugdev para acceso al Kinect sin sudo
sudo usermod -a -G plugdev $USER

# Crear reglas udev para el Kinect
sudo bash -c 'cat > /etc/udev/rules.d/51-kinect.rules << EOF
# Kinect Motor
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02b0", MODE="0666"
# Kinect Camera
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02ae", MODE="0666"
# Kinect Audio
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02ad", MODE="0666"
EOF'

# Recargar reglas udev
sudo udevadm control --reload-rules && sudo udevadm trigger

# IMPORTANTE: Cerrar sesion y volver a iniciar para aplicar cambios de grupo
```

### 5. Descargar Modelos
```bash
python scripts/download_models.py
```

## Verificar Instalacion

### Verificar Kinect:
```bash
# Probar visualizacion del Kinect
freenect-glview
```

### Ejecutar el sistema en modo prueba:
```bash
python main.py --test
```

## Primeros Pasos

### Ejecutar el Sistema
```bash
python main.py
```

### Calibrar el Kinect
```bash
python main.py --calibrate
```

### Modo Demostracion
```bash
python main.py --demo
```

### Sin Kinect Fisico (Simulacion con webcam)
```bash
python main.py --simulation tu_video.mp4
```

## Proximos Pasos

1. Lee el [README.md](README.md) completo
2. Revisa la [documentacion](docs/)
3. Explora los [ejemplos](examples/)

## Problemas Comunes

### "No module named 'freenect'" o biblioteca no encontrada
**Solucion:**
```bash
sudo apt-get install libfreenect-dev freenect python3-freenect
pip install freenect
```

### "Kinect not detected" o "Permission denied"
**Soluciones:**
1. Verificar conexion USB del Kinect (usar puerto USB 2.0 o 3.0)
2. Verificar que el adaptador de corriente AC este conectado
3. Aplicar reglas udev:
```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```
4. Cerrar sesion y volver a iniciar (para aplicar cambios de grupo)
5. Probar con sudo temporalmente:
```bash
sudo freenect-glview
```

### Error de permisos USB
**Solucion:**
```bash
# Verificar que el usuario este en el grupo plugdev
groups $USER

# Si no aparece plugdev, agregarlo
sudo usermod -a -G plugdev $USER

# Cerrar sesion e iniciar de nuevo
```

### Error de CUDA (GPU no detectada)
**Solucion:** Si no tienes GPU NVIDIA, ejecuta:
```bash
python main.py --no-gpu
```

### La camara no se detecta (modo simulacion)
**Solucion:**
```bash
# Agregar usuario al grupo video
sudo usermod -a -G video $USER

# Cerrar sesion e iniciar de nuevo
```

## Soporte

Necesitas ayuda?
- [Documentacion completa](docs/)
- [Reportar un bug](https://github.com/tu-usuario/kinect_table_system/issues)

---

Listo para comenzar!
