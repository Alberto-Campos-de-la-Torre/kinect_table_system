import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Grid, Text, Html } from '@react-three/drei';
import * as THREE from 'three';

/**
 * InteractionDemo3D - Demo de interacciones en 3D
 * 
 * Usa Three.js para renderizar objetos 3D que se pueden manipular con gestos.
 * La profundidad de la mano controla la posición Z del objeto.
 */

// Colores para las figuras
const SHAPE_COLORS = {
  cube: '#ef4444',
  sphere: '#22c55e',
  cylinder: '#3b82f6',
  cone: '#eab308',
  torus: '#a855f7',
  dodecahedron: '#f97316'
};

// Figura 3D interactiva
function InteractiveShape3D({ 
  id, 
  type, 
  position, 
  color, 
  isSelected, 
  isHovered,
  scale = 1 
}) {
  const meshRef = useRef();
  const [hoverLocal, setHoverLocal] = useState(false);
  
  // Animación de flotación
  useFrame((state) => {
    if (meshRef.current) {
      // Rotación suave
      if (isSelected) {
        meshRef.current.rotation.y += 0.02;
      }
      // Efecto de flotación
      if (isHovered || isSelected) {
        meshRef.current.position.y = position[1] + Math.sin(state.clock.elapsedTime * 3) * 0.02;
      }
    }
  });
  
  // Geometría según tipo
  const geometry = useMemo(() => {
    switch (type) {
      case 'sphere':
        return <sphereGeometry args={[0.08, 32, 32]} />;
      case 'cylinder':
        return <cylinderGeometry args={[0.06, 0.06, 0.12, 32]} />;
      case 'cone':
        return <coneGeometry args={[0.07, 0.14, 32]} />;
      case 'torus':
        return <torusGeometry args={[0.06, 0.025, 16, 32]} />;
      case 'dodecahedron':
        return <dodecahedronGeometry args={[0.07]} />;
      default: // cube
        return <boxGeometry args={[0.1, 0.1, 0.1]} />;
    }
  }, [type]);
  
  // Color del material
  const materialColor = isSelected ? '#00ff00' : isHovered ? '#00aaff' : color;
  const emissiveIntensity = isSelected ? 0.5 : isHovered ? 0.3 : 0.1;
  
  return (
    <mesh
      ref={meshRef}
      position={position}
      scale={scale}
      onPointerOver={() => setHoverLocal(true)}
      onPointerOut={() => setHoverLocal(false)}
    >
      {geometry}
      <meshStandardMaterial 
        color={materialColor}
        emissive={materialColor}
        emissiveIntensity={emissiveIntensity}
        metalness={0.3}
        roughness={0.4}
      />
      
      {/* Etiqueta cuando está seleccionado */}
      {isSelected && (
        <Html position={[0, 0.15, 0]} center>
          <div style={{
            background: 'rgba(34, 197, 94, 0.9)',
            color: 'white',
            padding: '4px 8px',
            borderRadius: '12px',
            fontSize: '10px',
            fontWeight: 'bold',
            whiteSpace: 'nowrap'
          }}>
            ✓ Seleccionado
          </div>
        </Html>
      )}
    </mesh>
  );
}

// Cursor 3D de la mano (vista aérea)
function HandCursor3D({ position, gesture, isActive, hand }) {
  const groupRef = useRef();
  const meshRef = useRef();
  
  useFrame((state) => {
    if (meshRef.current) {
      // Pulso cuando está activo (arrastrando)
      if (isActive && gesture === 'closed_fist') {
        const pulse = 1 + Math.sin(state.clock.elapsedTime * 8) * 0.15;
        meshRef.current.scale.setScalar(pulse);
      } else {
        meshRef.current.scale.setScalar(1);
      }
    }
  });
  
  const color = gesture === 'closed_fist' 
    ? '#ef4444' 
    : gesture === 'open_palm' 
      ? '#22c55e' 
      : '#666666';
  
  const isDragging = isActive && gesture === 'closed_fist';
  
  return (
    <group ref={groupRef} position={position}>
      {/* Sombra proyectada en el suelo */}
      <mesh position={[0, -position[1] + 0.001, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.03 + position[1] * 0.05, 16]} />
        <meshBasicMaterial color="#000000" transparent opacity={0.3} />
      </mesh>
      
      {/* Línea vertical al suelo */}
      <mesh position={[0, -position[1] / 2, 0]}>
        <cylinderGeometry args={[0.003, 0.003, position[1], 8]} />
        <meshBasicMaterial color={color} transparent opacity={0.4} />
      </mesh>
      
      {/* Esfera principal del cursor */}
      <mesh ref={meshRef}>
        <sphereGeometry args={[isDragging ? 0.035 : 0.025, 16, 16]} />
        <meshStandardMaterial 
          color={color}
          emissive={color}
          emissiveIntensity={isDragging ? 1.0 : 0.5}
          transparent
          opacity={0.9}
        />
      </mesh>
      
      {/* Anillo horizontal */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[isDragging ? 0.05 : 0.04, 0.004, 8, 24]} />
        <meshBasicMaterial color={color} transparent opacity={0.6} />
      </mesh>
      
      {/* Etiqueta flotante */}
      <Html position={[0, 0.06, 0]} center>
        <div style={{
          background: color,
          color: 'white',
          padding: '3px 8px',
          borderRadius: '10px',
          fontSize: '10px',
          fontWeight: 'bold',
          boxShadow: isDragging ? `0 0 10px ${color}` : 'none',
          whiteSpace: 'nowrap'
        }}>
          {hand === 'Left' ? 'L' : 'R'} {gesture === 'closed_fist' ? '✊' : '🖐️'}
        </div>
      </Html>
    </group>
  );
}

// Plano de la mesa
function TablePlane() {
  return (
    <>
      {/* Plano semi-transparente */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
        <planeGeometry args={[2, 2]} />
        <meshStandardMaterial 
          color="#1a1a2e"
          transparent
          opacity={0.5}
          side={THREE.DoubleSide}
        />
      </mesh>
      
      {/* Grid */}
      <Grid 
        args={[2, 2]}
        cellSize={0.1}
        cellThickness={0.5}
        cellColor="#00d4ff"
        sectionSize={0.5}
        sectionThickness={1}
        sectionColor="#0088ff"
        fadeDistance={5}
        fadeStrength={1}
        followCamera={false}
        position={[0, 0, 0]}
      />
    </>
  );
}

// Escena 3D con vista aérea
function Scene3D({ objects, handStates, selectedIds, hoveredIds }) {
  return (
    <>
      {/* Iluminación */}
      <ambientLight intensity={0.5} />
      <directionalLight position={[0, 10, 0]} intensity={0.8} castShadow />
      <pointLight position={[0.5, 0.5, 0.5]} intensity={0.4} color="#00d4ff" />
      <pointLight position={[-0.5, 0.5, -0.5]} intensity={0.3} color="#ff00ff" />
      
      {/* Mesa */}
      <TablePlane />
      
      {/* Objetos 3D */}
      {objects.map((obj) => (
        <InteractiveShape3D
          key={obj.id}
          id={obj.id}
          type={obj.shape_type || 'cube'}
          position={obj.position_3d || [0, 0.08, 0]}
          color={obj.color || SHAPE_COLORS.cube}
          isSelected={selectedIds.has(obj.id)}
          isHovered={hoveredIds.has(obj.id)}
          scale={obj.scale || 1}
        />
      ))}
      
      {/* Cursores de manos */}
      {Object.entries(handStates).map(([handName, state]) => {
        // Posición 3D ya viene mapeada correctamente del backend
        // X = horizontal, Y = altura (profundidad de mano), Z = vertical en cámara
        const pos3d = state.position_3d || [0, 0.2, 0];
        return (
          <HandCursor3D
            key={handName}
            hand={handName}
            position={pos3d}
            gesture={state.gesture}
            isActive={state.state !== 'idle'}
          />
        );
      })}
      
      {/* Controles de cámara - Vista aérea por defecto */}
      <OrbitControls 
        enablePan={true}
        enableZoom={true}
        enableRotate={true}
        minDistance={0.3}
        maxDistance={2}
        target={[0, 0, 0]}
        maxPolarAngle={Math.PI / 2.5}  // Limitar para mantener vista semi-aérea
      />
    </>
  );
}

// Panel de instrucciones 3D (Sensor arriba mirando abajo)
function Instructions3DPanel() {
  return (
    <div className="demo-instructions-3d">
      <h4>🎮 Controles 3D (Sensor Arriba)</h4>
      <div className="instruction-row">
        <span>🖐️</span>
        <span>Palma abierta: Seleccionar</span>
      </div>
      <div className="instruction-row">
        <span>✊</span>
        <span>Puño cerrado: Arrastrar</span>
      </div>
      <div className="instruction-row">
        <span>↔️</span>
        <span>Mano izq/der → Objeto izq/der (X)</span>
      </div>
      <div className="instruction-row">
        <span>↕️</span>
        <span>Mano adelante/atrás → Objeto cerca/lejos (Z)</span>
      </div>
      <div className="instruction-row">
        <span>🤚</span>
        <span>Levantar mano → Objeto sube (Y)</span>
      </div>
    </div>
  );
}

// Componente principal
export default function InteractionDemo3D({
  ws,
  isConnected,
  interaction,
  hands = [],
  width = 640,
  height = 480
}) {
  const [demoObjects, setDemoObjects] = useState([]);
  const [demoActive, setDemoActive] = useState(false);
  
  // Agregar objetos de demo 3D
  const addDemo3DObjects = useCallback(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'add_demo_objects_3d' }));
      setDemoActive(true);
    }
  }, [ws]);
  
  // Limpiar objetos
  const clearDemoObjects = useCallback(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'clear_demo_objects' }));
      setDemoActive(false);
      setDemoObjects([]);
    }
  }, [ws]);
  
  // Procesar objetos desde interacción
  useEffect(() => {
    if (interaction?.objects) {
      // Convertir objetos 2D a 3D si es necesario
      const objects3d = interaction.objects.map(obj => ({
        ...obj,
        position_3d: obj.position_3d || [
          (obj.center?.[0] || obj.bbox?.[0] || 320) / 640 - 0.5,  // X: -0.5 a 0.5
          0.1,  // Y: altura fija
          (obj.center?.[1] || obj.bbox?.[1] || 240) / 480 * 0.5   // Z: 0 a 0.5
        ],
        shape_type: getShapeType(obj.class_name),
        color: getShapeColor(obj.class_name)
      }));
      setDemoObjects(objects3d);
    }
  }, [interaction?.objects]);
  
  // Determinar tipo de forma 3D
  const getShapeType = (className) => {
    if (className?.includes('Círculo')) return 'sphere';
    if (className?.includes('Cuadrado')) return 'cube';
    if (className?.includes('Triángulo')) return 'cone';
    if (className?.includes('Estrella')) return 'dodecahedron';
    if (className?.includes('Diamante')) return 'torus';
    if (className?.includes('Hexágono')) return 'cylinder';
    return 'cube';
  };
  
  // Obtener color
  const getShapeColor = (className) => {
    if (className?.includes('Rojo')) return SHAPE_COLORS.cube;
    if (className?.includes('Verde')) return SHAPE_COLORS.sphere;
    if (className?.includes('Azul')) return SHAPE_COLORS.cylinder;
    if (className?.includes('Amarilla')) return SHAPE_COLORS.cone;
    if (className?.includes('Púrpura')) return SHAPE_COLORS.torus;
    if (className?.includes('Naranja')) return SHAPE_COLORS.dodecahedron;
    return '#888888';
  };
  
  // Estado de manos
  const handStates = useMemo(() => {
    if (!interaction?.hands) return {};
    return interaction.hands;
  }, [interaction?.hands]);
  
  // IDs seleccionados/hover
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
    <div className="interaction-demo-3d">
      {/* Controles */}
      <div className="demo-controls-3d">
        <button
          className={`demo-btn-3d ${demoActive ? 'active' : ''}`}
          onClick={demoActive ? clearDemoObjects : addDemo3DObjects}
          disabled={!isConnected}
        >
          {demoActive ? '🗑️ Limpiar 3D' : '🎮 Iniciar 3D'}
        </button>
        
        <div className="demo-status-3d">
          <span className={`status-dot ${isConnected ? 'connected' : ''}`} />
          {isConnected ? 'Conectado' : 'Desconectado'}
        </div>
        
        {demoActive && (
          <div className="demo-info-3d">
            <span>📦 {demoObjects.length} objetos</span>
            <span>🎯 {selectedIds.size} seleccionados</span>
          </div>
        )}
      </div>
      
      {/* Canvas 3D - Vista aérea */}
      <div className="canvas-container-3d" style={{ width, height }}>
        <Canvas
          camera={{ position: [0, 0.8, 0.4], fov: 50 }}
          style={{ background: 'linear-gradient(180deg, #0a0e27 0%, #1a1a2e 100%)' }}
        >
          <Scene3D
            objects={demoObjects}
            handStates={handStates}
            selectedIds={selectedIds}
            hoveredIds={hoveredIds}
          />
        </Canvas>
        
        {/* Placeholder cuando no hay demo */}
        {!demoActive && demoObjects.length === 0 && (
          <div className="demo-placeholder-3d">
            <div className="placeholder-icon-3d">🎮</div>
            <p>Haz clic en "Iniciar 3D" para comenzar</p>
            <p className="hint">Los objetos se moverán en 3D con tu mano</p>
          </div>
        )}
      </div>
      
      {/* Instrucciones */}
      <Instructions3DPanel />
    </div>
  );
}
