/**
 * Componente HandTracker - Visualización de detección de manos
 */

import React from 'react';
import { GestureData, GestureType } from '../types/gesture.types';
import { Hand, ThumbsUp, ThumbsDown, Circle, Fingerprint } from 'lucide-react';

interface HandTrackerProps {
  gestures: GestureData[];
  canvasWidth?: number;
  canvasHeight?: number;
}

const gestureIcons: Record<GestureType, React.ReactNode> = {
  [GestureType.OPEN_PALM]: <Hand className="w-6 h-6" />,
  [GestureType.CLOSED_FIST]: <Circle className="w-6 h-6" />,
  [GestureType.THUMBS_UP]: <ThumbsUp className="w-6 h-6" />,
  [GestureType.THUMBS_DOWN]: <ThumbsDown className="w-6 h-6" />,
  [GestureType.PINCH]: <Fingerprint className="w-6 h-6" />,
  [GestureType.VICTORY]: <Hand className="w-6 h-6" />,
  [GestureType.OK_SIGN]: <Circle className="w-6 h-6" />,
  [GestureType.POINTING]: <Hand className="w-6 h-6" />,
  [GestureType.UNKNOWN]: <Hand className="w-6 h-6" />,
};

const gestureColors: Record<GestureType, string> = {
  [GestureType.OPEN_PALM]: '#00ff00',
  [GestureType.CLOSED_FIST]: '#ff0000',
  [GestureType.THUMBS_UP]: '#ffff00',
  [GestureType.THUMBS_DOWN]: '#ff00ff',
  [GestureType.PINCH]: '#ffa500',
  [GestureType.VICTORY]: '#800080',
  [GestureType.OK_SIGN]: '#00ffff',
  [GestureType.POINTING]: '#ffc0cb',
  [GestureType.UNKNOWN]: '#808080',
};

const gestureNames: Record<GestureType, string> = {
  [GestureType.OPEN_PALM]: 'Mano Abierta',
  [GestureType.CLOSED_FIST]: 'Puño Cerrado',
  [GestureType.THUMBS_UP]: 'Pulgar Arriba',
  [GestureType.THUMBS_DOWN]: 'Pulgar Abajo',
  [GestureType.PINCH]: 'Pellizco',
  [GestureType.VICTORY]: 'Victoria',
  [GestureType.OK_SIGN]: 'OK',
  [GestureType.POINTING]: 'Señalando',
  [GestureType.UNKNOWN]: 'Desconocido',
};

export const HandTracker: React.FC<HandTrackerProps> = ({
  gestures,
  canvasWidth = 1280,
  canvasHeight = 720,
}) => {
  const canvasRef = React.useRef<HTMLCanvasElement>(null);

  React.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Limpiar canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Dibujar cada gesto detectado
    gestures.forEach((gesture) => {
      const [x, y, w, h] = gesture.bounding_box;
      const color = gestureColors[gesture.gesture as GestureType];

      // Dibujar bounding box
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.strokeRect(x, y, w, h);

      // Dibujar landmarks (puntos de la mano)
      ctx.fillStyle = color;
      Object.values(gesture.landmarks).forEach(([lx, ly]) => {
        ctx.beginPath();
        ctx.arc(lx, ly, 5, 0, 2 * Math.PI);
        ctx.fill();
      });

      // Dibujar líneas conectando landmarks
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      
      // Conectar muñeca con cada punta de dedo
      const wrist = gesture.landmarks.wrist;
      [
        gesture.landmarks.thumb_tip,
        gesture.landmarks.index_tip,
        gesture.landmarks.middle_tip,
        gesture.landmarks.ring_tip,
        gesture.landmarks.pinky_tip,
      ].forEach((tip) => {
        ctx.beginPath();
        ctx.moveTo(wrist[0], wrist[1]);
        ctx.lineTo(tip[0], tip[1]);
        ctx.stroke();
      });
    });
  }, [gestures]);

  return (
    <div className="relative w-full h-full bg-gray-900 rounded-lg overflow-hidden">
      {/* Canvas para landmarks */}
      <canvas
        ref={canvasRef}
        width={canvasWidth}
        height={canvasHeight}
        className="w-full h-full object-contain"
      />

      {/* Overlay con información de gestos */}
      <div className="absolute top-4 left-4 right-4 flex flex-col gap-2">
        {gestures.map((gesture, idx) => (
          <div
            key={idx}
            className="flex items-center gap-3 bg-black/60 backdrop-blur-sm rounded-lg p-3 border-l-4"
            style={{ borderLeftColor: gestureColors[gesture.gesture as GestureType] }}
          >
            <div
              className="p-2 rounded-full"
              style={{ backgroundColor: gestureColors[gesture.gesture as GestureType] + '40' }}
            >
              {gestureIcons[gesture.gesture as GestureType]}
            </div>
            <div className="flex-1">
              <div className="text-white font-semibold">
                {gesture.handedness} - {gestureNames[gesture.gesture as GestureType]}
              </div>
              <div className="text-gray-300 text-sm">
                Confianza: {(gesture.confidence * 100).toFixed(0)}%
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Mensaje cuando no hay gestos */}
      {gestures.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center text-gray-400">
            <Hand className="w-16 h-16 mx-auto mb-4 opacity-50" />
            <p className="text-lg">Esperando detección de manos...</p>
            <p className="text-sm mt-2">Coloca tu mano frente a la cámara</p>
          </div>
        </div>
      )}
    </div>
  );
};
