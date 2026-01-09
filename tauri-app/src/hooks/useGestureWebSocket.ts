/**
 * Custom Hook para conexión WebSocket con el servidor de gestos
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type { GestureData, GestureUpdate, ConnectionStatus } from '../types/gesture.types';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8765';
const RECONNECT_INTERVAL = 3000; // 3 segundos

export interface UseGestureWebSocketReturn {
  gestures: GestureData[];
  fps: number;
  connectionStatus: ConnectionStatus;
  reconnect: () => void;
}

export function useGestureWebSocket(): UseGestureWebSocketReturn {
  const [gestures, setGestures] = useState<GestureData[]>([]);
  const [fps, setFps] = useState<number>(0);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    connected: false,
  });
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef<boolean>(true);

  const connect = useCallback(() => {
    // Limpiar timeout anterior
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    try {
      console.log(`Conectando a WebSocket: ${WS_URL}`);
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket conectado');
        setConnectionStatus({ connected: true });
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'gesture_update') {
            const update = data as GestureUpdate;
            setGestures(update.gestures);
            setFps(update.fps);
          } else if (data.type === 'connected') {
            console.log('Mensaje de bienvenida:', data.message);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus({
          connected: false,
          error: 'Error de conexión con el servidor',
        });
      };

      ws.onclose = () => {
        console.log('WebSocket cerrado');
        setConnectionStatus({
          connected: false,
          error: 'Desconectado del servidor',
        });
        
        wsRef.current = null;

        // Intentar reconectar si está habilitado
        if (shouldReconnectRef.current) {
          console.log(`Reconectando en ${RECONNECT_INTERVAL}ms...`);
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, RECONNECT_INTERVAL);
        }
      };
    } catch (error) {
      console.error('Error creando WebSocket:', error);
      setConnectionStatus({
        connected: false,
        error: 'No se pudo conectar al servidor',
      });
    }
  }, []);

  const reconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    connect();
  }, [connect]);

  useEffect(() => {
    shouldReconnectRef.current = true;
    connect();

    // Cleanup al desmontar
    return () => {
      shouldReconnectRef.current = false;
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    gestures,
    fps,
    connectionStatus,
    reconnect,
  };
}
