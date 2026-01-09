/**
 * Aplicación Principal - Kinect Table System
 */

import React from 'react';
import { HandTracker } from './components/HandTracker';
import { StatsPanel } from './components/StatsPanel';
import { useGestureWebSocket } from './hooks/useGestureWebSocket';
import { Hand, RefreshCw, Settings } from 'lucide-react';
import './styles/App.css';

function App() {
  const { gestures, fps, connectionStatus, reconnect } = useGestureWebSocket();
  const [showSettings, setShowSettings] = React.useState(false);

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="logo-section">
            <Hand className="logo-icon" />
            <h1 className="app-title">Kinect Table System</h1>
            <span className="version-badge">v0.1.0</span>
          </div>
          
          <div className="header-actions">
            <button
              onClick={reconnect}
              className="icon-button"
              title="Reconectar"
              disabled={connectionStatus.connected}
            >
              <RefreshCw className={`w-5 h-5 ${connectionStatus.connected ? '' : 'animate-spin'}`} />
            </button>
            
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="icon-button"
              title="Configuración"
            >
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {/* Vista principal de tracking */}
        <div className="tracking-view">
          <HandTracker gestures={gestures} />
        </div>

        {/* Panel lateral de estadísticas */}
        <aside className="stats-sidebar">
          <StatsPanel
            fps={fps}
            connectionStatus={connectionStatus}
            gestureCount={gestures.length}
          />
        </aside>
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <div className="footer-content">
          <p className="footer-text">
            Detección de gestos en tiempo real con MediaPipe
          </p>
          <div className="footer-links">
            <a href="#" className="footer-link">Documentación</a>
            <span className="separator">•</span>
            <a href="#" className="footer-link">GitHub</a>
            <span className="separator">•</span>
            <a href="#" className="footer-link">Ayuda</a>
          </div>
        </div>
      </footer>

      {/* Modal de configuración */}
      {showSettings && (
        <div className="modal-overlay" onClick={() => setShowSettings(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Configuración</h2>
            
            <div className="settings-section">
              <h3 className="settings-subtitle">Conexión</h3>
              <div className="setting-item">
                <label className="setting-label">URL del servidor</label>
                <input
                  type="text"
                  className="setting-input"
                  value="ws://localhost:8765"
                  readOnly
                />
              </div>
              <div className="setting-item">
                <label className="setting-label">Estado</label>
                <div className="flex items-center gap-2">
                  <div className={`status-indicator ${connectionStatus.connected ? 'connected' : 'disconnected'}`} />
                  <span className="text-white">
                    {connectionStatus.connected ? 'Conectado' : 'Desconectado'}
                  </span>
                </div>
              </div>
            </div>

            <div className="settings-section">
              <h3 className="settings-subtitle">Visualización</h3>
              <div className="setting-item">
                <label className="setting-label">Mostrar FPS</label>
                <input type="checkbox" defaultChecked className="setting-checkbox" />
              </div>
              <div className="setting-item">
                <label className="setting-label">Mostrar landmarks</label>
                <input type="checkbox" defaultChecked className="setting-checkbox" />
              </div>
            </div>

            <div className="modal-actions">
              <button
                onClick={() => setShowSettings(false)}
                className="button-primary"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
