# Kinect Table System - Sistema de Reconocimiento de Objetos Interactivo

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-en%20desarrollo-yellow)

## 📋 Descripción

Sistema interactivo de reconocimiento de objetos y gestos utilizando Kinect Xbox 360 sobre una mesa-pantalla (televisor horizontal). El sistema detecta objetos en tiempo real, muestra sus siluetas y características, y permite interacción mediante gestos manuales.

## ✨ Características Principales

- 🎯 **Detección de objetos en tiempo real** con YOLO
- 👋 **Reconocimiento de gestos manuales** con MediaPipe
- 📊 **Visualización de características** de objetos detectados
- 🖥️ **Interfaz visual interactiva** en mesa-pantalla
- 🔄 **Procesamiento 3D** con datos de profundidad del Kinect
- ⚡ **Rendimiento optimizado** (30+ FPS)

## 🛠️ Requerimientos

### Hardware
- Kinect para Xbox 360 (modelo 1414 o 1473)
- Adaptador de corriente y USB para Kinect
- Televisor/Monitor 40-55" (montado horizontalmente)
- PC con:
  - CPU: Intel i5 6ta gen o AMD Ryzen 5+
  - RAM: 8GB mínimo (16GB recomendado)
  - GPU: NVIDIA GTX 1050+ (opcional pero recomendado)
  - USB 3.0

### Software
- Ubuntu 20.04+ (recomendado Ubuntu 22.04 LTS o superior)
- Python 3.8 - 3.11
- libfreenect (driver para Kinect Xbox 360)
- CUDA Toolkit (opcional, para aceleración GPU con NVIDIA)

## 🚀 Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/kinect_table_system.git
cd kinect_table_system
```

### 2. Crear entorno virtual
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Instalar drivers del Kinect (Ubuntu)

```bash
# Actualizar repositorios
sudo apt-get update

# Instalar libfreenect y dependencias
sudo apt-get install -y libfreenect-dev freenect libusb-1.0-0-dev

# Agregar usuario al grupo plugdev para acceso al Kinect sin sudo
sudo usermod -a -G plugdev $USER

# Crear reglas udev para el Kinect (permite acceso sin root)
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

# IMPORTANTE: Cerrar sesión y volver a iniciar para aplicar cambios de grupo
```

**Verificar instalación:**
```bash
# Probar que el Kinect sea detectado
freenect-glview
```

### 5. Descargar modelos pre-entrenados
```bash
python scripts/download_models.py
```

## 📖 Uso Básico

### Ejecutar el sistema completo
```bash
python main.py
```

### Ejecutar solo captura del Kinect (prueba)
```bash
python modules/kinect_capture.py
```

### Ejecutar calibración
```bash
python scripts/calibrate.py
```

### Ejecutar modo demo
```bash
python main.py --demo
```

## 📁 Estructura del Proyecto

```
kinect_table_system/
├── main.py                      # Punto de entrada principal
├── config.py                    # Configuración global
├── requirements.txt             # Dependencias Python
├── README.md                    # Este archivo
│
├── modules/                     # Módulos principales
│   ├── kinect_capture.py       # Captura de datos del Kinect
│   ├── preprocessing.py        # Preprocesamiento de imágenes
│   ├── calibration.py          # Calibración de cámaras
│   ├── segmentation.py         # Segmentación de objetos
│   ├── object_detection.py     # Detección con YOLO
│   ├── feature_extraction.py   # Extracción de características
│   ├── gesture_recognition.py  # Reconocimiento de gestos
│   ├── hand_tracking.py        # Tracking de manos
│   └── visualization.py        # Renderizado e interfaz
│
├── models/                      # Modelos de ML
│   └── README.md               # Instrucciones de modelos
│
├── data/                        # Datos del sistema
│   ├── calibration/            # Datos de calibración
│   ├── objects_db/             # Base de datos de objetos
│   └── templates/              # Templates de gestos
│
├── utils/                       # Utilidades
│   ├── geometry.py             # Funciones geométricas
│   ├── image_processing.py     # Procesamiento de imágenes
│   └── logger.py               # Sistema de logging
│
├── tests/                       # Tests unitarios
│   ├── test_capture.py
│   ├── test_detection.py
│   └── test_gestures.py
│
├── scripts/                     # Scripts auxiliares
│   ├── download_models.py      # Descargar modelos
│   ├── calibrate.py            # Script de calibración
│   └── benchmark.py            # Pruebas de rendimiento
│
└── docs/                        # Documentación adicional
    ├── INSTALLATION.md         # Guía de instalación detallada
    ├── API.md                  # Documentación de API
    └── TROUBLESHOOTING.md      # Solución de problemas
```

## 🎮 Gestos Soportados

| Gesto | Acción |
|-------|--------|
| ✋ Mano abierta | Seleccionar objeto |
| ✊ Puño cerrado | Mover objeto |
| 👍 Pulgar arriba | Zoom in |
| 👎 Pulgar abajo | Zoom out |
| 🤏 Pellizco | Rotar objeto |
| 👋 Deslizar | Navegar menú |

## 🔧 Configuración

El archivo `config.py` contiene todas las configuraciones del sistema:

```python
# Ejemplo de configuración
KINECT_RESOLUTION = (1920, 1080)
DEPTH_RESOLUTION = (512, 424)
FPS_TARGET = 30
DETECTION_CONFIDENCE = 0.5
```

## 📊 Estado del Proyecto

### Fase Actual: ✅ Fase 1 - Configuración Base

- [x] Estructura del repositorio
- [x] Configuración de dependencias
- [ ] Captura básica de Kinect
- [ ] Visualización de streams RGB y profundidad

### Próximas Fases:
- [ ] Fase 2: Preprocesamiento y Segmentación
- [ ] Fase 3: Reconocimiento de Objetos
- [ ] Fase 4: Reconocimiento de Gestos
- [ ] Fase 5: Interfaz Visual Avanzada
- [ ] Fase 6: Integración y Mejoras
- [ ] Fase 7: Pruebas y Refinamiento

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## 👥 Autores

- Tu Nombre - Desarrollo inicial

## 🙏 Agradecimientos

- OpenKinect por libfreenect
- Ultralytics por YOLOv5/v8
- Google por MediaPipe
- Comunidad de OpenCV

## 📧 Contacto

- Email: tu-email@ejemplo.com
- GitHub: [@tu-usuario](https://github.com/tu-usuario)
- LinkedIn: [Tu Perfil](https://linkedin.com/in/tu-perfil)

## 🔗 Enlaces Útiles

- [OpenKinect (libfreenect)](https://openkinect.org/)
- [libfreenect GitHub](https://github.com/OpenKinect/libfreenect)
- [OpenCV Documentation](https://docs.opencv.org/)
- [MediaPipe Hands](https://google.github.io/mediapipe/solutions/hands.html)
- [YOLOv8 Ultralytics](https://github.com/ultralytics/ultralytics)

---

⭐ Si este proyecto te resulta útil, considera darle una estrella en GitHub
