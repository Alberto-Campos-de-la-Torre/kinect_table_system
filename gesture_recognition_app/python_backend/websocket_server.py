"""
WebSocket Server para Hand Tracking
====================================
Servidor que transmite datos de tracking de manos a la aplicación Tauri
"""

import asyncio
import websockets
import json
import cv2
import base64
import numpy as np
from typing import Set, Optional
import logging
import sys
from pathlib import Path

# Configurar logging primero
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Intentar importar TurboJPEG, si no está disponible usar OpenCV como fallback
try:
    from turbojpeg import TurboJPEG
    TURBOJPEG_AVAILABLE = True
except (ImportError, RuntimeError) as e:
    TURBOJPEG_AVAILABLE = False
    logger.warning(f"TurboJPEG no disponible: {e}. Usando OpenCV como fallback.")

# Agregar el directorio padre al path para importar hand_tracking
sys.path.insert(0, str(Path(__file__).parent.parent))

from hand_tracking import HandTracker, HandGesture


class HandTrackingServer:
    """Servidor WebSocket para streaming de hand tracking"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.tracker = HandTracker(max_num_hands=2)
        self.cap = None
        self.running = False
        
        # Inicializar encoder JPEG (TurboJPEG si está disponible, sino OpenCV)
        self.use_turbojpeg = False
        self.jpeg_encoder: Optional[TurboJPEG] = None
        
        if TURBOJPEG_AVAILABLE:
            try:
                self.jpeg_encoder = TurboJPEG()
                self.use_turbojpeg = True
                logger.info("Usando TurboJPEG para codificación de frames (más rápido)")
            except RuntimeError as e:
                logger.warning(f"No se pudo inicializar TurboJPEG: {e}. Usando OpenCV como fallback.")
                self.use_turbojpeg = False
        else:
            logger.info("Usando OpenCV para codificación de frames")
        
    async def register_client(self, websocket: websockets.WebSocketServerProtocol):
        """Registrar un nuevo cliente"""
        self.clients.add(websocket)
        logger.info(f"Cliente conectado. Total: {len(self.clients)}")
        
    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol):
        """Desregistrar un cliente"""
        self.clients.discard(websocket)
        logger.info(f"Cliente desconectado. Total: {len(self.clients)}")
    
    def _encode_frame(self, frame: np.ndarray, quality: int = 75) -> str:
        """
        Codificar frame a base64 JPEG
        Usa TurboJPEG si está disponible (más rápido), sino usa OpenCV
        """
        # Redimensionar si es necesario para reducir ancho de banda
        if frame.shape[1] > 960:
            scale = 960 / frame.shape[1]
            new_size = (960, int(frame.shape[0] * scale))
            frame = cv2.resize(frame, new_size, interpolation=cv2.INTER_LINEAR)
        
        # Codificar con TurboJPEG si está disponible
        if self.use_turbojpeg and self.jpeg_encoder is not None:
            try:
                jpg_bytes = self.jpeg_encoder.encode(frame, quality=quality)
                return base64.b64encode(jpg_bytes).decode('utf-8')
            except Exception as e:
                logger.warning(f"Error con TurboJPEG, usando OpenCV: {e}")
                # Fallback a OpenCV
                self.use_turbojpeg = False
        
        # Fallback: usar OpenCV (más lento pero siempre disponible)
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        return jpg_as_text
    
    def _serialize_hand_data(self, hands_data: list) -> list:
        """Serializar datos de manos a JSON"""
        serialized = []
        
        for hand in hands_data:
            serialized.append({
                'handedness': hand.handedness,
                'gesture': hand.gesture.value,
                'gesture_name': self.tracker.get_gesture_name(hand.gesture),
                'confidence': float(hand.confidence),
                'bbox': {
                    'x': int(hand.bbox[0]),
                    'y': int(hand.bbox[1]),
                    'width': int(hand.bbox[2]),
                    'height': int(hand.bbox[3])
                },
                'center': {
                    'x': float(hand.center[0]),
                    'y': float(hand.center[1])
                },
                'landmarks': [
                    {
                        'x': float(lm.x),
                        'y': float(lm.y),
                        'z': float(lm.z)
                    }
                    for lm in hand.landmarks
                ]
            })
        
        return serialized
    
    async def send_frame_data(self):
        """Capturar y enviar frames a todos los clientes"""
        while self.running:
            if not self.cap or not self.cap.isOpened():
                await asyncio.sleep(0.1)
                continue
            
            ret, frame = self.cap.read()
            if not ret:
                logger.warning("No se pudo leer frame de la cámara")
                await asyncio.sleep(0.1)
                continue
            
            # Procesar frame
            annotated_frame, hands_data = self.tracker.process_frame(frame)
            
            # Codificar frame
            encoded_frame = self._encode_frame(annotated_frame, quality=75)
            
            # Serializar datos de manos
            hands_json = self._serialize_hand_data(hands_data)
            
            # Preparar mensaje
            message = json.dumps({
                'type': 'frame',
                'timestamp': asyncio.get_event_loop().time(),
                'fps': float(self.tracker.fps),
                'frame': encoded_frame,
                'hands': hands_json
            })
            
            # Enviar a todos los clientes conectados
            if self.clients:
                await asyncio.gather(
                    *[client.send(message) for client in self.clients],
                    return_exceptions=True
                )
            
            # Pequeña pausa para no saturar
            await asyncio.sleep(0.033)  # ~30 FPS
    
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str = None):
        """Manejar conexión de un cliente"""
        await self.register_client(websocket)
        
        try:
            # Enviar mensaje de bienvenida
            await websocket.send(json.dumps({
                'type': 'welcome',
                'message': 'Conectado al servidor de hand tracking'
            }))
            
            # Escuchar mensajes del cliente
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(websocket, data)
                except json.JSONDecodeError:
                    logger.error(f"Mensaje inválido: {message}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info("Conexión cerrada por el cliente")
        finally:
            await self.unregister_client(websocket)
    
    async def handle_message(self, websocket: websockets.WebSocketServerProtocol, data: dict):
        """Manejar mensajes recibidos del cliente"""
        msg_type = data.get('type')
        
        if msg_type == 'start_camera':
            await self.start_camera(data.get('camera_id', 0))
            await websocket.send(json.dumps({
                'type': 'camera_started',
                'success': self.cap is not None and self.cap.isOpened()
            }))
        
        elif msg_type == 'stop_camera':
            await self.stop_camera()
            await websocket.send(json.dumps({
                'type': 'camera_stopped',
                'success': True
            }))
        
        elif msg_type == 'ping':
            await websocket.send(json.dumps({
                'type': 'pong',
                'timestamp': asyncio.get_event_loop().time()
            }))
    
    async def start_camera(self, camera_id: int = 0):
        """Iniciar captura de cámara"""
        if self.cap is None or not self.cap.isOpened():
            logger.info(f"Iniciando cámara {camera_id}...")
            self.cap = cv2.VideoCapture(camera_id)
            
            if self.cap.isOpened():
                # Configurar resolución
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                logger.info("Cámara iniciada exitosamente")
            else:
                logger.error("No se pudo abrir la cámara")
                self.cap = None
    
    async def stop_camera(self):
        """Detener captura de cámara"""
        if self.cap:
            logger.info("Deteniendo cámara...")
            self.cap.release()
            self.cap = None
    
    async def start_server(self):
        """Iniciar servidor WebSocket"""
        self.running = True
        
        logger.info(f"Iniciando servidor en ws://{self.host}:{self.port}")
        
        # Iniciar cámara por defecto
        await self.start_camera(0)
        
        # Crear wrapper para el handler que maneje diferentes firmas de websockets
        async def handler(websocket, *args):
            path = args[0] if args else None
            await self.handle_client(websocket, path)
        
        # Iniciar servidor WebSocket
        async with websockets.serve(handler, self.host, self.port):
            # Iniciar envío de frames
            await self.send_frame_data()
    
    async def stop_server(self):
        """Detener servidor"""
        logger.info("Deteniendo servidor...")
        self.running = False
        await self.stop_camera()
        self.tracker.release()
        logger.info("Servidor detenido")


async def main():
    """Función principal"""
    server = HandTrackingServer(host="localhost", port=8765)
    
    try:
        await server.start_server()
    except KeyboardInterrupt:
        logger.info("Interrupción detectada")
    finally:
        await server.stop_server()


if __name__ == "__main__":
    print("=" * 60)
    print("HAND TRACKING WEBSOCKET SERVER")
    print("=" * 60)
    print(f"Servidor: ws://localhost:8765")
    print("Presiona Ctrl+C para detener")
    print("=" * 60)
    print()
    
    asyncio.run(main())
