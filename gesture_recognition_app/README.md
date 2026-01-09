# 🤖 Hand Gesture Recognition App

Aplicación moderna de reconocimiento de gestos de manos usando **MediaPipe**, **Tauri**, y **React** con interfaz futurista.

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![Tauri](https://img.shields.io/badge/tauri-1.5-orange)
![React](https://img.shields.io/badge/react-18.2-cyan)

## ✨ Características

- 🎯 **Reconocimiento en Tiempo Real** - Detección de hasta 2 manos simultáneas
- 👋 **8 Gestos Básicos** - Mano abierta, puño, thumbs up/down, paz, OK, señalar, pellizco
- 🖥️ **Interfaz Moderna** - Diseño futurista con animaciones fluidas (Framer Motion)
- ⚡ **Alto Rendimiento** - 30+ FPS con procesamiento optimizado
- 🔌 **Arquitectura Desacoplada** - Backend Python + Frontend Tauri/React
- 🌐 **Comunicación WebSocket** - Stream de video y datos en tiempo real

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────┐
│         TAURI APP (React)               │
│   ┌─────────────────────────────────┐   │
│   │   Video Stream Display          │   │
│   │   Gesture Information           │   │
│   │   Hand Position Tracking        │   │
│   └─────────────────────────────────┘   │
└──────────────┬──────────────────────────┘
               │ WebSocket (ws://localhost:8765)
               │
┌──────────────▼──────────────────────────┐
│    PYTHON BACKEND (WebSocket Server)    │
│   ┌─────────────────────────────────┐   │
│   │   MediaPipe Hand Tracking       │   │
│   │   Gesture Recognition Engine    │   │
│   │   OpenCV Video Processing       │   │
│   └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## 📋 Requisitos Previos

### Software
- **Python 3.8+** con pip
- **Node.js 16+** con npm
- **Rust** (para compilar Tauri)
- **Cámara web** funcional

### Sistema Operativo
- Windows 10/11
- macOS 10.15+
- Linux (Ubuntu 20.04+)

## 🚀 Instalación

### 1. Instalar Dependencias de Python

```bash
# Desde el directorio raíz del proyecto
cd kinect_table_system

# Crear entorno virtual (recomendado)
python -m venv venv

# Activar entorno
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias específicas
pip install opencv-python mediapipe websockets numpy
```

### 2. Instalar Rust (si no lo tienes)

```bash
# Linux/Mac
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Windows: Descargar de https://rustup.rs/
```

### 3. Instalar Dependencias de Node.js

```bash
cd gesture_recognition_app
npm install
```

## 🎮 Uso

### Opción 1: Modo Desarrollo (Recomendado para Testing)

Necesitas **2 terminales**:

**Terminal 1 - Backend Python:**
```bash
cd kinect_table_system/gesture_recognition_app/python_backend
python websocket_server.py
```

Deberías ver:
```
============================================================
HAND TRACKING WEBSOCKET SERVER
============================================================
Servidor: ws://localhost:8765
Presiona Ctrl+C para detener
============================================================
```

**Terminal 2 - Frontend Tauri:**
```bash
cd kinect_table_system/gesture_recognition_app
npm run tauri:dev
```

La aplicación se abrirá automáticamente.

### Opción 2: Modo Producción

```bash
# Construir la aplicación
cd gesture_recognition_app
npm run tauri:build

# El ejecutable estará en src-tauri/target/release/
```

⚠️ **Nota**: El backend Python debe ejecutarse por separado.

## 🎨 Interfaz de Usuario

### Pantalla Principal

```
┌─────────────────────────────────────────────────────────┐
│  🤖 HAND GESTURE RECOGNITION    [●] Conectado | 30 FPS  │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────┐  ┌────────────────────┐       │
│  │                     │  │  Gestos Detectados  │       │
│  │   Video Feed        │  │                     │       │
│  │   (Cámara en vivo)  │  │  👈 Mano Izquierda │       │
│  │                     │  │     ✌️ Paz          │       │
│  │  [2 Manos]          │  │     95% confianza   │       │
│  │                     │  │                     │       │
│  └─────────────────────┘  │  👉 Mano Derecha   │       │
│                            │     👍 Pulgar Arriba│       │
│                            │     98% confianza   │       │
│                            └────────────────────┘       │
│                                                           │
│  Gestos Disponibles:                                     │
│  🖐️ Abierta  ✊ Puño  👍 Arriba  👎 Abajo               │
│  ✌️ Paz  👌 OK  ☝️ Señalar  🤏 Pellizco                │
└─────────────────────────────────────────────────────────┘
```

### Gestos Reconocidos

| Gesto | Emoji | Descripción |
|-------|-------|-------------|
| Mano Abierta | 🖐️ | Todos los dedos extendidos |
| Puño Cerrado | ✊ | Todos los dedos cerrados |
| Pulgar Arriba | 👍 | Solo pulgar hacia arriba |
| Pulgar Abajo | 👎 | Solo pulgar hacia abajo |
| Señal de Paz | ✌️ | Índice y medio extendidos |
| Señal OK | 👌 | Pulgar e índice formando círculo |
| Señalando | ☝️ | Solo índice extendido |
| Pellizco | 🤏 | Pulgar e índice muy cercanos |

## 🔧 Configuración

### Backend Python

Edita `websocket_server.py`:

```python
# Cambiar puerto del servidor
server = HandTrackingServer(host="localhost", port=8765)

# Ajustar calidad de video
encoded_frame = self._encode_frame(annotated_frame, quality=75)  # 0-100

# Cambiar FPS objetivo
await asyncio.sleep(0.033)  # 0.033 = ~30 FPS, 0.016 = ~60 FPS
```

### Frontend React

Edita `src/App.jsx`:

```javascript
// Cambiar URL del WebSocket
const WEBSOCKET_URL = 'ws://localhost:8765';
```

### MediaPipe Settings

Edita `modules/hand_tracking.py`:

```python
tracker = HandTracker(
    max_num_hands=2,                    # Número de manos
    min_detection_confidence=0.7,       # Confianza de detección
    min_tracking_confidence=0.5,        # Confianza de tracking
    model_complexity=1                  # 0=lite, 1=full
)
```

## 📊 Rendimiento

### Benchmarks Típicos

| Hardware | FPS | Latencia |
|----------|-----|----------|
| RTX 3060 + i7 | 60+ | <50ms |
| GTX 1050 + i5 | 30-40 | <100ms |
| CPU Only (i5) | 15-20 | <150ms |

### Optimización

**Para mejorar FPS:**
1. Reducir resolución de video en `websocket_server.py`
2. Usar `model_complexity=0` (lite)
3. Reducir calidad de codificación JPEG
4. Detectar solo 1 mano en lugar de 2

**Para reducir latencia:**
1. Usar WebSocket en red local
2. Reducir `SMOOTHING_WINDOW` en `hand_tracking.py`
3. Aumentar `min_tracking_confidence`

## 🐛 Troubleshooting

### Error: "No module named 'mediapipe'"
```bash
pip install mediapipe
```

### Error: "Camera not detected"
```bash
# Linux: Verificar permisos
sudo usermod -a -G video $USER

# Verificar cámaras disponibles
python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
```

### Error: "WebSocket connection failed"
1. Verificar que el servidor Python esté corriendo
2. Verificar que el puerto 8765 no esté en uso
3. Verificar firewall

### Error: "Rust/Cargo not found"
```bash
# Instalar Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

### La aplicación no detecta gestos
1. Asegúrate de tener buena iluminación
2. Mantén las manos dentro del cuadro de la cámara
3. Verifica que MediaPipe esté instalado correctamente
4. Reduce `min_detection_confidence` en el config

## 📁 Estructura de Archivos

```
gesture_recognition_app/
├── python_backend/
│   └── websocket_server.py      # Servidor WebSocket
├── src/
│   ├── App.jsx                  # Componente principal React
│   ├── App.css                  # Estilos principales
│   ├── main.jsx                 # Entry point React
│   └── index.css                # Estilos base
├── src-tauri/
│   ├── src/
│   │   └── main.rs              # Backend Rust/Tauri
│   ├── Cargo.toml               # Dependencias Rust
│   ├── tauri.conf.json          # Config Tauri
│   └── build.rs                 # Build script
├── index.html                   # HTML base
├── package.json                 # Dependencias npm
└── vite.config.js               # Config Vite
```

## 🔮 Próximas Mejoras

- [ ] Grabación de sesiones
- [ ] Gestos personalizados
- [ ] Múltiples cámaras
- [ ] Integración con Kinect
- [ ] Machine Learning para gestos custom
- [ ] Exportación de datos
- [ ] Control de sistema por gestos
- [ ] Soporte multi-idioma

## 🤝 Contribuir

Este es parte del proyecto Kinect Table System. Ver [CONTRIBUTING.md](../CONTRIBUTING.md) para guías de contribución.

## 📝 Licencia

MIT License - Ver [LICENSE](../LICENSE)

## 🙏 Agradecimientos

- **MediaPipe** - Google's ML framework
- **Tauri** - Cross-platform app framework
- **OpenCV** - Computer vision library
- **React** - UI framework
- **Framer Motion** - Animation library

---

**Desarrollado con ❤️ para Kinect Table System**
