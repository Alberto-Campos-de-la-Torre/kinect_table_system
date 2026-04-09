# 🚀 GUÍA DE INICIO RÁPIDO - Hand Gesture Recognition

## ⚡ Inicio en 3 Pasos

### 1️⃣ Instalar Dependencias Python (5 minutos)

```bash
cd gesture_recognition_app/python_backend
pip install -r requirements.txt
```

### 2️⃣ Instalar Dependencias Node.js (10 minutos)

```bash
cd gesture_recognition_app
npm install
```

### 3️⃣ Ejecutar la Aplicación

#### Automático:
```bash
./start.sh
```

#### Manual (2 terminales):

**Terminal 1:**
```bash
cd python_backend
python websocket_server.py
```

**Terminal 2:**
```bash
npm run tauri:dev
```

---

## 🧪 Probar Solo el Tracking (Sin Tauri)

Si quieres probar solo el reconocimiento de gestos sin instalar Tauri:

```bash
cd python_backend
python test_hand_tracking.py
```

Esto abrirá una ventana con OpenCV mostrando el tracking en tiempo real.

---

## ✅ Verificar Instalación

### Python:
```bash
python -c "import cv2, mediapipe; print('✅ OK')"
```

### Node.js:
```bash
node --version
npm --version
```

### Rust (para Tauri):
```bash
rustc --version
cargo --version
```

Si Rust no está instalado:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

---

## 🎯 ¿Qué Hace Cada Archivo?

```
gesture_recognition_app/
│
├── python_backend/
│   ├── websocket_server.py          ⭐ Servidor principal
│   ├── test_hand_tracking.py        🧪 Test standalone
│   └── requirements.txt             📦 Dependencias Python
│
├── src/
│   ├── App.jsx                      🎨 Interfaz React
│   ├── App.css                      💅 Estilos
│   └── main.jsx                     🚀 Entry point
│
├── src-tauri/
│   ├── src/main.rs                  🦀 Backend Rust
│   └── tauri.conf.json              ⚙️ Configuración Tauri
│
├── hand_tracking.py                 🤖 Motor de reconocimiento
├── package.json                     📦 Dependencias npm
├── start.bat / start.sh             🎮 Inicio rápido
└── README.md                        📖 Documentación completa
```

---

## 🐛 Problemas Comunes

### "No se pudo abrir la cámara"
- Verifica que ninguna app esté usando la cámara
- En Linux: `sudo usermod -a -G video $USER`

### "WebSocket connection failed"
- Asegúrate de iniciar el servidor Python primero
- Verifica que el puerto 8765 esté libre

### "Rust not found"
- Instala Rust: https://rustup.rs/

### Gestos no se detectan
- Mejora la iluminación
- Acerca más las manos a la cámara
- Reduce `min_detection_confidence` en hand_tracking.py

---

## 📊 Rendimiento Esperado

- **Con GPU**: 60+ FPS
- **Solo CPU**: 20-30 FPS
- **Latencia**: <100ms

---

## 🎮 Gestos Disponibles

| Gesto | Cómo hacerlo |
|-------|--------------|
| 🖐️ Mano Abierta | Todos los dedos extendidos |
| ✊ Puño | Todos los dedos cerrados |
| 👍 Pulgar Arriba | Solo pulgar hacia arriba |
| 👎 Pulgar Abajo | Solo pulgar hacia abajo |
| ✌️ Paz | Índice y medio en V |
| 👌 OK | Pulgar e índice formando círculo |
| ☝️ Señalar | Solo índice extendido |
| 🤏 Pellizco | Pulgar e índice muy cerca |

---

## 📞 Ayuda

Ver README.md completo para:
- Documentación detallada
- Configuración avanzada
- Troubleshooting extendido
- Arquitectura del sistema

---

**¡Listo! Ahora muestra tus manos frente a la cámara** 👋
