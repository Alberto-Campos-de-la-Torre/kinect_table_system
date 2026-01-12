/**
 * usePointCloud - Hook para manejo de datos de nube de puntos
 * ===========================================================
 */

import { useState, useCallback, useRef } from 'react';

/**
 * Hook para manejar datos de nube de puntos del WebSocket
 */
export function usePointCloud() {
  const [pointcloudData, setPointcloudData] = useState(null);
  const [pointcloudEnabled, setPointcloudEnabled] = useState(true);
  const [colorMode, setColorMode] = useState('rgb');
  const [stats, setStats] = useState({
    numPoints: 0,
    compressedSize: 0,
    compressionRatio: 0,
    encodeTime: 0,
    lastUpdate: null
  });

  const wsRef = useRef(null);

  // Actualizar datos de nube de puntos desde frame del WebSocket
  const updatePointCloud = useCallback((frameData) => {
    if (frameData && frameData.pointcloud) {
      setPointcloudData(frameData.pointcloud);
      
      // Actualizar estadísticas
      if (frameData.pointcloud.stats) {
        setStats({
          numPoints: frameData.pointcloud.num_points || 0,
          compressedSize: frameData.pointcloud.stats.compressed_size || 0,
          compressionRatio: frameData.pointcloud.stats.compression_ratio || 0,
          encodeTime: frameData.pointcloud.stats.encode_time_ms || 0,
          lastUpdate: Date.now()
        });
      }
    }
  }, []);

  // Enviar comando al servidor WebSocket
  const sendCommand = useCallback((ws, type, data = {}) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type, ...data }));
    }
  }, []);

  // Toggle nube de puntos
  const togglePointCloud = useCallback((ws) => {
    sendCommand(ws, 'toggle_pointcloud');
    setPointcloudEnabled(prev => !prev);
  }, [sendCommand]);

  // Cambiar modo de color
  const setPointCloudColorMode = useCallback((ws, mode) => {
    sendCommand(ws, 'set_pointcloud_color_mode', { mode });
    setColorMode(mode);
  }, [sendCommand]);

  // Cambiar factor de downsampling
  const setDownsampleFactor = useCallback((ws, factor) => {
    sendCommand(ws, 'set_pointcloud_downsample', { factor });
  }, [sendCommand]);

  return {
    pointcloudData,
    pointcloudEnabled,
    colorMode,
    stats,
    updatePointCloud,
    togglePointCloud,
    setPointCloudColorMode,
    setDownsampleFactor
  };
}

export default usePointCloud;
