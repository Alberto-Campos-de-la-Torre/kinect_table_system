/**
 * PointCloudViewer - Visualizador de Nube de Puntos 3D
 * =====================================================
 * Renderiza nubes de puntos del Kinect usando Three.js
 */

import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import pako from 'pako';

// Decodificar datos binarios de nube de puntos
function decodePointCloud(data) {
  if (!data || data.num_points === 0) {
    return { points: null, colors: null, numPoints: 0 };
  }

  try {
    // Decodificar base64
    const binaryString = atob(data.data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    // Descomprimir si es necesario
    let rawData;
    if (data.compressed) {
      rawData = pako.inflate(bytes);
    } else {
      rawData = bytes;
    }

    // Parsear header
    const view = new DataView(rawData.buffer);
    const numPoints = view.getUint32(0, true);
    const hasColors = view.getUint8(4) === 1;
    let offset = 5;

    let points;

    // Parsear puntos
    if (data.quantized) {
      // Leer bounds (6 floats = 24 bytes)
      const minX = view.getFloat32(offset, true);
      const minY = view.getFloat32(offset + 4, true);
      const minZ = view.getFloat32(offset + 8, true);
      const rangeX = view.getFloat32(offset + 12, true);
      const rangeY = view.getFloat32(offset + 16, true);
      const rangeZ = view.getFloat32(offset + 20, true);
      offset += 24;

      // Leer puntos cuantizados (uint16)
      const pointsArray = new Float32Array(numPoints * 3);
      const maxVal = 65535;

      for (let i = 0; i < numPoints; i++) {
        const qx = view.getUint16(offset, true);
        const qy = view.getUint16(offset + 2, true);
        const qz = view.getUint16(offset + 4, true);
        offset += 6;

        pointsArray[i * 3] = (qx / maxVal) * rangeX + minX;
        pointsArray[i * 3 + 1] = (qy / maxVal) * rangeY + minY;
        pointsArray[i * 3 + 2] = (qz / maxVal) * rangeZ + minZ;
      }
      points = pointsArray;
    } else {
      // Leer puntos float32
      points = new Float32Array(rawData.buffer, offset, numPoints * 3);
      offset += numPoints * 3 * 4;
    }

    // Parsear colores
    let colors = null;
    if (hasColors) {
      const colorsArray = new Float32Array(numPoints * 3);
      for (let i = 0; i < numPoints * 3; i++) {
        colorsArray[i] = rawData[offset + i] / 255;
      }
      colors = colorsArray;
    }

    return { points, colors, numPoints };
  } catch (error) {
    console.error('Error decodificando nube de puntos:', error);
    return { points: null, colors: null, numPoints: 0 };
  }
}

// Crear textura circular para los puntos
function createCircleTexture() {
  const size = 64;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  
  // Dibujar círculo con gradiente suave
  const gradient = ctx.createRadialGradient(
    size / 2, size / 2, 0,
    size / 2, size / 2, size / 2
  );
  gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
  gradient.addColorStop(0.5, 'rgba(255, 255, 255, 0.8)');
  gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
  
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);
  
  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}

// Componente principal
export default function PointCloudViewer({ 
  pointcloudData, 
  width = 800, 
  height = 600,
  backgroundColor = 0x1a1a2e,
  pointSize = 0.5,
  showAxes = true,
  showGrid = true
}) {
  const containerRef = useRef(null);
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const controlsRef = useRef(null);
  const pointsRef = useRef(null);
  const frameIdRef = useRef(null);
  
  const [stats, setStats] = useState({
    numPoints: 0,
    fps: 0,
    lastUpdate: Date.now()
  });
  
  const [currentPointSize, setCurrentPointSize] = useState(pointSize);
  const [maxDisplayPoints, setMaxDisplayPoints] = useState(30000); // Máximo de puntos a mostrar

  // Inicializar Three.js
  useEffect(() => {
    if (!containerRef.current) return;

    // Escena
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(backgroundColor);
    sceneRef.current = scene;

    // Cámara
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 100);
    camera.position.set(0, -2, 3);
    camera.lookAt(0, 0, 2);
    cameraRef.current = camera;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Controles de órbita
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.target.set(0, 0, 2);
    controls.update();
    controlsRef.current = controls;

    // Ejes de referencia
    if (showAxes) {
      const axesHelper = new THREE.AxesHelper(1);
      scene.add(axesHelper);
    }

    // Grid de referencia
    if (showGrid) {
      const gridHelper = new THREE.GridHelper(4, 20, 0x444444, 0x222222);
      gridHelper.rotation.x = Math.PI / 2;
      gridHelper.position.z = 2;
      scene.add(gridHelper);
    }

    // Luz ambiental
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);

    // Crear geometría inicial para puntos
    const geometry = new THREE.BufferGeometry();
    
    // Crear textura circular para puntos suaves
    const circleTexture = createCircleTexture();
    
    const material = new THREE.PointsMaterial({
      size: pointSize,
      vertexColors: true,
      sizeAttenuation: true,
      map: circleTexture,
      alphaTest: 0.1,
      transparent: true,
      depthWrite: false
    });
    const points = new THREE.Points(geometry, material);
    scene.add(points);
    pointsRef.current = points;

    // Loop de animación
    let lastTime = performance.now();
    let frameCount = 0;

    const animate = () => {
      frameIdRef.current = requestAnimationFrame(animate);
      
      // Calcular FPS
      frameCount++;
      const currentTime = performance.now();
      if (currentTime - lastTime >= 1000) {
        setStats(prev => ({
          ...prev,
          fps: Math.round(frameCount * 1000 / (currentTime - lastTime))
        }));
        frameCount = 0;
        lastTime = currentTime;
      }

      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Cleanup
    return () => {
      if (frameIdRef.current) {
        cancelAnimationFrame(frameIdRef.current);
      }
      if (containerRef.current && renderer.domElement) {
        containerRef.current.removeChild(renderer.domElement);
      }
      renderer.dispose();
      geometry.dispose();
      material.dispose();
      circleTexture.dispose();
    };
  }, [width, height, backgroundColor, pointSize, showAxes, showGrid]);

  // Actualizar nube de puntos cuando lleguen nuevos datos
  useEffect(() => {
    if (!pointcloudData || !pointsRef.current) return;

    let { points, colors, numPoints } = decodePointCloud(pointcloudData);
    
    if (!points || numPoints === 0) return;

    // Limitar número de puntos mostrados si es necesario
    let displayedPoints = numPoints;
    if (numPoints > maxDisplayPoints) {
      // Submuestrear uniformemente
      const step = Math.ceil(numPoints / maxDisplayPoints);
      const newNumPoints = Math.floor(numPoints / step);
      const newPoints = new Float32Array(newNumPoints * 3);
      const newColors = colors ? new Float32Array(newNumPoints * 3) : null;
      
      for (let i = 0, j = 0; i < numPoints && j < newNumPoints; i += step, j++) {
        newPoints[j * 3] = points[i * 3];
        newPoints[j * 3 + 1] = points[i * 3 + 1];
        newPoints[j * 3 + 2] = points[i * 3 + 2];
        if (colors) {
          newColors[j * 3] = colors[i * 3];
          newColors[j * 3 + 1] = colors[i * 3 + 1];
          newColors[j * 3 + 2] = colors[i * 3 + 2];
        }
      }
      
      points = newPoints;
      colors = newColors;
      displayedPoints = newNumPoints;
    }

    const geometry = pointsRef.current.geometry;

    // Actualizar posiciones
    geometry.setAttribute('position', new THREE.BufferAttribute(points, 3));

    // Actualizar colores
    if (colors) {
      geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    } else {
      // Color por defecto basado en profundidad (Z)
      const defaultColors = new Float32Array(displayedPoints * 3);
      for (let i = 0; i < displayedPoints; i++) {
        const z = points[i * 3 + 2];
        const t = Math.min(1, Math.max(0, (z - 0.5) / 4)); // Normalizar Z
        
        // Colormap tipo "turbo"
        defaultColors[i * 3] = Math.sin(t * Math.PI) * 0.5 + 0.5;     // R
        defaultColors[i * 3 + 1] = Math.sin(t * Math.PI + 2) * 0.5 + 0.5; // G
        defaultColors[i * 3 + 2] = Math.sin(t * Math.PI + 4) * 0.5 + 0.5; // B
      }
      geometry.setAttribute('color', new THREE.BufferAttribute(defaultColors, 3));
    }

    geometry.computeBoundingSphere();
    geometry.attributes.position.needsUpdate = true;
    geometry.attributes.color.needsUpdate = true;

    // Actualizar stats
    setStats(prev => ({
      ...prev,
      numPoints: displayedPoints,
      totalPoints: numPoints,
      lastUpdate: Date.now()
    }));

  }, [pointcloudData, maxDisplayPoints]);

  // Manejar resize
  useEffect(() => {
    if (rendererRef.current && cameraRef.current) {
      rendererRef.current.setSize(width, height);
      cameraRef.current.aspect = width / height;
      cameraRef.current.updateProjectionMatrix();
    }
  }, [width, height]);

  // Funciones de control de cámara
  const resetCamera = useCallback(() => {
    if (cameraRef.current && controlsRef.current) {
      cameraRef.current.position.set(0, -2, 3);
      controlsRef.current.target.set(0, 0, 2);
      controlsRef.current.update();
    }
  }, []);

  const setViewTop = useCallback(() => {
    if (cameraRef.current && controlsRef.current) {
      cameraRef.current.position.set(0, 0, 6);
      controlsRef.current.target.set(0, 0, 2);
      controlsRef.current.update();
    }
  }, []);

  const setViewFront = useCallback(() => {
    if (cameraRef.current && controlsRef.current) {
      cameraRef.current.position.set(0, -4, 2);
      controlsRef.current.target.set(0, 0, 2);
      controlsRef.current.update();
    }
  }, []);

  const setViewSide = useCallback(() => {
    if (cameraRef.current && controlsRef.current) {
      cameraRef.current.position.set(4, 0, 2);
      controlsRef.current.target.set(0, 0, 2);
      controlsRef.current.update();
    }
  }, []);

  // Actualizar tamaño de puntos
  const handlePointSizeChange = useCallback((e) => {
    const newSize = parseFloat(e.target.value);
    setCurrentPointSize(newSize);
    if (pointsRef.current) {
      pointsRef.current.material.size = newSize;
    }
  }, []);

  // Actualizar máximo de puntos mostrados
  const handleMaxPointsChange = useCallback((e) => {
    const newMax = parseInt(e.target.value, 10);
    setMaxDisplayPoints(newMax);
  }, []);

  return (
    <div className="pointcloud-viewer" style={{ position: 'relative' }}>
      {/* Canvas container */}
      <div 
        ref={containerRef} 
        style={{ 
          width, 
          height, 
          borderRadius: '12px',
          overflow: 'hidden'
        }} 
      />
      
      {/* Stats overlay */}
      <div style={{
        position: 'absolute',
        top: '10px',
        left: '10px',
        background: 'rgba(0, 0, 0, 0.85)',
        padding: '12px 15px',
        borderRadius: '8px',
        color: 'white',
        fontFamily: 'monospace',
        fontSize: '11px',
        minWidth: '180px'
      }}>
        <div style={{ marginBottom: '4px' }}>
          <span style={{ color: '#00d4ff' }}>Puntos:</span> {stats.numPoints?.toLocaleString() || 0}
          {stats.totalPoints && stats.totalPoints !== stats.numPoints && (
            <span style={{ color: '#888' }}> / {stats.totalPoints.toLocaleString()}</span>
          )}
        </div>
        <div style={{ marginBottom: '8px' }}>
          <span style={{ color: '#00d4ff' }}>FPS:</span> {stats.fps}
        </div>
        
        {/* Slider de tamaño de punto */}
        <div style={{ marginBottom: '10px' }}>
          <label style={{ fontSize: '10px', color: '#aaa' }}>
            Tamaño punto: {currentPointSize.toFixed(2)}
          </label>
          <input 
            type="range" 
            min="0.01" 
            max="5" 
            step="0.01"
            value={currentPointSize}
            onChange={handlePointSizeChange}
            style={{ 
              width: '100%', 
              marginTop: '4px',
              accentColor: '#00d4ff',
              height: '4px'
            }}
          />
        </div>
        
        {/* Slider de máximo de puntos */}
        <div>
          <label style={{ fontSize: '10px', color: '#aaa' }}>
            Máx puntos: {maxDisplayPoints.toLocaleString()}
          </label>
          <input 
            type="range" 
            min="1000" 
            max="100000" 
            step="1000"
            value={maxDisplayPoints}
            onChange={handleMaxPointsChange}
            style={{ 
              width: '100%', 
              marginTop: '4px',
              accentColor: '#ff6b6b',
              height: '4px'
            }}
          />
        </div>
      </div>
      
      {/* Controles de cámara */}
      <div style={{
        position: 'absolute',
        top: '10px',
        right: '10px',
        display: 'flex',
        flexDirection: 'column',
        gap: '5px'
      }}>
        <button onClick={resetCamera} style={buttonStyle}>🔄 Reset</button>
        <button onClick={setViewTop} style={buttonStyle}>⬆️ Top</button>
        <button onClick={setViewFront} style={buttonStyle}>👁️ Front</button>
        <button onClick={setViewSide} style={buttonStyle}>➡️ Side</button>
      </div>
    </div>
  );
}

const buttonStyle = {
  background: 'rgba(0, 212, 255, 0.8)',
  border: 'none',
  borderRadius: '6px',
  padding: '8px 12px',
  color: 'white',
  fontWeight: 'bold',
  cursor: 'pointer',
  fontSize: '11px'
};
