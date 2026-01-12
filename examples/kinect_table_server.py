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

# Importar módulos
from modules.kinect_capture import KinectCapture, depth_to_color
from modules.object_detection import ObjectDetector, get_mesa_class_ids
from modules.hand_tracking import HandTracker, HandGesture

# Importar módulos de nube de puntos
from modules.point_cloud import (
    PointCloudGenerator, 
    PointCloudProcessor, 
    PointCloudStreamer,
    PointCloud
)
from modules.point_cloud.point_cloud_streaming import StreamingConfig

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
        enable_gestures: bool = True,
        enable_pointcloud: bool = True,  # Nube de puntos 3D
        pointcloud_downsample: int = 4,  # Factor de reducción
        pointcloud_max_points: int = 30000  # Máximo de puntos
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
            enable_pointcloud: Habilitar streaming de nube de puntos 3D
            pointcloud_downsample: Factor de reducción de resolución para nube de puntos
            pointcloud_max_points: Máximo de puntos a enviar
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
        self.enable_pointcloud = enable_pointcloud
        self.pointcloud_downsample = pointcloud_downsample
        self.pointcloud_max_points = pointcloud_max_points
        self.pointcloud_color_mode = 'rgb'  # 'rgb', 'depth', 'height'
        
        # Módulos
        self.kinect = None
        self.object_detector = None
        self.hand_tracker = None
        
        # Módulos de nube de puntos
        self.pc_generator = None
        self.pc_processor = None
        self.pc_streamer = None
        
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
        
        # Point Cloud Generator
        if self.enable_pointcloud:
            logger.info("Inicializando Point Cloud Generator...")
            self.pc_generator = PointCloudGenerator()
            self.pc_processor = PointCloudProcessor()
            
            # Configurar streamer
            streaming_config = StreamingConfig(
                max_points=self.pointcloud_max_points,
                compression=True,
                quantize_position=True,
                include_colors=True,
                target_fps=15
            )
            self.pc_streamer = PointCloudStreamer(streaming_config)
            logger.info(f"✅ Point Cloud Generator inicializado (downsample={self.pointcloud_downsample}x)")
        
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
        
        # Generar nube de puntos si está habilitado
        pointcloud_data = None
        if self.enable_pointcloud and self.pc_generator and self.pc_streamer:
            if self.pc_streamer.should_send():
                pointcloud_data = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self._generate_pointcloud,
                    kinect_frame.depth,
                    kinect_frame.rgb
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
        
        result = {
            'type': 'frame',
            'timestamp': asyncio.get_event_loop().time(),
            'frame_number': kinect_frame.frame_number,
            'rgb': encoded_rgb,
            'depth': encoded_depth,
            'objects': detections_json,
            'hands': hands_json,
            'stats': self.stats
        }
        
        # Añadir nube de puntos si está disponible
        if pointcloud_data is not None:
            result['pointcloud'] = pointcloud_data
        
        return result
    
    def _generate_pointcloud(self, depth: np.ndarray, rgb: np.ndarray) -> Optional[dict]:
        """Generar y codificar nube de puntos para streaming"""
        try:
            # Generar nube de puntos según el modo de color
            if self.pointcloud_color_mode == 'rgb':
                pc = self.pc_generator.generate_colored_pointcloud(
                    depth, rgb, 
                    downsample=self.pointcloud_downsample
                )
            elif self.pointcloud_color_mode == 'depth':
                pc = self.pc_generator.generate_depth_colored_pointcloud(
                    depth, 
                    colormap='turbo',
                    downsample=self.pointcloud_downsample
                )
            elif self.pointcloud_color_mode == 'height':
                pc = self.pc_generator.generate_height_colored_pointcloud(
                    depth,
                    floor_height=0,
                    colormap='viridis',
                    downsample=self.pointcloud_downsample
                )
            else:
                pc = self.pc_generator.depth_to_pointcloud(
                    depth,
                    downsample=self.pointcloud_downsample
                )
            
            if pc.num_points == 0:
                return None
            
            # Codificar para streaming
            return self.pc_streamer.encode_binary(pc)
            
        except Exception as e:
            logger.error(f"Error generando nube de puntos: {e}")
            return None
    
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
                    'pointcloud_enabled': self.enable_pointcloud,
                    'pointcloud_color_mode': self.pointcloud_color_mode,
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
        
        elif msg_type == 'toggle_pointcloud':
            self.enable_pointcloud = not self.enable_pointcloud
            await websocket.send(json.dumps({
                'type': 'pointcloud_toggled',
                'enabled': self.enable_pointcloud
            }))
        
        elif msg_type == 'set_pointcloud_color_mode':
            mode = data.get('mode', 'rgb')
            if mode in ['rgb', 'depth', 'height', 'none']:
                self.pointcloud_color_mode = mode
                await websocket.send(json.dumps({
                    'type': 'pointcloud_color_mode_changed',
                    'mode': self.pointcloud_color_mode
                }))
        
        elif msg_type == 'set_pointcloud_downsample':
            factor = data.get('factor', 4)
            if 1 <= factor <= 8:
                self.pointcloud_downsample = factor
                await websocket.send(json.dumps({
                    'type': 'pointcloud_downsample_changed',
                    'factor': self.pointcloud_downsample
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
        enable_gestures=True,
        enable_pointcloud=True,      # Nube de puntos 3D
        pointcloud_downsample=4,     # Reducir resolución 4x
        pointcloud_max_points=30000  # Máximo 30k puntos
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
