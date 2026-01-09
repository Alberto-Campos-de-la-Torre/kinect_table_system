# Kinect Table System - Aplicación Tauri

Aplicación de escritorio moderna para el sistema de reconocimiento de gestos construida con:
- **Frontend**: React + TypeScript + Vite
- **Backend**: Tauri (Rust)
- **Integración**: WebSocket con servidor Python

## 🚀 Inicio Rápido

### Prerrequisitos

1. **Node.js** (v18 o superior)
2. **Rust** (última versión estable)
3. **Tauri CLI**

```bash
# Instalar Tauri CLI
cargo install tauri-cli

# O con npm
npm install -g @tauri-apps/cli
```

### Instalación

```bash
# 1. Instalar dependencias
cd tauri-app
npm install

# 2. Desarrollo
npm run tauri dev

# 3. Build producción
npm run tauri build
```

## 📁 Estructura del Proyecto

```
tauri-app/
├── src/                    # Frontend React
│   ├── App.tsx            # Componente principal
│   ├── components/        # Componentes React
│   │   ├── GestureView.tsx
│   │   ├── HandTracker.tsx
│   │   └── StatsPanel.tsx
│   ├── hooks/             # Custom hooks
│   │   └── useGestureWebSocket.ts
│   ├── types/             # TypeScript types
│   │   └── gesture.types.ts
│   └── styles/            # CSS/SCSS
│
├── src-tauri/             # Backend Tauri (Rust)
│   ├── src/
│   │   └── main.rs       # Código Rust
│   ├── tauri.conf.json   # Configuración Tauri
│   └── Cargo.toml        # Dependencias Rust
│
├── package.json
└── README.md
```

## 🔌 Conexión con Backend Python

La aplicación se conecta al servidor Python mediante WebSocket:

```typescript
// URL del servidor Python
const WS_URL = 'ws://localhost:8765';

// Conexión WebSocket
const socket = new WebSocket(WS_URL);
```

## 🎨 Características

- ✅ Visualización en tiempo real de detección de manos
- ✅ Reconocimiento de 8 gestos diferentes
- ✅ Panel de estadísticas
- ✅ Interfaz moderna y responsiva
- ✅ Modo oscuro/claro
- ✅ Alta performance (60 FPS UI)

## 📦 Scripts Disponibles

```bash
npm run dev          # Desarrollo con hot reload
npm run build        # Build del frontend
npm run tauri dev    # Desarrollo completo (frontend + Tauri)
npm run tauri build  # Build producción
```

## 🔧 Configuración

### Tauri Configuration

Edita `src-tauri/tauri.conf.json` para cambiar:
- Nombre de la aplicación
- Tamaño de ventana
- Permisos
- Iconos

### WebSocket URL

Cambia la URL en `src/hooks/useGestureWebSocket.ts`:

```typescript
const WS_URL = process.env.VITE_WS_URL || 'ws://localhost:8765';
```

## 🚀 Despliegue

### Windows
```bash
npm run tauri build
# Instalador en: src-tauri/target/release/bundle/
```

### macOS
```bash
npm run tauri build
# .app y .dmg en: src-tauri/target/release/bundle/
```

### Linux
```bash
npm run tauri build
# .deb, .AppImage en: src-tauri/target/release/bundle/
```

## 🐛 Troubleshooting

### Error de conexión WebSocket
1. Verificar que el servidor Python esté corriendo
2. Verificar puerto (8765)
3. Verificar firewall

### Error al compilar Tauri
1. Actualizar Rust: `rustup update`
2. Instalar dependencias del sistema (Linux):
   ```bash
   sudo apt install libwebkit2gtk-4.0-dev \
     build-essential \
     curl \
     wget \
     file \
     libssl-dev \
     libgtk-3-dev \
     libayatana-appindicator3-dev \
     librsvg2-dev
   ```

## 📚 Documentación

- [Tauri Docs](https://tauri.app/)
- [React Docs](https://react.dev/)
- [Vite Docs](https://vitejs.dev/)

## 🤝 Contribuir

Ver [CONTRIBUTING.md](../CONTRIBUTING.md) en la raíz del proyecto.

## 📄 Licencia

MIT - Ver [LICENSE](../LICENSE)
