/**
 * CalibrationPanel.jsx
 * ====================
 * Panel de calibración interactiva del Kinect
 * - Calibración manual: el usuario selecciona sus 4 esquinas de trabajo
 * - Detección automática de plano
 * - Ajuste de orientación (flip)
 * - Reinicio del servidor
 */

import { useState, useCallback, useEffect, useRef } from 'react';

const CORNER_NAMES = ['top_left', 'top_right', 'bottom_right', 'bottom_left'];
const CORNER_LABELS = {
  'top_left': '1. Esquina Superior Izquierda',
  'top_right': '2. Esquina Superior Derecha', 
  'bottom_right': '3. Esquina Inferior Derecha',
  'bottom_left': '4. Esquina Inferior Izquierda'
};

export default function CalibrationPanel({
  ws,
  isConnected,
  calibrationData,
  frameRgb,
  frameDimensions,   // { w, h } – dimensiones reales del frame de captura
  onClose
}) {
  // Dimensiones reales del frame (para escalar correctamente los clics)
  const frameW = frameDimensions?.w || 640;
  const frameH = frameDimensions?.h || 480;
  const [mode, setMode] = useState('menu');
  const [currentStep, setCurrentStep] = useState(0);
  const [capturedPoints, setCapturedPoints] = useState([]);
  const [capturedImagePoints, setCapturedImagePoints] = useState([]); // Puntos 2D donde el usuario hizo clic
  const [message, setMessage] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Punto seleccionado por el usuario (donde hará clic para capturar)
  const [selectedPoint, setSelectedPoint] = useState(null);
  
  // Estado de flip (nube de puntos)
  const [flip, setFlip] = useState({
    x: calibrationData?.flip?.x || false,
    y: calibrationData?.flip?.y || true,
    z: calibrationData?.flip?.z || false
  });
  
  // Estado de flip de video
  const [videoFlip, setVideoFlip] = useState({
    h: false,
    v: false
  });
  
  // Ángulo de inclinación del Kinect
  const [kinectTilt, setKinectTilt] = useState(0);

  const canvasRef = useRef(null);

  // Sincronizar flip con calibrationData cuando cambia desde el servidor
  useEffect(() => {
    if (calibrationData?.flip) {
      setFlip(calibrationData.flip);
    }
  }, [calibrationData?.flip?.x, calibrationData?.flip?.y, calibrationData?.flip?.z]);

  // Manejar mensajes del servidor
  useEffect(() => {
    if (!ws) return;

    const handleMessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'calibration_started':
            setCurrentStep(data.status.calibration_step);
            setMessage('Haz clic en la imagen donde está la ESQUINA SUPERIOR IZQUIERDA de tu área de trabajo');
            break;
            
          case 'calibration_point_captured':
            console.log('Punto capturado:', data);
            setCapturedPoints(prev => [...prev, data.point_3d]);
            if (selectedPoint) {
              setCapturedImagePoints(prev => [...prev, selectedPoint]);
            }
            setCurrentStep(data.status.calibration_step);
            setIsProcessing(false);
            setSelectedPoint(null);
            
            if (data.completed) {
              setMessage('✅ ¡Calibración completada y guardada!');
              setTimeout(() => setMode('menu'), 2000);
            } else {
              const nextCorner = CORNER_NAMES[data.status.calibration_step];
              setMessage(`✅ Punto ${data.status.calibration_step} capturado. Ahora haz clic en: ${CORNER_LABELS[nextCorner]}`);
            }
            break;
            
          case 'calibration_auto_complete':
            setMessage(`✅ Plano detectado. Altura: ${data.table_height.toFixed(3)}m`);
            setIsProcessing(false);
            setTimeout(() => setMode('menu'), 2000);
            break;
            
          case 'calibration_error':
            setMessage(`❌ Error: ${data.error}`);
            setIsProcessing(false);
            break;
            
          case 'calibration_flip_updated':
            setFlip(data.flip);
            setMessage('✅ Orientación actualizada y guardada');
            break;
            
          case 'video_flip_updated':
            setVideoFlip({ h: data.flip_h, v: data.flip_v });
            setMessage('✅ Video volteado');
            break;
            
          case 'kinect_tilt_updated':
            setKinectTilt(data.angle);
            setMessage(`✅ Ángulo: ${data.angle}°`);
            break;
            
          case 'calibration_saved':
            setMessage('✅ Calibración guardada');
            break;
            
          case 'calibration_cancelled':
            setMessage('Calibración cancelada');
            setMode('menu');
            break;
            
          case 'calibration_reset_complete':
            setMessage('🔄 Calibración reiniciada');
            setCapturedPoints([]);
            setCapturedImagePoints([]);
            setCurrentStep(0);
            setSelectedPoint(null);
            break;
            
          case 'server_restarting':
            setMessage('🔄 Reiniciando servidor... La página se reconectará automáticamente.');
            break;
        }
      } catch (err) {
        console.error('Error procesando mensaje:', err);
      }
    };

    ws.addEventListener('message', handleMessage);
    return () => ws.removeEventListener('message', handleMessage);
  }, [ws, selectedPoint]);

  // Solicitar estado al abrir
  useEffect(() => {
    if (ws && isConnected) {
      ws.send(JSON.stringify({ type: 'calibration_get_status' }));
    }
  }, [ws, isConnected]);

  // Dibujar overlay en el canvas
  useEffect(() => {
    if (mode !== 'manual' || !canvasRef.current || !frameRgb) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    const img = new Image();
    img.onload = () => {
      // Dibujar imagen
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      // Escala para convertir coordenadas de imagen real → canvas
      const scaleX = canvas.width / frameW;
      const scaleY = canvas.height / frameH;
      
      // Dibujar puntos ya capturados (en verde)
      capturedImagePoints.forEach((pt, i) => {
        const x = pt.x * scaleX;
        const y = pt.y * scaleY;
        
        // Círculo verde
        ctx.beginPath();
        ctx.arc(x, y, 20, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(0, 255, 136, 0.4)';
        ctx.fill();
        ctx.strokeStyle = '#00ff88';
        ctx.lineWidth = 3;
        ctx.stroke();
        
        // Número
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 16px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`${i + 1}`, x, y);
      });
      
      // Dibujar líneas conectando puntos capturados
      if (capturedImagePoints.length > 1) {
        ctx.strokeStyle = 'rgba(0, 255, 136, 0.6)';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        capturedImagePoints.forEach((pt, i) => {
          const x = pt.x * scaleX;
          const y = pt.y * scaleY;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        if (capturedImagePoints.length === 4) {
          const first = capturedImagePoints[0];
          ctx.lineTo(first.x * scaleX, first.y * scaleY);
        }
        ctx.stroke();
        ctx.setLineDash([]);
      }
      
      // Dibujar punto seleccionado actual (en azul/cyan)
      if (selectedPoint && currentStep < 4) {
        const x = selectedPoint.x * scaleX;
        const y = selectedPoint.y * scaleY;
        
        // Cruz
        ctx.strokeStyle = '#00d4ff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x - 25, y);
        ctx.lineTo(x + 25, y);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x, y - 25);
        ctx.lineTo(x, y + 25);
        ctx.stroke();
        
        // Círculo
        ctx.beginPath();
        ctx.arc(x, y, 30, 0, Math.PI * 2);
        ctx.strokeStyle = '#00d4ff';
        ctx.lineWidth = 3;
        ctx.stroke();
        
        // Texto
        ctx.fillStyle = '#00d4ff';
        ctx.font = 'bold 14px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('CAPTURAR AQUÍ', x, y + 50);
        ctx.fillText(`(${selectedPoint.x}, ${selectedPoint.y})`, x, y + 65);
      }
      
      // Instrucción en pantalla
      if (currentStep < 4) {
        const cornerName = CORNER_NAMES[currentStep];
        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        ctx.fillRect(0, 0, canvas.width, 40);
        ctx.fillStyle = '#ffff00';
        ctx.font = 'bold 14px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(`Paso ${currentStep + 1}/4: Haz clic en tu ${CORNER_LABELS[cornerName]}`, canvas.width / 2, 25);
      }
    };
    img.src = `data:image/jpeg;base64,${frameRgb}`;
  }, [frameRgb, mode, selectedPoint, currentStep, capturedImagePoints, frameW, frameH]);

  // Manejar clic en el canvas
  const handleCanvasClick = useCallback((e) => {
    if (mode !== 'manual' || currentStep >= 4) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();

    // Mapear clic del canvas → coordenadas del frame real (frameW × frameH)
    // El servidor escala internamente estos valores al espacio de imagen correcto.
    const x = Math.round((e.clientX - rect.left) * (640 / canvas.width));
    const y = Math.round((e.clientY - rect.top) * (480 / canvas.height));

    // Limitar a rango válido (en espacio 640×480 normalizado; el servidor re-escala)
    const clampedX = Math.max(0, Math.min(639, x));
    const clampedY = Math.max(0, Math.min(479, y));

    setSelectedPoint({ x: clampedX, y: clampedY });
    setMessage(`Punto seleccionado (${clampedX}, ${clampedY}) → imagen real (~${Math.round(clampedX * frameW / 640)}, ${Math.round(clampedY * frameH / 480)}). Presiona "Capturar".`);
  }, [mode, currentStep, frameW, frameH]);

  // Iniciar calibración manual
  const startManualCalibration = useCallback(() => {
    if (!ws) return;
    setMode('manual');
    setCapturedPoints([]);
    setCapturedImagePoints([]);
    setCurrentStep(0);
    setSelectedPoint(null);
    setMessage('Haz clic en la imagen donde está la ESQUINA SUPERIOR IZQUIERDA de tu área de trabajo');
    ws.send(JSON.stringify({ type: 'calibration_start' }));
  }, [ws]);

  // Capturar punto seleccionado
  const captureSelectedPoint = useCallback(() => {
    if (!ws || !selectedPoint) {
      setMessage('❌ Primero haz clic en la imagen para seleccionar un punto');
      return;
    }
    setIsProcessing(true);
    setMessage('Capturando profundidad...');
    ws.send(JSON.stringify({ 
      type: 'calibration_capture',
      x: selectedPoint.x,
      y: selectedPoint.y
    }));
  }, [ws, selectedPoint]);

  // Detección automática
  const runAutoDetection = useCallback(() => {
    if (!ws) return;
    setMode('auto');
    setIsProcessing(true);
    setMessage('Analizando nube de puntos para detectar plano horizontal...');
    ws.send(JSON.stringify({ type: 'calibration_auto_plane' }));
  }, [ws]);

  // Toggle flip (nube de puntos)
  const toggleFlip = useCallback((axis) => {
    if (!ws) return;
    const newFlip = { ...flip, [axis]: !flip[axis] };
    setFlip(newFlip);
    
    ws.send(JSON.stringify({ 
      type: 'calibration_set_flip',
      [`flip_${axis}`]: newFlip[axis]
    }));
  }, [ws, flip]);

  // Toggle video flip
  const toggleVideoFlip = useCallback((axis) => {
    if (!ws) return;
    const newFlip = { ...videoFlip, [axis]: !videoFlip[axis] };
    setVideoFlip(newFlip);
    
    ws.send(JSON.stringify({ 
      type: 'set_video_flip',
      flip_h: newFlip.h,
      flip_v: newFlip.v
    }));
  }, [ws, videoFlip]);

  // Cambiar ángulo de inclinación del Kinect
  const setKinectTiltAngle = useCallback((angle) => {
    if (!ws) return;
    const numAngle = parseFloat(angle);
    setKinectTilt(numAngle);
    
    ws.send(JSON.stringify({ 
      type: 'set_kinect_tilt',
      angle: numAngle
    }));
  }, [ws]);

  // Cancelar
  const cancelCalibration = useCallback(() => {
    if (!ws) return;
    ws.send(JSON.stringify({ type: 'calibration_cancel' }));
    setMode('menu');
    setCapturedPoints([]);
    setCapturedImagePoints([]);
    setSelectedPoint(null);
  }, [ws]);

  // Reiniciar calibración
  const resetCalibration = useCallback(() => {
    if (!ws) return;
    if (confirm('¿Eliminar la calibración actual?')) {
      ws.send(JSON.stringify({ type: 'calibration_reset' }));
    }
  }, [ws]);

  // Reiniciar servidor
  const restartServer = useCallback(() => {
    if (!ws) return;
    if (confirm('¿Reiniciar el servidor? Tendrás que esperar unos segundos.')) {
      ws.send(JSON.stringify({ type: 'server_restart' }));
      setMessage('🔄 Reiniciando servidor...');
    }
  }, [ws]);

  return (
    <div className="calibration-panel">
      <div className="calibration-header">
        <h2>🎯 Calibración del Sensor</h2>
        <button className="close-btn" onClick={onClose}>✕</button>
      </div>

      {message && (
        <div className={`calibration-message ${message.includes('✅') ? 'success' : message.includes('❌') ? 'error' : ''}`}>
          {message}
        </div>
      )}

      {mode === 'menu' && (
        <div className="calibration-menu">
          <div className="calibration-status-box">
            <h3>Estado Actual</h3>
            <div className="status-item">
              <span>Mesa calibrada:</span>
              <span className={calibrationData?.is_calibrated ? 'yes' : 'no'}>
                {calibrationData?.is_calibrated ? '✅ Sí' : '❌ No'}
              </span>
            </div>
            <div className="status-item">
              <span>Flip X:</span>
              <span>{flip.x ? 'Invertido' : 'Normal'}</span>
            </div>
            <div className="status-item">
              <span>Flip Y:</span>
              <span>{flip.y ? 'Invertido' : 'Normal'}</span>
            </div>
            <div className="status-item">
              <span>Flip Z:</span>
              <span>{flip.z ? 'Invertido' : 'Normal'}</span>
            </div>
          </div>

          <div className="calibration-info-box">
            <h4>📖 ¿Cómo funciona?</h4>
            <p>La calibración calcula una <strong>homografía</strong> que corrige perspectiva y offsets:</p>
            <ol>
              <li>Apunta tu dedo índice a cada <strong>esquina de la pantalla/TV</strong></li>
              <li>Haz clic en la imagen donde aparece la punta de tu dedo</li>
              <li>Presiona "Capturar Punto" para registrar</li>
              <li>Repite para las 4 esquinas (↖ ↗ ↘ ↙)</li>
            </ol>
            <p style={{fontSize:'0.8em', opacity:0.7}}>
              Frame actual: {frameW}×{frameH}px
            </p>
          </div>

          <div className="calibration-options">
            <button 
              className="calibration-btn primary"
              onClick={startManualCalibration}
              disabled={!isConnected}
            >
              📍 Calibración Manual (4 esquinas)
            </button>
            
            <button 
              className="calibration-btn secondary"
              onClick={runAutoDetection}
              disabled={!isConnected || isProcessing}
            >
              🔍 Detección Automática de Plano
            </button>
            
            <button 
              className="calibration-btn secondary"
              onClick={() => setMode('flip')}
            >
              🔄 Ajustar Orientación (Flip)
            </button>
            
            <button 
              className="calibration-btn danger"
              onClick={resetCalibration}
              disabled={!isConnected}
            >
              🗑️ Eliminar Calibración
            </button>

            <div className="calibration-divider"></div>
            
            <button 
              className="calibration-btn warning"
              onClick={restartServer}
              disabled={!isConnected}
            >
              ⚡ Reiniciar Servidor
            </button>
          </div>
        </div>
      )}

      {mode === 'manual' && (
        <div className="calibration-manual">
          <div className="step-indicator">
            <span>Paso {Math.min(currentStep + 1, 4)} de 4</span>
            <div className="step-dots">
              {[0, 1, 2, 3].map(i => (
                <div 
                  key={i} 
                  className={`step-dot ${i < currentStep ? 'completed' : i === currentStep ? 'active' : ''}`}
                />
              ))}
            </div>
          </div>

          {currentStep < 4 && (
            <>
              <div className="calibration-video-container">
                <canvas 
                  ref={canvasRef}
                  width={640}
                  height={480}
                  onClick={handleCanvasClick}
                  className="calibration-canvas"
                />
              </div>

              <div className="canvas-instructions">
                <p><strong>Instrucciones:</strong></p>
                <p>1️⃣ Apunta tu <strong>dedo índice</strong> a la esquina indicada de la pantalla</p>
                <p>2️⃣ Haz clic en la imagen EXACTAMENTE donde ves la punta de tu dedo</p>
                <p>3️⃣ Presiona "Capturar Punto" para registrar</p>
              </div>

              {selectedPoint && (
                <div className="capture-info">
                  <span>📍 Punto seleccionado: X={selectedPoint.x}, Y={selectedPoint.y}</span>
                </div>
              )}

              <div className="capture-buttons">
                <button 
                  className="calibration-btn primary large"
                  onClick={captureSelectedPoint}
                  disabled={isProcessing || !selectedPoint}
                >
                  {isProcessing ? '⏳ Capturando...' : '📷 Capturar Punto'}
                </button>
                
                <button 
                  className="calibration-btn secondary"
                  onClick={cancelCalibration}
                >
                  Cancelar
                </button>
              </div>
            </>
          )}

          {capturedPoints.length > 0 && (
            <div className="captured-points">
              <h4>✅ Puntos Capturados ({capturedPoints.length}/4):</h4>
              <ul>
                {capturedPoints.map((point, i) => (
                  <li key={i}>
                    <span className="point-label">{CORNER_LABELS[CORNER_NAMES[i]].split('. ')[1]}:</span>
                    <span className="point-coords">
                      img=({Math.round(point[0])}, {Math.round(point[1])})px
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {mode === 'auto' && (
        <div className="calibration-auto">
          <div className="auto-status">
            {isProcessing ? (
              <>
                <div className="spinner"></div>
                <p>Analizando nube de puntos...</p>
                <p className="auto-hint">Esto detecta el plano horizontal más grande (tu mesa)</p>
              </>
            ) : (
              <p>{message}</p>
            )}
          </div>
          
          <button 
            className="calibration-btn secondary"
            onClick={() => setMode('menu')}
          >
            Volver
          </button>
        </div>
      )}

      {mode === 'flip' && (
        <div className="calibration-flip">
          <h3>Ajustar Orientación de Ejes</h3>
          {/* Volteo de video */}
          <h4 className="flip-section-title">📹 Volteo de Video</h4>
          <p className="flip-description">
            Si el video aparece invertido, activa el volteo correspondiente.
          </p>
          
          <div className="flip-controls video-flip">
            <button 
              className={`flip-btn ${videoFlip.h ? 'active' : ''}`}
              onClick={() => toggleVideoFlip('h')}
            >
              <span className="axis">↔️</span>
              <span className="status">{videoFlip.h ? 'Espejo' : 'Normal'}</span>
              <span className="hint">Horizontal</span>
            </button>
            
            <button 
              className={`flip-btn ${videoFlip.v ? 'active' : ''}`}
              onClick={() => toggleVideoFlip('v')}
            >
              <span className="axis">↕️</span>
              <span className="status">{videoFlip.v ? 'Invertido' : 'Normal'}</span>
              <span className="hint">Vertical</span>
            </button>
          </div>
          
          {/* Ángulo de inclinación del Kinect */}
          <h4 className="flip-section-title">📐 Ángulo de Inclinación</h4>
          <p className="flip-description">
            Si el Kinect no está perpendicular a la mesa, ajusta el ángulo de inclinación.
          </p>
          
          <div className="tilt-control">
            <input
              type="range"
              min="-45"
              max="45"
              step="1"
              value={kinectTilt}
              onChange={(e) => setKinectTiltAngle(e.target.value)}
              className="tilt-slider"
            />
            <div className="tilt-value">
              <span className="tilt-label">{kinectTilt}°</span>
              <span className="tilt-hint">
                {kinectTilt > 0 ? '↘️ Mirando hacia abajo' : kinectTilt < 0 ? '↗️ Mirando hacia arriba' : '→ Perpendicular'}
              </span>
            </div>
            <div className="tilt-presets">
              <button onClick={() => setKinectTiltAngle(0)}>0°</button>
              <button onClick={() => setKinectTiltAngle(15)}>15°</button>
              <button onClick={() => setKinectTiltAngle(20)}>20°</button>
              <button onClick={() => setKinectTiltAngle(30)}>30°</button>
            </div>
          </div>
          
          {/* Volteo de nube de puntos */}
          <h4 className="flip-section-title">☁️ Volteo de Nube de Puntos</h4>
          <p className="flip-description">
            Si la nube de puntos aparece invertida, activa el flip del eje correspondiente.
          </p>
          
          <div className="flip-controls">
            <button 
              className={`flip-btn ${flip.x ? 'active' : ''}`}
              onClick={() => toggleFlip('x')}
            >
              <span className="axis">X</span>
              <span className="status">{flip.x ? 'Invertido' : 'Normal'}</span>
              <span className="hint">Izq ↔ Der</span>
            </button>
            
            <button 
              className={`flip-btn ${flip.y ? 'active' : ''}`}
              onClick={() => toggleFlip('y')}
            >
              <span className="axis">Y</span>
              <span className="status">{flip.y ? 'Invertido' : 'Normal'}</span>
              <span className="hint">Arriba ↔ Abajo</span>
            </button>
            
            <button 
              className={`flip-btn ${flip.z ? 'active' : ''}`}
              onClick={() => toggleFlip('z')}
            >
              <span className="axis">Z</span>
              <span className="status">{flip.z ? 'Invertido' : 'Normal'}</span>
              <span className="hint">Cerca ↔ Lejos</span>
            </button>
          </div>
          
          <button 
            className="calibration-btn secondary"
            onClick={() => setMode('menu')}
          >
            Volver
          </button>
        </div>
      )}
    </div>
  );
}
