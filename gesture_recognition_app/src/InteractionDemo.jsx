import { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * InteractionDemo - Panel de demostración de interacciones
 * 
 * Muestra figuras virtuales que se pueden manipular con gestos:
 * - 🖐️ Palma abierta: Seleccionar objeto (hover → select)
 * - ✊ Puño cerrado: Arrastrar objeto seleccionado
 */

// Colores de las figuras
const SHAPE_COLORS = {
  circle: '#ef4444',
  square: '#22c55e',
  triangle: '#3b82f6',
  star: '#eab308',
  diamond: '#a855f7',
  hexagon: '#f97316'
};

// Componente de figura
function DemoShape({ 
  object, 
  isSelected, 
  isHovered, 
  onSelect,
  canvasScale = { x: 1, y: 1 } // Factor de escala del canvas
}) {
  const { id, class_name, bbox, center, offset, rotation, scale } = object;
  const [x, y, width, height] = bbox;
  
  // Calcular posición con offset y escalar al tamaño del canvas
  const posX = (x + (offset?.[0] || 0)) * canvasScale.x;
  const posY = (y + (offset?.[1] || 0)) * canvasScale.y;
  const scaledWidth = width * canvasScale.x;
  const scaledHeight = height * canvasScale.y;
  
  // Determinar tipo de figura por nombre
  const getShapeType = (name) => {
    if (name.includes('Círculo')) return 'circle';
    if (name.includes('Cuadrado')) return 'square';
    if (name.includes('Triángulo')) return 'triangle';
    if (name.includes('Estrella')) return 'star';
    if (name.includes('Diamante')) return 'diamond';
    if (name.includes('Hexágono')) return 'hexagon';
    return 'square';
  };
  
  const shapeType = getShapeType(class_name);
  const color = SHAPE_COLORS[shapeType] || '#888';
  
  // Estilo base con dimensiones escaladas
  const baseStyle = {
    position: 'absolute',
    left: posX,
    top: posY,
    width: scaledWidth * (scale || 1),
    height: scaledHeight * (scale || 1),
    transform: `rotate(${rotation || 0}deg)`,
    transformOrigin: 'center center',
    cursor: 'pointer',
    transition: 'box-shadow 0.2s, transform 0.1s'
  };
  
  // Renderizar forma específica
  const renderShape = () => {
    const commonProps = {
      style: {
        ...baseStyle,
        backgroundColor: color,
        border: isSelected ? '4px solid #fff' : isHovered ? '3px solid rgba(255,255,255,0.7)' : '2px solid rgba(255,255,255,0.3)',
        boxShadow: isSelected 
          ? `0 0 30px ${color}, 0 0 60px ${color}50`
          : isHovered 
            ? `0 0 20px ${color}80`
            : `0 0 10px ${color}40`
      }
    };
    
    switch (shapeType) {
      case 'circle':
        return (
          <motion.div 
            {...commonProps}
            style={{ ...commonProps.style, borderRadius: '50%' }}
            animate={{ scale: isSelected ? 1.1 : 1 }}
          />
        );
        
      case 'triangle':
        return (
          <motion.div
            style={{
              ...baseStyle,
              width: 0,
              height: 0,
              backgroundColor: 'transparent',
              borderLeft: `${scaledWidth/2}px solid transparent`,
              borderRight: `${scaledWidth/2}px solid transparent`,
              borderBottom: `${scaledHeight}px solid ${color}`,
              filter: isSelected 
                ? `drop-shadow(0 0 20px ${color})`
                : `drop-shadow(0 0 10px ${color}40)`
            }}
            animate={{ scale: isSelected ? 1.1 : 1 }}
          />
        );
        
      case 'diamond':
        return (
          <motion.div 
            {...commonProps}
            style={{ 
              ...commonProps.style, 
              transform: `rotate(${(rotation || 0) + 45}deg)`,
              borderRadius: '4px'
            }}
            animate={{ scale: isSelected ? 1.1 : 1 }}
          />
        );
        
      case 'star':
        return (
          <motion.div
            style={{
              ...baseStyle,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: `${scaledWidth * 0.8}px`,
              filter: isSelected 
                ? `drop-shadow(0 0 20px ${color})`
                : `drop-shadow(0 0 10px ${color}40)`
            }}
            animate={{ scale: isSelected ? 1.2 : 1 }}
          >
            ⭐
          </motion.div>
        );
        
      case 'hexagon':
        return (
          <motion.div 
            {...commonProps}
            style={{ 
              ...commonProps.style, 
              borderRadius: '15%',
              clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)'
            }}
            animate={{ scale: isSelected ? 1.1 : 1 }}
          />
        );
        
      default: // square
        return (
          <motion.div 
            {...commonProps}
            style={{ ...commonProps.style, borderRadius: '8px' }}
            animate={{ scale: isSelected ? 1.1 : 1 }}
          />
        );
    }
  };
  
  return (
    <div className="demo-shape-container">
      {renderShape()}
      
      {/* Etiqueta */}
      {(isSelected || isHovered) && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            position: 'absolute',
            left: posX + scaledWidth / 2,
            top: posY - 30,
            transform: 'translateX(-50%)',
            backgroundColor: isSelected ? '#22c55e' : '#3b82f6',
            color: '#fff',
            padding: '4px 12px',
            borderRadius: 20,
            fontSize: 12,
            fontWeight: 'bold',
            whiteSpace: 'nowrap',
            zIndex: 100
          }}
        >
          {class_name} {isSelected ? '✓' : ''}
        </motion.div>
      )}
    </div>
  );
}

// Cursor de mano virtual
function HandCursor({ hand, position, gesture, isActive, state }) {
  if (!position || (position[0] === 0 && position[1] === 0)) {
    return null;
  }
  
  // Determinar icono y color según gesto y estado
  let gestureIcon = '✋';
  let color = 'rgba(128, 128, 128, 0.7)';
  
  if (gesture === 'closed_fist') {
    gestureIcon = '✊';
    color = state === 'dragging' 
      ? 'rgba(239, 68, 68, 0.95)' 
      : 'rgba(239, 68, 68, 0.8)';
  } else if (gesture === 'open_palm') {
    gestureIcon = '🖐️';
    color = state === 'selected' 
      ? 'rgba(34, 197, 94, 0.95)'
      : 'rgba(34, 197, 94, 0.8)';
  }
  
  return (
    <motion.div
      style={{
        position: 'absolute',
        left: position[0] - 30,
        top: position[1] - 30,
        width: 60,
        height: 60,
        borderRadius: '50%',
        backgroundColor: color,
        border: '4px solid #fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 28,
        zIndex: 200,
        pointerEvents: 'none',
        boxShadow: `0 0 30px ${color}`
      }}
      animate={{
        scale: state === 'dragging' ? 1.3 : isActive ? 1.1 : 1
      }}
      transition={{ type: 'spring', stiffness: 400, damping: 25 }}
    >
      {gestureIcon}
      
      {/* Indicador de mano */}
      <div
        style={{
          position: 'absolute',
          top: -20,
          left: '50%',
          transform: 'translateX(-50%)',
          backgroundColor: color,
          color: '#fff',
          padding: '2px 8px',
          borderRadius: 8,
          fontSize: 10,
          fontWeight: 'bold',
          whiteSpace: 'nowrap'
        }}
      >
        {hand === 'Left' ? '← Izq' : 'Der →'}
      </div>
      
      {/* Anillo de estado */}
      {state === 'dragging' && (
        <motion.div
          style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            borderRadius: '50%',
            border: '3px solid #fff'
          }}
          animate={{
            scale: [1, 1.4, 1],
            opacity: [1, 0, 1]
          }}
          transition={{
            duration: 0.8,
            repeat: Infinity
          }}
        />
      )}
    </motion.div>
  );
}

// Panel de instrucciones
function InstructionsPanel() {
  return (
    <div className="demo-instructions">
      <h3>🎮 Controles de Interacción</h3>
      <div className="instruction-item">
        <span className="gesture-icon">🖐️</span>
        <div>
          <strong>Palma Abierta</strong>
          <p>Mueve sobre un objeto para seleccionarlo</p>
        </div>
      </div>
      <div className="instruction-item">
        <span className="gesture-icon">✊</span>
        <div>
          <strong>Puño Cerrado</strong>
          <p>Cierra el puño para arrastrar el objeto</p>
        </div>
      </div>
      <div className="instruction-item">
        <span className="gesture-icon">🖐️</span>
        <div>
          <strong>Soltar</strong>
          <p>Abre la mano para soltar el objeto</p>
        </div>
      </div>
    </div>
  );
}

// Componente principal
export default function InteractionDemo({ 
  ws,
  isConnected,
  interaction,
  hands = [],
  width = 640,
  height = 480 
}) {
  const [demoObjects, setDemoObjects] = useState([]);
  const [demoActive, setDemoActive] = useState(false);
  
  // Agregar objetos de demo
  const addDemoObjects = useCallback(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'add_demo_objects' }));
      setDemoActive(true);
    }
  }, [ws]);
  
  // Limpiar objetos de demo
  const clearDemoObjects = useCallback(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'clear_demo_objects' }));
      setDemoActive(false);
      setDemoObjects([]);
    }
  }, [ws]);
  
  // Actualizar objetos desde la interacción
  useEffect(() => {
    if (interaction?.objects) {
      setDemoObjects(interaction.objects);
    }
  }, [interaction?.objects]);
  
  // Obtener estado de manos
  const handStates = useMemo(() => {
    if (!interaction?.hands) return {};
    return interaction.hands;
  }, [interaction?.hands]);
  
  // IDs de objetos seleccionados/hover
  const selectedIds = useMemo(() => {
    const ids = new Set();
    Object.values(handStates).forEach(hand => {
      if (hand.selected) ids.add(hand.selected);
    });
    return ids;
  }, [handStates]);
  
  const hoveredIds = useMemo(() => {
    const ids = new Set();
    Object.values(handStates).forEach(hand => {
      if (hand.hovered && !selectedIds.has(hand.hovered)) {
        ids.add(hand.hovered);
      }
    });
    return ids;
  }, [handStates, selectedIds]);
  
  return (
    <div className="interaction-demo">
      {/* Controles */}
      <div className="demo-controls">
        <button 
          className={`demo-btn ${demoActive ? 'active' : ''}`}
          onClick={demoActive ? clearDemoObjects : addDemoObjects}
          disabled={!isConnected}
        >
          {demoActive ? '🗑️ Limpiar Demo' : '🎮 Iniciar Demo'}
        </button>
        
        <div className="demo-status">
          <span className={`status-dot ${isConnected ? 'connected' : ''}`} />
          {isConnected ? 'Conectado' : 'Desconectado'}
        </div>
      </div>
      
      {/* Área de demo */}
      <div 
        className="demo-canvas"
        style={{ 
          width, 
          height, 
          position: 'relative',
          background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
          borderRadius: 16,
          overflow: 'hidden',
          border: '2px solid rgba(0, 212, 255, 0.3)'
        }}
      >
        {/* Grid de fondo */}
        <div 
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundImage: `
              linear-gradient(rgba(0, 212, 255, 0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(0, 212, 255, 0.1) 1px, transparent 1px)
            `,
            backgroundSize: '40px 40px',
            pointerEvents: 'none'
          }}
        />
        
        {/* Objetos de demo */}
        <AnimatePresence>
          {demoObjects.map(obj => (
            <DemoShape
              key={obj.id}
              object={obj}
              isSelected={selectedIds.has(obj.id)}
              isHovered={hoveredIds.has(obj.id)}
              canvasScale={{ x: width / 640, y: height / 480 }}
            />
          ))}
        </AnimatePresence>
        
        {/* Cursores de manos */}
        {Object.entries(handStates).map(([handName, handState]) => {
          // Escalar posición de 640x480 (resolución Kinect) al tamaño del canvas
          const scaleX = width / 640;
          const scaleY = height / 480;
          const scaledPosition = [
            (handState.position?.[0] || 0) * scaleX,
            (handState.position?.[1] || 0) * scaleY
          ];
          
          return (
            <HandCursor
              key={handName}
              hand={handName}
              position={scaledPosition}
              gesture={handState.gesture}
              isActive={handState.state !== 'idle'}
              state={handState.state}
            />
          );
        })}
        
        {/* Mensaje cuando no hay objetos */}
        {!demoActive && demoObjects.length === 0 && (
          <div className="demo-placeholder">
            <div className="placeholder-icon">🎮</div>
            <p>Haz clic en "Iniciar Demo" para agregar figuras</p>
            <p className="placeholder-hint">
              Usa 🖐️ para seleccionar y ✊ para arrastrar
            </p>
          </div>
        )}
        
        {/* Estado de interacción */}
        {demoActive && (
          <div className="demo-state-indicator">
            <div className="demo-mode-badge">
              🎮 DEMO {interaction?.mirror_enabled ? '🪞' : ''}
            </div>
            {Object.entries(handStates).map(([handName, handState]) => (
              <div key={handName} className="hand-state">
                <span>{handName === 'Left' ? '👈' : '👉'}</span>
                <span className={`state-badge state-${handState.state}`}>
                  {handState.state}
                </span>
                <span className="gesture-label">
                  {handState.gesture === 'closed_fist' ? '✊' : handState.gesture === 'open_palm' ? '🖐️' : '✋'}
                </span>
                {handState.selected && (
                  <span className="selected-indicator">📦</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      
      {/* Instrucciones */}
      <InstructionsPanel />
    </div>
  );
}
