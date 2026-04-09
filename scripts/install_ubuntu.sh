#!/bin/bash
# ===================================
# KINECT TABLE SYSTEM - INSTALACION UBUNTU
# ===================================
# Script de instalacion automatica para Ubuntu 20.04+
# Uso: ./scripts/install_ubuntu.sh

set -e

echo "=============================================="
echo "KINECT TABLE SYSTEM - Instalador Ubuntu"
echo "=============================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funcion para imprimir mensajes
print_status() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar que es Ubuntu/Debian
if ! command -v apt-get &> /dev/null; then
    print_error "Este script es solo para sistemas basados en Debian/Ubuntu"
    exit 1
fi

# Verificar version de Python
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python detectado: $PYTHON_VERSION"

# 1. Actualizar repositorios
echo ""
echo ">>> Actualizando repositorios..."
sudo apt-get update

# 2. Instalar dependencias del sistema
echo ""
echo ">>> Instalando dependencias del sistema..."
sudo apt-get install -y \
    libfreenect-dev \
    freenect \
    libusb-1.0-0-dev \
    python3-dev \
    python3-pip \
    python3-venv \
    build-essential \
    cmake \
    git \
    tesseract-ocr \
    libgl1-mesa-glx \
    libglib2.0-0

print_status "Dependencias del sistema instaladas"

# 3. Configurar permisos para Kinect
echo ""
echo ">>> Configurando permisos para Kinect..."

# Agregar usuario a grupos necesarios
sudo usermod -a -G plugdev $USER 2>/dev/null || true
sudo usermod -a -G video $USER 2>/dev/null || true

# Crear reglas udev para Kinect
UDEV_RULES="/etc/udev/rules.d/51-kinect.rules"
if [ ! -f "$UDEV_RULES" ]; then
    echo "Creando reglas udev para Kinect..."
    sudo bash -c "cat > $UDEV_RULES << 'EOF'
# Kinect Motor
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"045e\", ATTR{idProduct}==\"02b0\", MODE=\"0666\"
# Kinect Camera
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"045e\", ATTR{idProduct}==\"02ae\", MODE=\"0666\"
# Kinect Audio
SUBSYSTEM==\"usb\", ATTR{idVendor}==\"045e\", ATTR{idProduct}==\"02ad\", MODE=\"0666\"
EOF"
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    print_status "Reglas udev creadas"
else
    print_status "Reglas udev ya existen"
fi

# 4. Crear entorno virtual
echo ""
echo ">>> Creando entorno virtual Python..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_status "Entorno virtual creado"
else
    print_warning "Entorno virtual ya existe"
fi

# 5. Activar entorno e instalar dependencias Python
echo ""
echo ">>> Instalando dependencias Python..."
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

print_status "Dependencias Python instaladas"

# 6. Verificar instalacion
echo ""
echo ">>> Verificando instalacion..."

# Verificar OpenCV
python3 -c "import cv2; print(f'OpenCV: {cv2.__version__}')" && print_status "OpenCV OK" || print_error "OpenCV fallo"

# Verificar MediaPipe
python3 -c "import mediapipe; print(f'MediaPipe: {mediapipe.__version__}')" && print_status "MediaPipe OK" || print_error "MediaPipe fallo"

# Verificar NumPy
python3 -c "import numpy; print(f'NumPy: {numpy.__version__}')" && print_status "NumPy OK" || print_error "NumPy fallo"

# Verificar PyTorch
python3 -c "import torch; print(f'PyTorch: {torch.__version__}')" && print_status "PyTorch OK" || print_warning "PyTorch no instalado (opcional para GPU)"

# Verificar libfreenect
if [ -f "/usr/lib/libfreenect.so" ] || [ -f "/usr/lib/x86_64-linux-gnu/libfreenect.so" ]; then
    print_status "libfreenect encontrado"
else
    print_warning "libfreenect no encontrado en rutas estandar"
fi

echo ""
echo "=============================================="
echo "INSTALACION COMPLETADA"
echo "=============================================="
echo ""
echo "Proximos pasos:"
echo "1. Cerrar sesion y volver a iniciar (para aplicar grupos)"
echo "2. Conectar el Kinect Xbox 360"
echo "3. Verificar con: freenect-glview"
echo "4. Activar entorno: source venv/bin/activate"
echo "5. Ejecutar: python main.py --test"
echo ""
print_warning "IMPORTANTE: Debes cerrar sesion y volver a iniciar"
print_warning "para que los cambios de grupo surtan efecto."
echo ""
