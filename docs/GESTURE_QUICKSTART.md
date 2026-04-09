# 🤚 Reconocimiento de Gestos - Guía de Inicio Rápido

## 📋 Opciones Disponibles

Tienes **3 formas** de usar el sistema de reconocimiento de gestos:

### 1️⃣ Demo Standalone (Más Rápido)
Solo Python + OpenCV - Sin necesidad de Tauri

### 2️⃣ Servidor API + Cliente Web
Python backend + cualquier frontend

### 3️⃣ Aplicación Tauri Completa (Recomendado)
Aplicación de escritorio moderna con React

---

## 🚀 Opción 1: Demo Standalone

### Instalación
```bash
# Instalar dependencias
pip install opencv-python mediapipe numpy

# Ejecutar demo
python examples/gesture_demo.py
```

### Características
- ✅ Visualización en tiempo real
- ✅ Reconocimiento de 8 gestos
- ✅ Detección de hasta 2 manos simultáneas
- ✅ FPS en pantalla
- ✅ No requiere instalación adicional

### Controles
- `q` o `ESC` - Salir

---

## 🌐 Opción 2: Servidor API

### Paso 1: Instalar dependencias
```bash
pip install opencv-python mediapipe numpy websockets aiohttp
```

### Paso 2: Iniciar servidor
```bash
python examples/start_api_server.py
```

El servidor estará disponible en:
- **WebSocket**: `ws://localhost:8765`
- **REST API**: `http://localhost:8000`

### Paso 3: Conectar cliente

#### Desde JavaScript:
```javascript
const socket = new WebSocket('ws://localhost:8765');

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Gestos:', data.gestures);
};
```

#### Endpoints REST:
```bash
# Obtener gesto actual
curl http://localhost:8000/gesture

# Obtener estadísticas
curl http://localhost:8000/stats
```

---

## 💻 Opción 3: Aplicación Tauri Completa

### Requisitos Previos
1. **Python 3.8+** con dependencias instaladas
2. **Node.js 18+**
3. **Rust** (última versión estable)

### Instalación Rust (Ubuntu)
```bash
# Instalar Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Recargar el shell
source $HOME/.cargo/env

# Verificar instalación
rustc --version
```

### Paso 1: Iniciar Backend Python
```bash
# Terminal 1
python examples/start_api_server.py
```

### Paso 2: Iniciar Aplicación Tauri
```bash
# Terminal 2
cd tauri-app
npm install
npm run tauri dev
```

### Características de la App Tauri
- Interfaz moderna con React
- Visualización en tiempo real de landmarks
- Panel de estadísticas
- Conexión WebSocket automática
- Modo oscuro/claro
- Optimizado para Ubuntu/Linux

---

## 🎯 Gestos Soportados

| Gesto | Descripción | Color |
|-------|-------------|-------|
| 🖐️ Mano Abierta | Todos los dedos extendidos | Verde |
| ✊ Puño Cerrado | Todos los dedos cerrados | Rojo |
| 👍 Pulgar Arriba | Solo pulgar extendido | Amarillo |
| 👎 Pulgar Abajo | Pulgar hacia abajo | Magenta |
| 🤏 Pellizco | Pulgar e índice juntos | Naranja |
| ✌️ Victoria | Índice y medio extendidos | Púrpura |
| 👌 OK | Pulgar e índice formando círculo | Cian |
| 👉 Señalando | Solo índice extendido | Rosa |

---

## 🔧 Configuración

### Cambiar Resolución
Edita `modules/gesture_recognition.py`:
```python
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)   # Cambiar aquí
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)  # Y aquí
```

### Ajustar Confianza
```python
recognizer = GestureRecognizer(
    max_num_hands=2,
    min_detection_confidence=0.7,  # Cambiar (0.0 - 1.0)
    min_tracking_confidence=0.5    # Cambiar (0.0 - 1.0)
)
```

### Cambiar Puerto del Servidor
Edita `modules/gesture_api_server.py`:
```python
server = GestureAPIServer(
    host="localhost",
    ws_port=8765,    # Puerto WebSocket
    http_port=8000   # Puerto HTTP
)
```

---

## 🐛 Solución de Problemas

### Error: "No se pudo abrir la cámara"
**Solución**:
1. Verifica que la cámara esté conectada
2. Cierra otras aplicaciones que usen la cámara
3. Prueba cambiar el índice de cámara:
   ```python
   cap = cv2.VideoCapture(1)  # Cambiar 0 por 1, 2, etc.
   ```

### Error: "ImportError: No module named 'mediapipe'"
**Solución**:
```bash
pip install mediapipe
```

### Error: WebSocket no conecta
**Solución**:
1. Verifica que el servidor Python esté corriendo
2. Verifica el puerto (8765)
3. Revisa el firewall

### Bajo FPS
**Solución**:
1. Reducir resolución de cámara
2. Reducir `max_num_hands` a 1
3. Bajar `min_detection_confidence` a 0.5

---

## 📊 Arquitectura del Sistema

```
┌─────────────────────────────────────────────┐
│           Python Backend                    │
│  ┌────────────────────────────────────┐    │
│  │  Camera Input (OpenCV)              │    │
│  └──────────────┬──────────────────────┘    │
│                 │                            │
│  ┌──────────────▼──────────────────────┐    │
│  │  MediaPipe Hands (ML Detection)     │    │
│  └──────────────┬──────────────────────┘    │
│                 │                            │
│  ┌──────────────▼──────────────────────┐    │
│  │  Gesture Recognition Logic          │    │
│  └──────────────┬──────────────────────┘    │
│                 │                            │
│  ┌──────────────▼──────────────────────┐    │
│  │  WebSocket Server (Port 8765)       │    │
│  │  REST API (Port 8000)               │    │
│  └──────────────┬──────────────────────┘    │
└─────────────────┼───────────────────────────┘
                  │
    WebSocket Connection (Real-time)
                  │
┌─────────────────▼───────────────────────────┐
│           Tauri Frontend                    │
│  ┌────────────────────────────────────┐    │
│  │  React UI (TypeScript)              │    │
│  │  - HandTracker Component            │    │
│  │  - StatsPanel Component             │    │
│  │  - WebSocket Hook                   │    │
│  └────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

---

## 🚀 Siguientes Pasos

1. **Prueba el demo standalone** para verificar que todo funciona
2. **Experimenta con el servidor API** para entender la integración
3. **Construye la app Tauri** para una experiencia completa
4. **Personaliza los gestos** agregando tus propios patrones
5. **Integra con Kinect** para detección 3D (próxima fase)

---

## 📚 Recursos Adicionales

- [MediaPipe Hands Docs](https://google.github.io/mediapipe/solutions/hands.html)
- [Tauri Documentation](https://tauri.app/v1/guides/)
- [OpenCV Python Tutorial](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)

---

## 🤝 Contribuir

¿Encontraste un bug o quieres agregar un nuevo gesto? Ver [CONTRIBUTING.md](../CONTRIBUTING.md)

---

**¡Listo para comenzar!** 🎉

Comienza con: `python examples/gesture_demo.py`
