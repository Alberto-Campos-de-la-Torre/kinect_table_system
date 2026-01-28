import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './App.css';
import PointCloudViewer from './PointCloudViewer';
import CalibrationPanel from './CalibrationPanel';
import InteractionDemo from './InteractionDemo';
import InteractionDemo3D from './InteractionDemo3D';

const WEBSOCKET_URL = 'ws://localhost:8765';

function App() {
  // Estado de conexión
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);
  
  // Estado de pantalla completa
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [fullscreenMode, setFullscreenMode] = useState('rgb'); // 'rgb', 'projection', 'demo', 'demo3d'
  const appContainerRef = useRef(null);
  
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
    pointcloudColorMode: 'rgb',
    interactionsEnabled: true
  });
  
  // Datos de interacción
  const [interactionData, setInteractionData] = useState(null);
  
  // Panel de calibración
  const [showCalibration, setShowCalibration] = useState(false);
  const [calibrationData, setCalibrationData] = useState({
    is_calibrated: false,
    has_intrinsics: false,
    flip: { x: false, y: true, z: false }
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
            
            // Actualizar datos de interacción
            if (data.interaction) {
              setInteractionData(data.interaction);
            }
            
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
                pointcloudColorMode: data.config.pointcloud_color_mode || 'rgb',
                interactionsEnabled: data.config.interactions_enabled ?? true
              });
              
              // Cargar estado de calibración
              if (data.config.calibration) {
                setCalibrationData(data.config.calibration);
              }
            }
          }
          // Manejar toggle de interacciones
          else if (data.type === 'interactions_toggled') {
            setConfig(prev => ({ ...prev, interactionsEnabled: data.enabled }));
          }
          // Actualizar estado de calibración cuando se guarda
          else if (data.type === 'calibration_saved') {
            // Solicitar estado actualizado
            if (wsRef.current) {
              wsRef.current.send(JSON.stringify({ type: 'calibration_get_status' }));
            }
          }
          // Actualización inmediata del flip
          else if (data.type === 'calibration_flip_updated') {
            console.log('Flip actualizado:', data.flip);
            setCalibrationData(prev => ({
              ...prev,
              flip: data.flip
            }));
          }
          else if (data.type === 'calibration_status') {
            setCalibrationData({
              is_calibrated: data.calibration?.has_table_plane || false,
              has_intrinsics: data.calibration?.has_intrinsics || false,
              flip: data.calibration?.flip || { x: false, y: true, z: false }
            });
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

  const toggleInteractions = () => {
    sendMessage('toggle_interactions');
    setConfig(prev => ({ ...prev, interactionsEnabled: !prev.interactionsEnabled }));
  };

  // ==========================================
  // Funciones de Pantalla Completa
  // ==========================================
  
  const enterFullscreen = useCallback((mode = 'rgb') => {
    setFullscreenMode(mode);
    
    const elem = appContainerRef.current || document.documentElement;
    
    if (elem.requestFullscreen) {
      elem.requestFullscreen();
    } else if (elem.webkitRequestFullscreen) {
      elem.webkitRequestFullscreen();
    } else if (elem.msRequestFullscreen) {
      elem.msRequestFullscreen();
    }
    
    setIsFullscreen(true);
  }, []);

  const exitFullscreen = useCallback(() => {
    if (document.exitFullscreen) {
      document.exitFullscreen();
    } else if (document.webkitExitFullscreen) {
      document.webkitExitFullscreen();
    } else if (document.msExitFullscreen) {
      document.msExitFullscreen();
    }
    setIsFullscreen(false);
  }, []);

  const toggleFullscreen = useCallback((mode = 'rgb') => {
    if (isFullscreen) {
      exitFullscreen();
    } else {
      enterFullscreen(mode);
    }
  }, [isFullscreen, enterFullscreen, exitFullscreen]);

  // Escuchar eventos de fullscreen
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isFS = !!(document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement);
      setIsFullscreen(isFS);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('msfullscreenchange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
      document.removeEventListener('msfullscreenchange', handleFullscreenChange);
    };
  }, []);

  // Manejar tecla ESC para salir de fullscreen
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isFullscreen) {
        exitFullscreen();
      }
      // F11 para toggle fullscreen
      if (e.key === 'F11') {
        e.preventDefault();
        toggleFullscreen(viewMode);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullscreen, exitFullscreen, toggleFullscreen, viewMode]);

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

  // Renderizado de pantalla completa
  if (isFullscreen) {
    return (
      <div 
        ref={appContainerRef}
        className={`fullscreen-container fullscreen-mode-${fullscreenMode}`}
      >
        {/* Barra de control flotante */}
        <div className="fullscreen-controls">
          <div className="fs-status">
            <span className={`fs-indicator ${connected ? 'connected' : ''}`} />
            <span>{fps.toFixed(1)} FPS</span>
          </div>
          
          <div className="fs-mode-selector">
            <button 
              className={`fs-btn ${fullscreenMode === 'rgb' ? 'active' : ''}`}
              onClick={() => setFullscreenMode('rgb')}
            >
              📹 RGB
            </button>
            <button 
              className={`fs-btn ${fullscreenMode === 'projection' ? 'active' : ''}`}
              onClick={() => setFullscreenMode('projection')}
            >
              🎯 Proyección
            </button>
            <button 
              className={`fs-btn ${fullscreenMode === 'demo' ? 'active' : ''}`}
              onClick={() => setFullscreenMode('demo')}
            >
              🎮 Demo 2D
            </button>
            <button 
              className={`fs-btn ${fullscreenMode === 'demo3d' ? 'active' : ''}`}
              onClick={() => setFullscreenMode('demo3d')}
            >
              🌐 Demo 3D
            </button>
          </div>
          
          <div className="fs-actions">
            <button 
              className="fs-btn calibrate"
              onClick={() => setShowCalibration(true)}
            >
              🎯 Calibrar
            </button>
            <button 
              className="fs-btn exit"
              onClick={exitFullscreen}
            >
              ✕ Salir (ESC)
            </button>
          </div>
        </div>

        {/* Contenido Fullscreen */}
        <div className="fullscreen-content">
          {fullscreenMode === 'rgb' && frameRgb && (
            <img 
              src={`data:image/jpeg;base64,${frameRgb}`} 
              alt="RGB Feed" 
              className="fullscreen-video"
            />
          )}

          {fullscreenMode === 'projection' && (
            <div className="projection-mode">
              {/* Modo proyección: fondo negro con indicadores de manos */}
              <div className="projection-canvas">
                {/* Indicadores de manos detectadas */}
                {hands.map((hand, idx) => {
                  // Obtener coordenadas del centro de la mano
                  // El centro puede venir como array [x, y] o como objeto {x, y}
                  let handX = 0, handY = 0;
                  
                  if (hand.center) {
                    if (Array.isArray(hand.center)) {
                      handX = hand.center[0] || 0;
                      handY = hand.center[1] || 0;
                    } else if (typeof hand.center === 'object') {
                      handX = hand.center.x || 0;
                      handY = hand.center.y || 0;
                    }
                  }
                  
                  // Calcular porcentaje para toda la pantalla (640x480 es la resolución de captura)
                  const leftPercent = (handX / 640) * 100;
                  const topPercent = (handY / 480) * 100;
                  
                  return (
                    <div 
                      key={idx}
                      className={`projection-hand ${hand.handedness?.toLowerCase() || 'right'} ${hand.gesture === 'closed_fist' ? 'grabbing' : ''}`}
                      style={{
                        left: `${leftPercent}%`,
                        top: `${topPercent}%`
                      }}
                    >
                      <div className="hand-cursor">
                        <span className="cursor-icon">
                          {hand.gesture === 'closed_fist' ? '✊' : '🖐️'}
                        </span>
                        <span className="cursor-ring" />
                      </div>
                      <div className="hand-label">
                        {hand.handedness === 'Left' ? '👈 Izq' : '👉 Der'}
                      </div>
                      {/* Debug info */}
                      <div className="hand-debug">
                        ({Math.round(handX)}, {Math.round(handY)})
                      </div>
                    </div>
                  );
                })}
                
                {/* Marco de área de trabajo */}
                <div className="work-area-frame">
                  <div className="corner top-left" />
                  <div className="corner top-right" />
                  <div className="corner bottom-left" />
                  <div className="corner bottom-right" />
                </div>
                
                {/* Información de estado */}
                <div className="projection-info">
                  <span>🖐️ Manos: {hands.length}</span>
                  {interactionData?.selected_count > 0 && (
                    <span className="selected-info">
                      ✅ Seleccionados: {interactionData.selected_count}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          {fullscreenMode === 'demo' && (
            <div className="fullscreen-demo">
              <InteractionDemo
                ws={wsRef.current}
                isConnected={connected}
                interaction={interactionData}
                hands={hands}
                width={window.innerWidth}
                height={window.innerHeight}
                isFullscreen={true}
              />
            </div>
          )}

          {fullscreenMode === 'demo3d' && (
            <div className="fullscreen-demo">
              <InteractionDemo3D
                ws={wsRef.current}
                isConnected={connected}
                interaction={interactionData}
                hands={hands}
                width={window.innerWidth}
                height={window.innerHeight}
                isFullscreen={true}
              />
            </div>
          )}

          {/* Mensaje si no hay video */}
          {fullscreenMode === 'rgb' && !frameRgb && (
            <div className="fullscreen-placeholder">
              <div className="placeholder-spinner" />
              <p>Esperando señal del Kinect...</p>
            </div>
          )}
        </div>

        {/* Panel de calibración en fullscreen */}
        <AnimatePresence>
          {showCalibration && (
            <>
              <motion.div 
                className="calibration-overlay fullscreen-calibration-overlay"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setShowCalibration(false)}
              />
              <motion.div
                className="fullscreen-calibration-panel"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
              >
                <CalibrationPanel 
                  ws={wsRef.current}
                  isConnected={connected}
                  calibrationData={calibrationData}
                  frameRgb={frameRgb}
                  onClose={() => setShowCalibration(false)}
                />
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </div>
    );
  }

  return (
    <div className="app-container" ref={appContainerRef}>
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
            
            {/* Botón de pantalla completa en header */}
            <button 
              className="fullscreen-header-btn"
              onClick={() => enterFullscreen(viewMode)}
              title="Pantalla completa (F11)"
            >
              ⛶
            </button>
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
            <button 
              className={`view-btn demo-btn ${viewMode === 'demo' ? 'active' : ''}`}
              onClick={() => setViewMode('demo')}
              disabled={!config.interactionsEnabled}
            >
              🎮 2D
            </button>
            <button 
              className={`view-btn demo-3d-btn ${viewMode === 'demo3d' ? 'active' : ''}`}
              onClick={() => setViewMode('demo3d')}
              disabled={!config.interactionsEnabled}
            >
              🌐 3D
            </button>
            
            {/* Separador */}
            <div className="view-controls-separator" />
            
            {/* Botones de pantalla completa */}
            <button 
              className="view-btn fullscreen-btn"
              onClick={() => enterFullscreen(viewMode)}
              title="Pantalla completa con vista actual"
            >
              ⛶ Completa
            </button>
            <button 
              className="view-btn projection-btn"
              onClick={() => enterFullscreen('projection')}
              title="Modo proyección para mesa"
            >
              🎯 Proyectar
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

            {viewMode === 'demo' && (
              <div className="video-wrapper demo-wrapper">
                <InteractionDemo
                  ws={wsRef.current}
                  isConnected={connected}
                  interaction={interactionData}
                  hands={hands}
                  width={640}
                  height={480}
                />
              </div>
            )}

            {viewMode === 'demo3d' && (
              <div className="video-wrapper demo-wrapper-3d">
                <InteractionDemo3D
                  ws={wsRef.current}
                  isConnected={connected}
                  interaction={interactionData}
                  hands={hands}
                  width={640}
                  height={480}
                />
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
              <button 
                className={`toggle-btn ${config.interactionsEnabled ? 'active' : ''}`}
                onClick={toggleInteractions}
              >
                {config.interactionsEnabled ? '✅' : '❌'} Interacciones
              </button>
              <button 
                className={`toggle-btn calibration-btn-main ${calibrationData.is_calibrated ? 'calibrated' : ''}`}
                onClick={() => setShowCalibration(true)}
              >
                🎯 Calibración {calibrationData.is_calibrated ? '✅' : '⚠️'}
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

          {/* Estado de Interacción */}
          {config.interactionsEnabled && interactionData && (
            <div className="interaction-section">
              <h3 className="section-title">🎮 Estado de Interacción</h3>
              <div className="interaction-status">
                {Object.entries(interactionData.hands || {}).map(([hand, state]) => (
                  <div key={hand} className="hand-status-card">
                    <div className="hand-status-header">
                      <span>{hand === 'Left' ? '👈' : '👉'} {hand}</span>
                      <span className={`state-badge state-${state?.state || 'idle'}`}>
                        {state?.state || 'idle'}
                      </span>
                    </div>
                    {state?.selected && (
                      <div className="hand-status-detail">
                        Objeto seleccionado: #{state.selected}
                      </div>
                    )}
                    {state?.hovered && !state?.selected && (
                      <div className="hand-status-detail">
                        Hover: #{state.hovered}
                      </div>
                    )}
                  </div>
                ))}
                
                <div className="interaction-counters">
                  <div className="counter">
                    <span className="counter-value">{interactionData.selected_count || 0}</span>
                    <span className="counter-label">Seleccionados</span>
                  </div>
                  <div className="counter">
                    <span className="counter-value">{interactionData.hovered_count || 0}</span>
                    <span className="counter-label">Hover</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Panel de Calibración */}
      <AnimatePresence>
        {showCalibration && (
          <>
            <motion.div 
              className="calibration-overlay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowCalibration(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
            >
              <CalibrationPanel 
                ws={wsRef.current}
                isConnected={connected}
                calibrationData={calibrationData}
                frameRgb={frameRgb}
                onClose={() => setShowCalibration(false)}
              />
            </motion.div>
          </>
        )}
      </AnimatePresence>

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
