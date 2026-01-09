/**
 * Componente StatsPanel - Panel de estadísticas del sistema
 */

import React from 'react';
import { Activity, TrendingUp, Clock, Zap } from 'lucide-react';
import type { ConnectionStatus } from '../types/gesture.types';

interface StatsPanelProps {
  fps: number;
  connectionStatus: ConnectionStatus;
  gestureCount: number;
}

export const StatsPanel: React.FC<StatsPanelProps> = ({
  fps,
  connectionStatus,
  gestureCount,
}) => {
  const [uptime, setUptime] = React.useState<number>(0);

  React.useEffect(() => {
    const interval = setInterval(() => {
      setUptime((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const formatUptime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours.toString().padStart(2, '0')}:${minutes
      .toString()
      .padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const getFpsColor = (fps: number): string => {
    if (fps >= 25) return 'text-green-500';
    if (fps >= 15) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6 space-y-4">
      <h2 className="text-xl font-bold text-white mb-4">Estadísticas del Sistema</h2>

      {/* Estado de conexión */}
      <div className="flex items-center gap-3 p-4 bg-gray-700 rounded-lg">
        <div
          className={`w-3 h-3 rounded-full ${
            connectionStatus.connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
          }`}
        />
        <div className="flex-1">
          <p className="text-white font-medium">
            {connectionStatus.connected ? 'Conectado' : 'Desconectado'}
          </p>
          {connectionStatus.error && (
            <p className="text-red-400 text-sm">{connectionStatus.error}</p>
          )}
        </div>
      </div>

      {/* Grid de estadísticas */}
      <div className="grid grid-cols-2 gap-4">
        {/* FPS */}
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-5 h-5 text-yellow-500" />
            <span className="text-gray-400 text-sm">FPS</span>
          </div>
          <p className={`text-3xl font-bold ${getFpsColor(fps)}`}>
            {fps.toFixed(1)}
          </p>
        </div>

        {/* Gestos detectados */}
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-5 h-5 text-blue-500" />
            <span className="text-gray-400 text-sm">Gestos</span>
          </div>
          <p className="text-3xl font-bold text-white">{gestureCount}</p>
        </div>

        {/* Tiempo activo */}
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-5 h-5 text-purple-500" />
            <span className="text-gray-400 text-sm">Tiempo Activo</span>
          </div>
          <p className="text-xl font-mono font-bold text-white">
            {formatUptime(uptime)}
          </p>
        </div>

        {/* Performance */}
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-5 h-5 text-green-500" />
            <span className="text-gray-400 text-sm">Performance</span>
          </div>
          <p className="text-xl font-bold text-white">
            {fps >= 25 ? 'Óptimo' : fps >= 15 ? 'Bueno' : 'Bajo'}
          </p>
        </div>
      </div>

      {/* Leyenda de gestos */}
      <div className="bg-gray-700 rounded-lg p-4">
        <h3 className="text-white font-semibold mb-3">Gestos Soportados</h3>
        <div className="grid grid-cols-2 gap-2 text-sm">
          {[
            { name: 'Mano Abierta', color: '#00ff00' },
            { name: 'Puño Cerrado', color: '#ff0000' },
            { name: 'Pulgar Arriba', color: '#ffff00' },
            { name: 'Pulgar Abajo', color: '#ff00ff' },
            { name: 'Pellizco', color: '#ffa500' },
            { name: 'Victoria', color: '#800080' },
            { name: 'OK', color: '#00ffff' },
            { name: 'Señalando', color: '#ffc0cb' },
          ].map((gesture) => (
            <div key={gesture.name} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: gesture.color }}
              />
              <span className="text-gray-300">{gesture.name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
