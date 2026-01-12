"""
Kinect Table System - Sistema Integrado Principal
==================================================
Integra: Kinect + Hand Tracking + Object Detection
Para mesa-pantalla interactiva
"""

import asyncio
import websockets
import json
import cv2
import base64
import numpy as np
from typing import Set, List, Optional
import logging
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

# Agregar paths
sys.path.insert(0, str(Path(__file__).parent.parent))
print(sys.path)
# Importar módulos
from modules.kinect_capture import KinectCapture, depth_to_color
from modules.object_detection import ObjectDetector, get_mesa_class_ids
from modules.hand_tracking import HandTracker, HandGesture

# TurboJPEG opcional
try:
    from turbojpeg import TurboJPEG
    TURBO_AVAILABLE = True
except ImportError:
    TURBO_AVAILABLE = False

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KinectTableSystem:
    """
    Sistema completo de mesa interactiva con Kinect
    
    Características:
    - Captura RGB + Depth del Kinect
    - Detección de objetos con YOLO
    - Reconocimiento de gestos con MediaPipe
    - Streaming WebSocket a interfaz Tauri
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        kinect_rgb_res: tuple = None,  # Auto-detectar según versión del Kinect
        kinect_depth_res: tuple = None,  # Auto-detectar según versión del Kinect
        stream_quality: int = 75,
        enable_depth: bool = True,
        enable_objects: bool = True,
        enable_gestures: bool = True
    ):
        """
        Inicializar sistema
        
        Args:
            host: Host del servidor WebSocket
            port: Puerto del servidor
            kinect_rgb_res: Resolución RGB del Kinect (None = auto según versión)
            kinect_depth_res: Resolución depth del Kinect (None = auto según versión)
            stream_quality: Calidad JPEG (0-100)
            enable_depth: Habilitar streaming de profundidad
            enable_objects: Habilitar detección de objetos
            enable_gestures: Habilitar detección de gestos
        """
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.running = False
        
        # Configuración
        self.stream_quality = stream_quality
        self.enable_depth = enable_depth
        self.enable_objects = enable_objects
        self.enable_gestures = enable_gestures
        
        # Módulos
        self.kinect = None
        self.object_detector = None
        self.hand_tracker = None
        
        # Codificador (TurboJPEG si está disponible, sino OpenCV)
        self.jpeg_encoder = None
        if TURBO_AVAILABLE:
            try:
                self.jpeg_encoder = TurboJPEG()
                logger.info("Usando TurboJPEG para codificación de frames (más rápido)")
            except RuntimeError as e:
                logger.warning(f"No se pudo inicializar TurboJPEG: {e}. Usando OpenCV como fallback.")
                self.jpeg_encoder = None
        else:
            logger.info("Usando OpenCV para codificación de frames")
        
        # Procesamiento paralelo
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # Estadísticas
        self.stats = {
            'frames_processed': 0,
            'objects_detected': 0,
            'hands_detected': 0,
            'fps': 0.0
        }
        
        # Inicializar módulos
        self._initialize_modules(kinect_rgb_res, kinect_depth_res)
    
    def _initialize_modules(self, rgb_res: tuple, depth_res: tuple):
        """Inicializar módulos del sistema"""
        logger.info("=" * 60)
        logger.info("KINECT TABLE SYSTEM - INICIALIZACIÓN")
        logger.info("=" * 60)
        
        # Kinect
        logger.info("Inicializando Kinect...")
        self.kinect = KinectCapture(
            rgb_resolution=rgb_res,
            depth_resolution=depth_res
        )
        
        if not self.kinect.is_running:
            logger.error("❌ Kinect no inicializado")
        else:
            kinect_info = self.kinect.get_info()
            logger.info(f"✅ Kinect: {self.kinect.backend} (versión: {kinect_info.get('kinect_version', 'desconocida')})")
            logger.info(f"   Resolución RGB: {kinect_info['rgb_resolution']}")
            logger.info(f"   Resolución Depth: {kinect_info['depth_resolution']}")
        
        # Object Detector
        if self.enable_objects:
            logger.info("Inicializando Object Detector...")
            self.object_detector = ObjectDetector(
                model_name="yolov8n.pt",
                confidence_threshold=0.5,
                device="auto"
            )
            
            if not self.object_detector.is_initialized:
                logger.warning("⚠️ Object Detector no disponible")
            else:
                logger.info("✅ Object Detector inicializado")
        
        # Hand Tracker
        if self.enable_gestures:
            logger.info("Inicializando Hand Tracker...")
            self.hand_tracker = HandTracker(max_num_hands=2)
            logger.info("✅ Hand Tracker inicializado")
        
        logger.info("=" * 60)
        print()
    
    def _encode_frame(self, frame: np.ndarray) -> str:
        """Codificar frame a base64 JPEG"""
        if self.jpeg_encoder:
            # TurboJPEG
            jpg_bytes = self.jpeg_encoder.encode(frame, quality=self.stream_quality)
            return base64.b64encode(jpg_bytes).decode('utf-8')
        else:
            # OpenCV
            _, buffer = cv2.imencode('.jpg', frame, [
                cv2.IMWRITE_JPEG_QUALITY, self.stream_quality
            ])
            return base64.b64encode(buffer).decode('utf-8')
    
    async def process_frame(self):
        """Procesar un frame completo del sistema"""
        # Capturar del Kinect
        kinect_frame = self.kinect.get_frame()
        
        if kinect_frame is None:
            return None
        
        rgb = kinect_frame.rgb.copy()
        detections = []
        hands_data = []
        
        # Detección de objetos
        if self.enable_objects and self.object_detector and self.object_detector.is_initialized:
            loop = asyncio.get_event_loop()
            rgb, detections = await loop.run_in_executor(
                self.executor,
                self.object_detector.detect_and_draw,
                rgb
            )
            self.stats['objects_detected'] += len(detections)
        
        # Detección de gestos
        if self.enable_gestures and self.hand_tracker:
            loop = asyncio.get_event_loop()
            rgb, hands_data = await loop.run_in_executor(
                self.executor,
                self.hand_tracker.process_frame,
                rgb
            )
            self.stats['hands_detected'] += len(hands_data)
        
        # Codificar RGB
        encoded_rgb = await asyncio.get_event_loop().run_in_executor(
            self.executor,
            self._encode_frame,
            rgb
        )
        
        # Codificar Depth si está habilitado
        encoded_depth = None
        if self.enable_depth:
            depth_colored = depth_to_color(kinect_frame.depth)
            encoded_depth = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._encode_frame,
                depth_colored
            )
        
        # Serializar detecciones
        detections_json = [
            {
                'class_id': det.class_id,
                'class_name': det.class_name,
                'confidence': float(det.confidence),
                'bbox': {
                    'x': det.bbox[0],
                    'y': det.bbox[1],
                    'width': det.bbox[2],
                    'height': det.bbox[3]
                },
                'center': {
                    'x': float(det.center[0]),
                    'y': float(det.center[1])
                }
            }
            for det in detections
        ]
        
        # Serializar manos
        hands_json = []
        if self.hand_tracker:
            hands_json = [
                {
                    'handedness': hand.handedness,
                    'gesture': hand.gesture.value,
                    'gesture_name': self.hand_tracker.get_gesture_name(hand.gesture),
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
                    }
                }
                for hand in hands_data
            ]
        
        self.stats['frames_processed'] += 1
        
        return {
            'type': 'frame',
            'timestamp': asyncio.get_event_loop().time(),
            'frame_number': kinect_frame.frame_number,
            'rgb': encoded_rgb,
            'depth': encoded_depth,
            'objects': detections_json,
            'hands': hands_json,
            'stats': self.stats
        }
    
    async def stream_loop(self):
        """Loop principal de streaming"""
        import time
        frame_count = 0
        start_time = time.time()
        
        while self.running:
            if not self.kinect.is_running:
                await asyncio.sleep(0.1)
                continue
            
            try:
                # Procesar frame
                data = await self.process_frame()
                
                if data is None:
                    await asyncio.sleep(0.033)
                    continue
                
                # Calcular FPS
                frame_count += 1
                elapsed = time.time() - start_time
                if elapsed >= 1.0:
                    self.stats['fps'] = frame_count / elapsed
                    frame_count = 0
                    start_time = time.time()
                
                data['stats']['fps'] = self.stats['fps']
                
                # Enviar a clientes
                if self.clients:
                    message = json.dumps(data)
                    await asyncio.gather(
                        *[client.send(message) for client in self.clients],
                        return_exceptions=True
                    )
                
            except Exception as e:
                logger.error(f"Error en stream loop: {e}")
            
            await asyncio.sleep(0.001)  # Mínimo delay
    
    async def handle_client(self, websocket):
        """Manejar conexión de cliente"""
        self.clients.add(websocket)
        logger.info(f"Cliente conectado. Total: {len(self.clients)}")
        
        try:
            # Mensaje de bienvenida
            await websocket.send(json.dumps({
                'type': 'welcome',
                'message': 'Conectado a Kinect Table System',
                'config': {
                    'kinect_backend': self.kinect.backend if self.kinect else None,
                    'depth_enabled': self.enable_depth,
                    'objects_enabled': self.enable_objects,
                    'gestures_enabled': self.enable_gestures,
                    'turbo_jpeg': TURBO_AVAILABLE
                }
            }))
            
            # Escuchar mensajes
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(websocket, data)
                except json.JSONDecodeError:
                    logger.error(f"Mensaje inválido: {message}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info("Conexión cerrada")
        finally:
            self.clients.discard(websocket)
            logger.info(f"Cliente desconectado. Total: {len(self.clients)}")
    
    async def handle_message(self, websocket, data: dict):
        """Manejar mensajes del cliente"""
        msg_type = data.get('type')
        
        if msg_type == 'get_stats':
            await websocket.send(json.dumps({
                'type': 'stats',
                'stats': self.stats
            }))
        
        elif msg_type == 'toggle_depth':
            self.enable_depth = not self.enable_depth
            await websocket.send(json.dumps({
                'type': 'depth_toggled',
                'enabled': self.enable_depth
            }))
        
        elif msg_type == 'toggle_objects':
            self.enable_objects = not self.enable_objects
            await websocket.send(json.dumps({
                'type': 'objects_toggled',
                'enabled': self.enable_objects
            }))
        
        elif msg_type == 'toggle_gestures':
            self.enable_gestures = not self.enable_gestures
            await websocket.send(json.dumps({
                'type': 'gestures_toggled',
                'enabled': self.enable_gestures
            }))
    
    async def start(self):
        """Iniciar sistema"""
        self.running = True
        
        logger.info(f"Servidor iniciado en ws://{self.host}:{self.port}")
        
        # Iniciar servidor WebSocket
        async with websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            compression='deflate'
        ):
            # Iniciar streaming
            await self.stream_loop()
    
    async def stop(self):
        """Detener sistema"""
        logger.info("Deteniendo sistema...")
        self.running = False
        
        if self.kinect:
            self.kinect.release()
        if self.object_detector:
            self.object_detector.release()
        if self.hand_tracker:
            self.hand_tracker.release()
        
        self.executor.shutdown(wait=True)
        
        logger.info("✅ Sistema detenido")


async def main():
    """Función principal"""
    # Crear sistema con configuración por defecto
    # Las resoluciones se auto-detectan según la versión del Kinect
    system = KinectTableSystem(
        host="localhost",
        port=8765,
        kinect_rgb_res=None,  # Auto: 640x480 para Xbox 360, 1920x1080 para Xbox One
        kinect_depth_res=None,  # Auto: 640x480 para Xbox 360, 512x424 para Xbox One
        stream_quality=75,
        enable_depth=True,
        enable_objects=True,
        enable_gestures=True
    )
    
    try:
        await system.start()
    except KeyboardInterrupt:
        logger.info("Interrupción detectada")
    finally:
        await system.stop()


if __name__ == "__main__":
    print("=" * 60)
    print("KINECT TABLE SYSTEM - SERVIDOR INTEGRADO")
    print("=" * 60)
    print("Presiona Ctrl+C para detener")
    print("=" * 60)
    print()
    
    asyncio.run(main())
