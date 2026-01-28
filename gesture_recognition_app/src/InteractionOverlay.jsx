import { useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * InteractionOverlay - Overlay visual para mostrar interacciones
 * 
 * Muestra:
 * - Cursores de manos con estado
 * - Bounding boxes de objetos con estado (hover, selected)
 * - Líneas de conexión mano-objeto
 * - Indicadores de gesto activo
 * - Efectos visuales de arrastre
 */

// Colores por estado
const STATE_COLORS = {
  idle: 'rgba(128, 128, 128, 0.5)',
  hover: 'rgba(59, 130, 246, 0.7)',      // Azul
  selecting: 'rgba(234, 179, 8, 0.7)',    // Amarillo
  selected: 'rgba(34, 197, 94, 0.8)',     // Verde
  dragging: 'rgba(239, 68, 68, 0.8)',     // Rojo
  rotating: 'rgba(168, 85, 247, 0.8)',    // Púrpura
  scaling: 'rgba(236, 72, 153, 0.8)',     // Rosa
  menu: 'rgba(20, 184, 166, 0.8)'         // Teal
};

// Iconos de gestos
const GESTURE_ICONS = {
  open_palm: '🖐️',
  closed_fist: '✊',
  pointing: '👉',
  pinch: '🤏',
  thumbs_up: '👍',
  thumbs_down: '👎',
  peace_sign: '✌️',
  ok_sign: '👌',
  rock: '🤘',
  grab: '🫳',
  unknown: '❓'
};

// Componente de cursor de mano
function HandCursor({ hand, position, state, gesture, isActive }) {
  const color = STATE_COLORS[state] || STATE_COLORS.idle;
  const icon = GESTURE_ICONS[gesture] || GESTURE_ICONS.unknown;
  
  if (!position || (position[0] === 0 && position[1] === 0)) {
    return null;
  }
  
  return (
    <motion.div
      className="hand-cursor"
      initial={{ scale: 0, opacity: 0 }}
      animate={{ 
        scale: isActive ? 1.2 : 1, 
        opacity: 1,
        x: position[0],
        y: position[1]
      }}
      exit={{ scale: 0, opacity: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      style={{
        position: 'absolute',
        left: -20,
        top: -20,
        width: 40,
        height: 40,
        borderRadius: '50%',
        backgroundColor: color,
        border: `3px solid ${state === 'selected' || state === 'dragging' ? '#fff' : 'rgba(255,255,255,0.5)'}`,
        boxShadow: `0 0 20px ${color}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '20px',
        zIndex: 100,
        pointerEvents: 'none'
      }}
    >
      {icon}
      
      {/* Etiqueta de mano */}
      <div
        style={{
          position: 'absolute',
          top: -24,
          left: '50%',
          transform: 'translateX(-50%)',
          backgroundColor: 'rgba(0,0,0,0.8)',
          color: '#fff',
          padding: '2px 8px',
          borderRadius: 4,
          fontSize: 10,
          fontWeight: 'bold',
          whiteSpace: 'nowrap'
        }}
      >
        {hand === 'Left' ? '👈' : '👉'} {state}
      </div>
      
      {/* Anillo de pulso cuando está activo */}
      {(state === 'dragging' || state === 'rotating') && (
        <motion.div
          animate={{
            scale: [1, 1.5, 1],
            opacity: [0.8, 0, 0.8]
          }}
          transition={{
            duration: 1,
            repeat: Infinity,
            ease: 'easeInOut'
          }}
          style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            borderRadius: '50%',
            border: `2px solid ${color}`,
            pointerEvents: 'none'
          }}
        />
      )}
    </motion.div>
  );
}

// Componente de objeto interactivo
function InteractiveObjectOverlay({ object, isSelected, isHovered }) {
  const { bbox, class_name, transformed_bbox, rotation = 0, scale = 1 } = object;
  const box = transformed_bbox || bbox;
  
  if (!box) return null;
  
  const [x, y, width, height] = Array.isArray(box) 
    ? box 
    : [box.x, box.y, box.width, box.height];
  
  let borderColor = 'rgba(255,255,255,0.3)';
  let bgColor = 'transparent';
  
  if (isSelected) {
    borderColor = STATE_COLORS.selected;
    bgColor = 'rgba(34, 197, 94, 0.1)';
  } else if (isHovered) {
    borderColor = STATE_COLORS.hover;
    bgColor = 'rgba(59, 130, 246, 0.1)';
  }
  
  return (
    <motion.div
      className="interactive-object"
      initial={{ opacity: 0 }}
      animate={{ 
        opacity: 1,
        x: x,
        y: y,
        rotate: rotation,
        scale: scale
      }}
      exit={{ opacity: 0 }}
      transition={{ type: 'spring', stiffness: 200, damping: 25 }}
      style={{
        position: 'absolute',
        left: 0,
        top: 0,
        width: width,
        height: height,
        border: `3px solid ${borderColor}`,
        borderRadius: 8,
        backgroundColor: bgColor,
        pointerEvents: 'none',
        transformOrigin: 'center center'
      }}
    >
      {/* Etiqueta del objeto */}
      {(isSelected || isHovered) && (
        <motion.div
          initial={{ y: -10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          style={{
            position: 'absolute',
            top: -28,
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: isSelected ? STATE_COLORS.selected : STATE_COLORS.hover,
            color: '#fff',
            padding: '4px 12px',
            borderRadius: 12,
            fontSize: 12,
            fontWeight: 'bold',
            whiteSpace: 'nowrap',
            boxShadow: '0 2px 8px rgba(0,0,0,0.3)'
          }}
        >
          {class_name} {isSelected ? '✓' : ''}
        </motion.div>
      )}
      
      {/* Esquinas destacadas cuando está seleccionado */}
      {isSelected && (
        <>
          <div className="corner corner-tl" style={cornerStyle('tl')} />
          <div className="corner corner-tr" style={cornerStyle('tr')} />
          <div className="corner corner-bl" style={cornerStyle('bl')} />
          <div className="corner corner-br" style={cornerStyle('br')} />
        </>
      )}
    </motion.div>
  );
}

// Estilo de esquinas
const cornerStyle = (position) => {
  const base = {
    position: 'absolute',
    width: 12,
    height: 12,
    borderColor: STATE_COLORS.selected,
    borderStyle: 'solid',
    borderWidth: 0
  };
  
  switch (position) {
    case 'tl':
      return { ...base, top: -2, left: -2, borderTopWidth: 3, borderLeftWidth: 3, borderTopLeftRadius: 6 };
    case 'tr':
      return { ...base, top: -2, right: -2, borderTopWidth: 3, borderRightWidth: 3, borderTopRightRadius: 6 };
    case 'bl':
      return { ...base, bottom: -2, left: -2, borderBottomWidth: 3, borderLeftWidth: 3, borderBottomLeftRadius: 6 };
    case 'br':
      return { ...base, bottom: -2, right: -2, borderBottomWidth: 3, borderRightWidth: 3, borderBottomRightRadius: 6 };
    default:
      return base;
  }
};

// Línea de conexión mano-objeto
function ConnectionLine({ start, end, color = 'rgba(255,255,255,0.4)' }) {
  if (!start || !end) return null;
  
  const [x1, y1] = start;
  const [x2, y2] = end;
  
  return (
    <svg
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 50
      }}
    >
      <motion.line
        x1={x1}
        y1={y1}
        x2={x2}
        y2={y2}
        stroke={color}
        strokeWidth={2}
        strokeDasharray="5,5"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        exit={{ opacity: 0 }}
      />
    </svg>
  );
}

// Panel de estado de interacción
function InteractionStatusPanel({ interaction, visible = true }) {
  if (!visible || !interaction) return null;
  
  const { hands, selected_count, hovered_count } = interaction;
  
  return (
    <motion.div
      className="interaction-status-panel"
      initial={{ x: 100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 100, opacity: 0 }}
      style={{
        position: 'absolute',
        top: 10,
        right: 10,
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        backdropFilter: 'blur(10px)',
        borderRadius: 12,
        padding: 12,
        minWidth: 180,
        zIndex: 200,
        border: '1px solid rgba(255,255,255,0.1)'
      }}
    >
      <div style={{ fontSize: 12, fontWeight: 'bold', marginBottom: 8, color: '#94a3b8' }}>
        🎮 Interacción
      </div>
      
      {/* Estado de manos */}
      {Object.entries(hands || {}).map(([hand, state]) => (
        <div 
          key={hand}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 6,
            padding: '4px 8px',
            backgroundColor: 'rgba(255,255,255,0.05)',
            borderRadius: 6
          }}
        >
          <span style={{ color: '#e2e8f0' }}>
            {hand === 'Left' ? '👈' : '👉'} {hand}
          </span>
          <span 
            style={{ 
              fontSize: 10, 
              padding: '2px 6px',
              borderRadius: 4,
              backgroundColor: STATE_COLORS[state?.state] || STATE_COLORS.idle,
              color: '#fff'
            }}
          >
            {state?.state || 'idle'}
          </span>
        </div>
      ))}
      
      {/* Contadores */}
      <div style={{ 
        marginTop: 8, 
        paddingTop: 8, 
        borderTop: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        gap: 12
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 16, fontWeight: 'bold', color: STATE_COLORS.selected }}>
            {selected_count || 0}
          </div>
          <div style={{ fontSize: 10, color: '#94a3b8' }}>Seleccionados</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 16, fontWeight: 'bold', color: STATE_COLORS.hover }}>
            {hovered_count || 0}
          </div>
          <div style={{ fontSize: 10, color: '#94a3b8' }}>Hover</div>
        </div>
      </div>
    </motion.div>
  );
}

// Notificación de evento
function EventNotification({ event }) {
  if (!event) return null;
  
  const getEventIcon = (type) => {
    const icons = {
      select: '✅',
      deselect: '❌',
      hover_start: '👁️',
      hover_end: '👁️‍🗨️',
      drag_start: '🚀',
      drag_move: '↔️',
      drag_end: '🎯',
      rotate_start: '🔄',
      rotate_end: '🔄',
      confirm: '✅',
      cancel: '❌'
    };
    return icons[type] || '📢';
  };
  
  return (
    <motion.div
      initial={{ y: 20, opacity: 0, scale: 0.8 }}
      animate={{ y: 0, opacity: 1, scale: 1 }}
      exit={{ y: -20, opacity: 0, scale: 0.8 }}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        padding: '8px 12px',
        borderRadius: 8,
        marginBottom: 4,
        border: '1px solid rgba(255,255,255,0.1)'
      }}
    >
      <span style={{ fontSize: 16 }}>{getEventIcon(event.type)}</span>
      <span style={{ fontSize: 12, color: '#e2e8f0' }}>{event.type}</span>
      {event.object_id && (
        <span style={{ fontSize: 10, color: '#94a3b8' }}>
          ID: {event.object_id}
        </span>
      )}
    </motion.div>
  );
}

// Componente principal
export default function InteractionOverlay({ 
  interaction,
  objects = [],
  hands = [],
  width = 640,
  height = 480,
  showCursors = true,
  showObjectOverlays = true,
  showConnections = true,
  showStatusPanel = true,
  showEvents = true
}) {
  // Procesar datos de interacción
  const handStates = useMemo(() => {
    if (!interaction?.hands) return {};
    return interaction.hands;
  }, [interaction]);
  
  // Obtener objetos con estado
  const objectsWithState = useMemo(() => {
    const selectedIds = new Set();
    const hoveredIds = new Set();
    
    // Desde estado de manos
    Object.values(handStates).forEach(hand => {
      if (hand.selected) selectedIds.add(hand.selected);
      if (hand.hovered) hoveredIds.add(hand.hovered);
    });
    
    return objects.map((obj, index) => ({
      ...obj,
      id: obj.id || index,
      isSelected: selectedIds.has(obj.id || index),
      isHovered: hoveredIds.has(obj.id || index) && !selectedIds.has(obj.id || index)
    }));
  }, [objects, handStates]);
  
  // Eventos recientes
  const recentEvents = useMemo(() => {
    return interaction?.events?.slice(-3) || [];
  }, [interaction?.events]);
  
  return (
    <div 
      className="interaction-overlay"
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: width,
        height: height,
        pointerEvents: 'none',
        overflow: 'hidden'
      }}
    >
      {/* Overlays de objetos */}
      {showObjectOverlays && (
        <AnimatePresence>
          {objectsWithState.map(obj => (
            <InteractiveObjectOverlay
              key={obj.id}
              object={obj}
              isSelected={obj.isSelected}
              isHovered={obj.isHovered}
            />
          ))}
        </AnimatePresence>
      )}
      
      {/* Líneas de conexión */}
      {showConnections && Object.entries(handStates).map(([hand, state]) => {
        if (!state.selected || !state.position) return null;
        
        const selectedObj = objectsWithState.find(o => o.id === state.selected);
        if (!selectedObj) return null;
        
        const objCenter = selectedObj.center 
          ? [selectedObj.center.x, selectedObj.center.y]
          : null;
        
        return objCenter && (
          <ConnectionLine
            key={`conn-${hand}`}
            start={state.position}
            end={objCenter}
            color={STATE_COLORS[state.state]}
          />
        );
      })}
      
      {/* Cursores de manos */}
      {showCursors && (
        <AnimatePresence>
          {Object.entries(handStates).map(([hand, state]) => (
            <HandCursor
              key={hand}
              hand={hand}
              position={state.position}
              state={state.state}
              gesture={state.gesture}
              isActive={state.state !== 'idle'}
            />
          ))}
        </AnimatePresence>
      )}
      
      {/* Panel de estado */}
      {showStatusPanel && (
        <InteractionStatusPanel 
          interaction={interaction}
          visible={true}
        />
      )}
      
      {/* Notificaciones de eventos */}
      {showEvents && recentEvents.length > 0 && (
        <div
          style={{
            position: 'absolute',
            bottom: 10,
            left: 10,
            zIndex: 200
          }}
        >
          <AnimatePresence mode="popLayout">
            {recentEvents.map((event, idx) => (
              <EventNotification 
                key={`${event.type}-${event.timestamp}-${idx}`}
                event={event}
              />
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
