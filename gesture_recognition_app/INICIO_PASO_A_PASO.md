# 🚀 GUÍA PASO A PASO - Ejecutar la App

## ✅ Pre-requisitos

Antes de empezar, asegúrate de tener:
- ✅ Python 3.11 instalado
- ✅ Node.js 16+ instalado
- ✅ Rust instalado (para Tauri)
- ✅ Dependencias de Python instaladas

---

## 📋 Paso 1: Verificar Instalación

```bash
cd gesture_recognition_app
python verificar_instalacion.py
```

**Esperado:**
```
✅ Todas las dependencias están instaladas
✅ Todos los archivos están presentes
✅ Sistema listo para usar
```

Si ves errores, sigue las instrucciones que te da el script.

---

## 📋 Paso 2: Instalar Dependencias de Node (Solo Primera Vez)

```bash
cd gesture_recognition_app
npm install
```

Esto tardará unos minutos. Esperado:
```
added 234 packages, and audited 235 packages in 2m
```

---

## 📋 Paso 3: Iniciar Backend Python

Abre una terminal y ejecuta:

```bash
cd gesture_recognition_app/python_backend
python websocket_server.py
```

**✅ Si funciona, verás:**
```
============================================================
HAND TRACKING WEBSOCKET SERVER
============================================================
Servidor: ws://localhost:8765
Presiona Ctrl+C para detener
============================================================

INFO:root:Iniciando servidor en ws://localhost:8765
INFO:root:Iniciando cámara 0...
INFO:root:Cámara iniciada exitosamente
```

**❌ Si ves "ModuleNotFoundError":**
- Verifica que el archivo `hand_tracking.py` esté en la carpeta `gesture_recognition_app/`
- Verifica que los imports en `websocket_server.py` estén corregidos (ver SOLUCION_IMPORTS.md)

**⚠️ Si ves "Camera not detected":**
- Verifica que tu cámara esté conectada
- Cierra otras apps que usen la cámara (Zoom, Skype, etc.)

---

## 📋 Paso 4: Iniciar Frontend Tauri

**IMPORTANTE:** No cierres la terminal anterior. Abre una **NUEVA** terminal.

```bash
cd gesture_recognition_app
npm run tauri:dev
```

**La primera vez tardará 2-5 minutos** compilando Rust:
```
   Compiling tauri v1.5...
   Compiling hand-gesture-recognition v0.1.0
    Finished dev [unoptimized + debuginfo] target(s) in 3m 24s
```

Luego se abrirá automáticamente la ventana de la aplicación.

---

## ✅ Paso 5: ¡Usar la App!

Si todo funcionó:

1. Deberías ver una ventana con la interfaz futurista
2. Indicador "Conectado" en verde
3. Video de tu cámara en vivo
4. Muestra tus manos frente a la cámara
5. Los gestos aparecerán en el panel derecho

**Gestos disponibles:**
- 🖐️ Mano abierta - Todos los dedos extendidos
- ✊ Puño - Todos cerrados
- 👍 Pulgar arriba
- 👎 Pulgar abajo
- ✌️ Paz - Índice y medio en V
- 👌 OK - Círculo con pulgar e índice
- ☝️ Señalando - Solo índice
- 🤏 Pellizco - Pulgar e índice juntos

---

## 🛑 Para Detener

1. En la ventana de la app: Cierra la ventana
2. En Terminal 2 (Tauri): Ctrl+C
3. En Terminal 1 (Python): Ctrl+C

---

## 🔧 Problemas Comunes

### "Cannot find module 'tauri'"
```bash
npm install
```

### "Rust not found"
```bash
# Windows: Descargar de https://rustup.rs/
# Linux/Mac:
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

### "WebSocket connection failed"
1. Verifica que Terminal 1 (Python) esté corriendo
2. Verifica que veas "Servidor: ws://localhost:8765"
3. Verifica que no haya errores en Terminal 1

### La app se abre pero no muestra video
1. Verifica que Terminal 1 muestre "Cámara iniciada exitosamente"
2. Verifica que el indicador en la app esté en "Conectado" (verde)
3. Recarga la app (Ctrl+R en la ventana)

### Los gestos no se detectan
1. Mejora la iluminación
2. Acerca más las manos a la cámara
3. Asegúrate de hacer los gestos claramente

---

## 📱 Usar Script Automático (Alternativa)

En lugar de abrir dos terminales manualmente, puedes usar:

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

Esto abrirá ambas terminales automáticamente.

---

## 🎯 Resumen Visual

```
┌─────────────────────────────────────────┐
│  Terminal 1: Python Backend             │
│  > python websocket_server.py           │
│  ✓ Servidor corriendo                   │
│  ✓ Cámara iniciada                      │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  Terminal 2: Tauri Frontend             │
│  > npm run tauri:dev                    │
│  ⏳ Compilando (primera vez 2-5 min)    │
│  ✓ App abierta                          │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  Ventana de la App                      │
│  ✓ Conectado (verde)                    │
│  ✓ Video en vivo                        │
│  ✓ Gestos detectados                    │
└─────────────────────────────────────────┘
```

---

**¿Necesitas ayuda?** Revisa `SOLUCION_IMPORTS.md` o el README.md completo.
