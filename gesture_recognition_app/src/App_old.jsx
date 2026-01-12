import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './App.css';

const WEBSOCKET_URL = 'ws://localhost:8765';

function App() {
  const [connected, setConnected] = useState(false);
  const [hands, setHands] = useState([]);
  const [fps, setFps] = useState(0);
  const [frame, setFrame] = useState(null);
  const [error, setError] = useState(null);
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
        console.log('Conectado al servidor');
        setConnected(true);
        setError(null);
        ws.send(JSON.stringify({ type: 'start_camera', camera_id: 0 }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'frame') {
            setFrame(data.frame);
            setHands(data.hands || []);
            setFps(data.fps || 0);
          } else if (data.type === 'welcome') {
            console.log(data.message);
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
        
        // Intentar reconectar después de 3 segundos
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

  const getGestureIcon = (gesture) => {
    const icons = {
      'open_palm': '🖐️',
      'closed_fist': '✊',
      'thumbs_up': '👍',
      'thumbs_down': '👎',
      'peace_sign': '✌️',
      'ok_sign': '👌',
      'pointing': '☝️',
      'pinch': '🤏',
      'unknown': '❓'
    };
    return icons[gesture] || '❓';
  };

  const getHandColor = (handedness) => {
    return handedness === 'Left' ? 'from-cyan-500 to-blue-600' : 'from-pink-500 to-purple-600';
  };

  return (
    <div className="app-container">
      {/* Header con efecto de cristal */}
      <motion.header 
        className="app-header"
        initial={{ y: -100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      >
        <div className="header-content">
          <motion.div 
            className="logo-container"
            whileHover={{ scale: 1.05 }}
            transition={{ type: "spring", stiffness: 400 }}
          >
            <div className="logo-icon">🤖</div>
            <div>
              <h1 className="logo-title">Hand Gesture Recognition</h1>
              <p className="logo-subtitle">Kinect Table System</p>
            </div>
          </motion.div>

          <div className="status-container">
            <motion.div 
              className={`status-indicator ${connected ? 'connected' : 'disconnected'}`}
              animate={{ 
                scale: connected ? [1, 1.2, 1] : 1,
                opacity: connected ? [1, 0.7, 1] : 0.5
              }}
              transition={{ 
                duration: 2, 
                repeat: connected ? Infinity : 0,
                ease: "easeInOut" 
              }}
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
        <motion.div 
          className="video-container"
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <div className="video-wrapper">
            {frame ? (
              <img 
                src={`data:image/jpeg;base64,${frame}`} 
                alt="Hand Tracking" 
                className="video-feed"
              />
            ) : (
              <div className="video-placeholder">
                <motion.div 
                  className="placeholder-icon"
                  animate={{ 
                    scale: [1, 1.1, 1],
                    rotate: [0, 5, -5, 0]
                  }}
                  transition={{ 
                    duration: 3, 
                    repeat: Infinity,
                    ease: "easeInOut" 
                  }}
                >
                  📹
                </motion.div>
                <p>Esperando feed de video...</p>
              </div>
            )}
          </div>

          {/* Video Overlay Info */}
          {hands.length > 0 && (
            <div className="video-overlay">
              <motion.div 
                className="hands-detected-badge"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 300 }}
              >
                {hands.length} {hands.length === 1 ? 'Mano' : 'Manos'} Detectadas
              </motion.div>
            </div>
          )}
        </motion.div>

        {/* Hands Panel */}
        <div className="hands-panel">
          <motion.h2 
            className="panel-title"
            initial={{ x: 50, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            Gestos Detectados
          </motion.h2>

          <div className="hands-grid">
            <AnimatePresence mode="popLayout">
              {hands.length === 0 ? (
                <motion.div 
                  key="no-hands"
                  className="no-hands-message"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="no-hands-icon">👋</div>
                  <p>Muestra tus manos frente a la cámara</p>
                </motion.div>
              ) : (
                hands.map((hand, index) => (
                  <motion.div
                    key={`hand-${index}-${hand.handedness}`}
                    className="hand-card"
                    initial={{ opacity: 0, scale: 0.8, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.8, y: -20 }}
                    transition={{ 
                      type: "spring", 
                      stiffness: 300, 
                      damping: 25,
                      delay: index * 0.1 
                    }}
                    whileHover={{ scale: 1.05, y: -5 }}
                  >
                    <div className={`hand-gradient bg-gradient-to-br ${getHandColor(hand.handedness)}`} />
                    
                    <div className="hand-card-content">
                      <div className="hand-header">
                        <motion.span 
                          className="hand-icon"
                          animate={{ rotate: [0, 10, -10, 0] }}
                          transition={{ duration: 2, repeat: Infinity }}
                        >
                          {hand.handedness === 'Left' ? '👈' : '👉'}
                        </motion.span>
                        <div className="hand-info">
                          <h3 className="hand-title">Mano {hand.handedness === 'Left' ? 'Izquierda' : 'Derecha'}</h3>
                          <p className="hand-confidence">{(hand.confidence * 100).toFixed(0)}% confianza</p>
                        </div>
                      </div>

                      <div className="gesture-display">
                        <motion.div 
                          className="gesture-icon-large"
                          key={hand.gesture}
                          initial={{ scale: 0, rotate: -180 }}
                          animate={{ scale: 1, rotate: 0 }}
                          transition={{ type: "spring", stiffness: 200 }}
                        >
                          {getGestureIcon(hand.gesture)}
                        </motion.div>
                        <p className="gesture-name">{hand.gesture_name}</p>
                      </div>

                      <div className="hand-details">
                        <div className="detail-item">
                          <span className="detail-label">Posición</span>
                          <span className="detail-value">
                            X: {hand.center.x.toFixed(0)} Y: {hand.center.y.toFixed(0)}
                          </span>
                        </div>
                        <div className="detail-item">
                          <span className="detail-label">Landmarks</span>
                          <span className="detail-value">{hand.landmarks.length} puntos</span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))
              )}
            </AnimatePresence>
          </div>

          {/* Gesture Guide */}
          <motion.div 
            className="gesture-guide"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <h3 className="guide-title">Gestos Disponibles</h3>
            <div className="gesture-grid">
              {[
                { icon: '🖐️', name: 'Mano Abierta' },
                { icon: '✊', name: 'Puño' },
                { icon: '👍', name: 'Pulgar Arriba' },
                { icon: '👎', name: 'Pulgar Abajo' },
                { icon: '✌️', name: 'Paz' },
                { icon: '👌', name: 'OK' },
                { icon: '☝️', name: 'Señalar' },
                { icon: '🤏', name: 'Pellizco' }
              ].map((gesture, i) => (
                <motion.div
                  key={i}
                  className="gesture-item"
                  whileHover={{ scale: 1.1, y: -3 }}
                  transition={{ type: "spring", stiffness: 400 }}
                >
                  <span className="gesture-item-icon">{gesture.icon}</span>
                  <span className="gesture-item-name">{gesture.name}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
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
