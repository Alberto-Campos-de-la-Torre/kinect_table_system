import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './App.css';
import PointCloudViewer from './PointCloudViewer';

const WEBSOCKET_URL = 'ws://localhost:8765';

function App() {
  // Estado de conexión
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);
  
  // Datos del sistema
  const [fps, setFps] = useState(0);
  const [frameRgb, setFrameRgb] = useState(null);
  const [frameDepth, setFrameDepth] = useState(null);
  const [pointcloudData, setPointcloudData] = useState(null);
  
  // Detecciones
  const [objects, setObjects] = useState([]);
  const [hands, setHands] = useState([]);
  
  // Configuración
  const [config, setConfig] = useState({
    depthEnabled: true,
    objectsEnabled: true,
    gesturesEnabled: true,
    pointcloudEnabled: true,
    pointcloudColorMode: 'rgb'
  });
  
  // Estadísticas
  const [stats, setStats] = useState({
    frames_processed: 0,
    objects_detected: 0,
    hands_detected: 0
  });
  
  // Modo de visualización
  const [viewMode, setViewMode] = useState('rgb'); // 'rgb', 'depth', 'split', '3d'
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  const connectWebSocket = () => {
    try {
      const ws = new WebSocket(WEBSOCKET_URL);
      
      ws.onopen = () => {
        console.log('Conectado al Kinect Table System');
        setConnected(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'frame') {
            // Actualizar frames
            if (data.rgb) setFrameRgb(data.rgb);
            if (data.depth) setFrameDepth(data.depth);
            
            // Actualizar nube de puntos
            if (data.pointcloud) setPointcloudData(data.pointcloud);
            
            // Actualizar detecciones
            setObjects(data.objects || []);
            setHands(data.hands || []);
            
            // Actualizar stats
            if (data.stats) {
              setStats(data.stats);
              setFps(data.stats.fps || 0);
            }
          } 
          else if (data.type === 'welcome') {
            console.log(data.message);
            if (data.config) {
              setConfig({
                depthEnabled: data.config.depth_enabled,
                objectsEnabled: data.config.objects_enabled,
                gesturesEnabled: data.config.gestures_enabled,
                pointcloudEnabled: data.config.pointcloud_enabled,
                pointcloudColorMode: data.config.pointcloud_color_mode || 'rgb'
              });
            }
          }
        } catch (err) {
          console.error('Error procesando mensaje:', err);
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        setError('Error de conexión con el servidor');
      };

      ws.onclose = () => {
        console.log('Desconectado del servidor');
        setConnected(false);
        
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Intentando reconectar...');
          connectWebSocket();
        }, 3000);
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('Error creando WebSocket:', err);
      setError('No se pudo conectar al servidor');
    }
  };

  const sendMessage = (type, data = {}) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, ...data }));
    }
  };

  const toggleDepth = () => {
    sendMessage('toggle_depth');
    setConfig(prev => ({ ...prev, depthEnabled: !prev.depthEnabled }));
  };

  const toggleObjects = () => {
    sendMessage('toggle_objects');
    setConfig(prev => ({ ...prev, objectsEnabled: !prev.objectsEnabled }));
  };

  const toggleGestures = () => {
    sendMessage('toggle_gestures');
    setConfig(prev => ({ ...prev, gesturesEnabled: !prev.gesturesEnabled }));
  };

  const togglePointcloud = () => {
    sendMessage('toggle_pointcloud');
    setConfig(prev => ({ ...prev, pointcloudEnabled: !prev.pointcloudEnabled }));
  };

  const setPointcloudColorMode = (mode) => {
    sendMessage('set_pointcloud_color_mode', { mode });
    setConfig(prev => ({ ...prev, pointcloudColorMode: mode }));
  };

  const getGestureIcon = (gesture) => {
    const icons = {
      'open_palm': '🖐️',
      'closed_fist': '✊',
      'thumbs_up': '👍',
      'thumbs_down': '👎',
      'peace_sign': '✌️',
      'ok_sign': '👌',
      'pointing': '👉',
      'pinch': '🤏',
      'rock': '🤘',
      'call_me': '🤙',
      'three': '3️⃣',
      'four': '4️⃣',
      'spiderman': '🕷️',
      'love': '🤟',
      'gun': '🔫',
      'middle_finger': '🖕',
      'grab': '🫳',
      'unknown': '❓'
    };
    return icons[gesture] || '❓';
  };

  const getObjectIcon = (className) => {
    const icons = {
      'person': '🚶',
      'cup': '☕',
      'bottle': '🍾',
      'book': '📚',
      'cell phone': '📱',
      'laptop': '💻',
      'mouse': '🖱️',
      'keyboard': '⌨️',
      'scissors': '✂️'
    };
    return icons[className] || '📦';
  };

  return (
    <div className="app-container">
      {/* Header */}
      <motion.header 
        className="app-header"
        initial={{ y: -100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.8 }}
      >
        <div className="header-content">
          <motion.div className="logo-container">
            <div className="logo-icon">🎯</div>
            <div>
              <h1 className="logo-title">Kinect Table System</h1>
              <p className="logo-subtitle">Interactive Object & Gesture Recognition</p>
            </div>
          </motion.div>

          <div className="status-container">
            <motion.div 
              className={`status-indicator ${connected ? 'connected' : 'disconnected'}`}
              animate={{ 
                scale: connected ? [1, 1.2, 1] : 1,
                opacity: connected ? [1, 0.7, 1] : 0.5
              }}
              transition={{ duration: 2, repeat: Infinity }}
            />
            <span className="status-text">
              {connected ? 'Conectado' : 'Desconectado'}
            </span>
            <div className="fps-badge">{fps.toFixed(1)} FPS</div>
          </div>
        </div>
      </motion.header>

      {/* Error Banner */}
      <AnimatePresence>
        {error && (
          <motion.div 
            className="error-banner"
            initial={{ y: -50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -50, opacity: 0 }}
          >
            ⚠️ {error}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <div className="main-content">
        {/* Video Feed */}
        <div className="video-section">
          {/* Controles de visualización */}
          <div className="view-controls">
            <button 
              className={`view-btn ${viewMode === 'rgb' ? 'active' : ''}`}
              onClick={() => setViewMode('rgb')}
            >
              📹 RGB
            </button>
            <button 
              className={`view-btn ${viewMode === 'depth' ? 'active' : ''}`}
              onClick={() => setViewMode('depth')}
              disabled={!config.depthEnabled}
            >
              🌊 Depth
            </button>
            <button 
              className={`view-btn ${viewMode === 'split' ? 'active' : ''}`}
              onClick={() => setViewMode('split')}
              disabled={!config.depthEnabled}
            >
              🔀 Split
            </button>
            <button 
              className={`view-btn ${viewMode === '3d' ? 'active' : ''}`}
              onClick={() => setViewMode('3d')}
              disabled={!config.pointcloudEnabled}
            >
              ☁️ 3D
            </button>
          </div>

          {/* Video Display */}
          <motion.div 
            className="video-container"
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
          >
            {viewMode === 'rgb' && (
              <div className="video-wrapper">
                {frameRgb ? (
                  <img 
                    src={`data:image/jpeg;base64,${frameRgb}`} 
                    alt="RGB Feed" 
                    className="video-feed"
                  />
                ) : (
                  <div className="video-placeholder">
                    <div className="placeholder-icon">📹</div>
                    <p>Esperando feed RGB...</p>
                  </div>
                )}
              </div>
            )}

            {viewMode === 'depth' && (
              <div className="video-wrapper">
                {frameDepth ? (
                  <img 
                    src={`data:image/jpeg;base64,${frameDepth}`} 
                    alt="Depth Feed" 
                    className="video-feed"
                  />
                ) : (
                  <div className="video-placeholder">
                    <div className="placeholder-icon">🌊</div>
                    <p>Esperando feed de profundidad...</p>
                  </div>
                )}
              </div>
            )}

            {viewMode === 'split' && (
              <div className="video-split">
                <div className="video-wrapper-half">
                  {frameRgb ? (
                    <img 
                      src={`data:image/jpeg;base64,${frameRgb}`} 
                      alt="RGB" 
                      className="video-feed"
                    />
                  ) : (
                    <div className="video-placeholder-small">RGB</div>
                  )}
                  <div className="video-label">RGB</div>
                </div>
                <div className="video-wrapper-half">
                  {frameDepth ? (
                    <img 
                      src={`data:image/jpeg;base64,${frameDepth}`} 
                      alt="Depth" 
                      className="video-feed"
                    />
                  ) : (
                    <div className="video-placeholder-small">DEPTH</div>
                  )}
                  <div className="video-label">DEPTH</div>
                </div>
              </div>
            )}

            {viewMode === '3d' && (
              <div className="video-wrapper pointcloud-wrapper">
                <PointCloudViewer 
                  pointcloudData={pointcloudData}
                  width={640}
                  height={480}
                  backgroundColor={0x0a0e27}
                  pointSize={0.5}
                  showAxes={true}
                  showGrid={true}
                />
                {/* Controles de color para nube de puntos */}
                <div className="pointcloud-controls">
                  <span className="control-label">Color:</span>
                  <button 
                    className={`color-btn ${config.pointcloudColorMode === 'rgb' ? 'active' : ''}`}
                    onClick={() => setPointcloudColorMode('rgb')}
                  >
                    🎨 RGB
                  </button>
                  <button 
                    className={`color-btn ${config.pointcloudColorMode === 'depth' ? 'active' : ''}`}
                    onClick={() => setPointcloudColorMode('depth')}
                  >
                    🌈 Depth
                  </button>
                  <button 
                    className={`color-btn ${config.pointcloudColorMode === 'height' ? 'active' : ''}`}
                    onClick={() => setPointcloudColorMode('height')}
                  >
                    📏 Height
                  </button>
                </div>
              </div>
            )}
          </motion.div>

          {/* Stats Overlay */}
          <div className="stats-overlay">
            <div className="stat-item">
              <span className="stat-label">Frames:</span>
              <span className="stat-value">{stats.frames_processed}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Objetos:</span>
              <span className="stat-value">{objects.length}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Manos:</span>
              <span className="stat-value">{hands.length}</span>
            </div>
          </div>
        </div>

        {/* Detections Panel */}
        <div className="detections-panel">
          {/* Controles */}
          <div className="controls-section">
            <h3 className="section-title">🎛️ Controles</h3>
            <div className="toggle-buttons">
              <button 
                className={`toggle-btn ${config.depthEnabled ? 'active' : ''}`}
                onClick={toggleDepth}
              >
                {config.depthEnabled ? '✅' : '❌'} Profundidad
              </button>
              <button 
                className={`toggle-btn ${config.objectsEnabled ? 'active' : ''}`}
                onClick={toggleObjects}
              >
                {config.objectsEnabled ? '✅' : '❌'} Objetos
              </button>
              <button 
                className={`toggle-btn ${config.gesturesEnabled ? 'active' : ''}`}
                onClick={toggleGestures}
              >
                {config.gesturesEnabled ? '✅' : '❌'} Gestos
              </button>
              <button 
                className={`toggle-btn ${config.pointcloudEnabled ? 'active' : ''}`}
                onClick={togglePointcloud}
              >
                {config.pointcloudEnabled ? '✅' : '❌'} Nube 3D
              </button>
            </div>
          </div>

          {/* Objetos Detectados */}
          <div className="objects-section">
            <h3 className="section-title">📦 Objetos Detectados</h3>
            <div className="items-grid">
              <AnimatePresence mode="popLayout">
                {objects.length === 0 ? (
                  <motion.div 
                    key="no-objects"
                    className="no-items-message"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    <div className="no-items-icon">📦</div>
                    <p>No hay objetos detectados</p>
                  </motion.div>
                ) : (
                  objects.map((obj, index) => (
                    <motion.div
                      key={`obj-${index}`}
                      className="detection-card object-card"
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.8 }}
                      transition={{ delay: index * 0.05 }}
                    >
                      <div className="card-icon">{getObjectIcon(obj.class_name)}</div>
                      <div className="card-content">
                        <div className="card-title">{obj.class_name}</div>
                        <div className="card-confidence">
                          {(obj.confidence * 100).toFixed(0)}%
                        </div>
                      </div>
                    </motion.div>
                  ))
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* Gestos Detectados */}
          <div className="gestures-section">
            <h3 className="section-title">👋 Gestos Detectados</h3>
            <div className="items-grid">
              <AnimatePresence mode="popLayout">
                {hands.length === 0 ? (
                  <motion.div 
                    key="no-hands"
                    className="no-items-message"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    <div className="no-items-icon">👋</div>
                    <p>No hay gestos detectados</p>
                  </motion.div>
                ) : (
                  hands.map((hand, index) => (
                    <motion.div
                      key={`hand-${index}`}
                      className="detection-card gesture-card"
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.8 }}
                      transition={{ delay: index * 0.05 }}
                    >
                      <div className="card-icon">
                        {getGestureIcon(hand.gesture)}
                      </div>
                      <div className="card-content">
                        <div className="card-title">
                          {hand.handedness === 'Left' ? '👈' : '👉'} {hand.gesture_name}
                        </div>
                        <div className="card-confidence">
                          {(hand.confidence * 100).toFixed(0)}%
                        </div>
                      </div>
                    </motion.div>
                  ))
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>

      {/* Animated Background */}
      <div className="background-decoration">
        <div className="bg-circle bg-circle-1" />
        <div className="bg-circle bg-circle-2" />
        <div className="bg-circle bg-circle-3" />
      </div>
    </div>
  );
}

export default App;
