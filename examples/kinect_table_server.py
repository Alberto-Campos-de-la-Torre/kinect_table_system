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
from typing import Set, List, Optional, Tuple
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

# Importar módulos de calibración
from modules.calibration import (
    CoordinateMapper,
    CalibrationData,
    load_or_create_intrinsics,
    TableCalibrator,
    IntrinsicCalibrator
)

# Importar módulos de interacción
from modules.gesture_actions import (
    GestureActionMapper,
    ActionType,
    ActionState,
    ActionEvent,
    create_default_mapper
)
from modules.interaction_engine import (
    InteractionEngine,
    InteractionState,
    InteractionEvent as EngineInteractionEvent
)

# Importar módulo de control del mouse
from modules.mouse_control import (
    MouseController,
    MouseControlConfig,
    MouseAction,
    is_available as is_mouse_available
)

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
        
        # Configuración de volteo de video
        self.video_flip_h = False  # Volteo horizontal (espejo)
        self.video_flip_v = False  # Volteo vertical
        
        # Ángulo de inclinación del Kinect (grados hacia abajo respecto a la horizontal)
        # Usado para corregir la perspectiva cuando el Kinect no está perpendicular a la mesa
        self.kinect_tilt_angle = 0.0  # Grados (positivo = inclinado hacia abajo)
        
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
        
        # Módulo de calibración
        self.coordinate_mapper = None
        self.table_calibrator = None
        self.calibration_mode = False  # Modo calibración activo
        self.calibration_file = Path(__file__).parent.parent / "data" / "calibration_data.json"
        
        # Motor de interacción
        self.interaction_engine = None
        self.enable_interactions = True  # Habilitar sistema de interacciones

        # Controlador del mouse
        self.mouse_controller = None
        self.enable_mouse_control = False  # Deshabilitado por defecto

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
        
        # Cargar calibración
        logger.info("Cargando calibración...")
        self.coordinate_mapper = CoordinateMapper()
        self.table_calibrator = TableCalibrator()
        
        # Crear directorio de datos si no existe
        self.calibration_file.parent.mkdir(exist_ok=True)
        
        if self.calibration_file.exists():
            self.coordinate_mapper.load_calibration(str(self.calibration_file))
            logger.info("✅ Calibración cargada")
            
            # Aplicar intrinsics al generador de nube de puntos
            if self.pc_generator and self.coordinate_mapper.calibration.intrinsics:
                intr = self.coordinate_mapper.calibration.intrinsics
                self.pc_generator.set_intrinsics(
                    fx=intr.fx, fy=intr.fy,
                    cx=intr.cx, cy=intr.cy
                )
                logger.info(f"   Intrinsics aplicados: fx={intr.fx:.1f}, fy={intr.fy:.1f}")
        else:
            logger.info("⚠️ Sin calibración - usando valores por defecto")
            logger.info("   Usa la app o 'python scripts/calibrate_kinect.py' para calibrar")
        
        # Inicializar motor de interacción
        if self.enable_interactions:
            logger.info("Inicializando Interaction Engine...")
            self.interaction_engine = InteractionEngine()
            # Configurar tamaño del frame según el Kinect (v1: 640x480, v2: 1920x1080)
            kinect_rgb_res = self.kinect.rgb_resolution if self.kinect else (640, 480)
            self.interaction_engine.set_frame_size(kinect_rgb_res[0], kinect_rgb_res[1])
            logger.info("✅ Interaction Engine inicializado (modo espejo activado)")
            logger.info(f"   Mapeos de gestos: {len(self.interaction_engine.action_mapper.mappings)}")

        # Inicializar controlador del mouse
        logger.info("Inicializando Mouse Controller...")
        if is_mouse_available():
            self.mouse_controller = MouseController()
            # Usar resolución real del Kinect (v1: 640x480, v2: 1920x1080)
            kinect_rgb_res = self.kinect.rgb_resolution if self.kinect else (640, 480)
            self.mouse_controller.set_input_resolution(kinect_rgb_res[0], kinect_rgb_res[1])
            logger.info("✅ Mouse Controller inicializado (pyautogui disponible)")
            logger.info(f"   Resolución entrada: {kinect_rgb_res[0]}x{kinect_rgb_res[1]}")
            logger.info("   Gesto PINCH = clic izquierdo")
        else:
            logger.warning("⚠️ Mouse Controller no disponible (instalar: pip install pyautogui)")

        logger.info("=" * 60)
        print()
    
    def _get_hand_depth(
        self, 
        depth_frame: np.ndarray, 
        center: Tuple[float, float],
        bbox: Tuple[int, int, int, int]
    ) -> float:
        """
        Obtener la profundidad real de la mano desde el sensor Kinect.
        
        Args:
            depth_frame: Frame de profundidad del Kinect
            center: Centro de la mano (x, y) en píxeles
            bbox: Bounding box de la mano (x, y, width, height)
            
        Returns:
            Profundidad en mm (0 si no se puede obtener)
        """
        if depth_frame is None:
            return 0.0
        
        h, w = depth_frame.shape[:2]
        cx, cy = int(center[0]), int(center[1])
        
        # Asegurar que las coordenadas estén dentro del frame
        # Nota: Las cámaras RGB y Depth pueden tener diferentes resoluciones
        # Escalar las coordenadas si es necesario
        rgb_width = 640  # Asumiendo resolución RGB estándar
        rgb_height = 480
        
        # Escalar coordenadas de RGB a Depth
        scale_x = w / rgb_width
        scale_y = h / rgb_height
        
        cx_depth = int(cx * scale_x)
        cy_depth = int(cy * scale_y)
        
        # Limitar a los bordes del frame
        cx_depth = max(0, min(w - 1, cx_depth))
        cy_depth = max(0, min(h - 1, cy_depth))
        
        # Obtener profundidad en el centro de la mano
        # Usar un área pequeña alrededor del centro para mayor estabilidad
        sample_size = 5
        x1 = max(0, cx_depth - sample_size)
        x2 = min(w, cx_depth + sample_size)
        y1 = max(0, cy_depth - sample_size)
        y2 = min(h, cy_depth + sample_size)
        
        # Extraer región de interés
        roi = depth_frame[y1:y2, x1:x2]
        
        if roi.size == 0:
            return 0.0
        
        # Filtrar valores válidos (Kinect devuelve 0 o 2047 para profundidad no válida)
        valid_depths = roi[(roi > 0) & (roi < 2047)]
        
        if len(valid_depths) == 0:
            return 0.0
        
        # Usar la mediana para robustez contra outliers
        depth_raw = float(np.median(valid_depths))
        
        # Convertir valores crudos de Kinect v1 a milímetros reales
        # Kinect v1 con libfreenect devuelve valores 0-2046, necesitan conversión
        if depth_raw < 2047:
            # Fórmula de conversión de Kinect v1 (libfreenect)
            depth_mm = 1000.0 / (depth_raw * -0.0030711016 + 3.3309495161)
            # Limitar a rango válido (400mm - 4000mm)
            depth_mm = max(400.0, min(4000.0, depth_mm))
        else:
            depth_mm = depth_raw  # Ya está en mm (Kinect v2/SDK)
        
        return depth_mm
    
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
        depth = kinect_frame.depth
        detections = []
        hands_data = []
        
        # Aplicar volteo de video si está habilitado
        if self.video_flip_h or self.video_flip_v:
            flip_code = None
            if self.video_flip_h and self.video_flip_v:
                flip_code = -1  # Ambos
            elif self.video_flip_h:
                flip_code = 1   # Horizontal
            elif self.video_flip_v:
                flip_code = 0   # Vertical
            
            if flip_code is not None:
                rgb = cv2.flip(rgb, flip_code)
                depth = cv2.flip(depth, flip_code)
        
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
            depth_colored = depth_to_color(depth)  # Usar depth con flip aplicado
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
        interaction_data = None
        
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
            
            # Procesar interacciones
            if self.enable_interactions and self.interaction_engine:
                # Actualizar objetos en el motor de interacción
                self.interaction_engine.update_objects(detections_json)
                
                # Procesar cada mano
                active_hands = set()
                for hand in hands_data:
                    active_hands.add(hand.handedness)
                    
                    # Obtener profundidad real de la mano desde el sensor Kinect
                    hand_depth = self._get_hand_depth(
                        kinect_frame.depth, 
                        hand.center, 
                        hand.bbox
                    )
                    
                    # Procesar a través del motor de interacción
                    action_event = self.interaction_engine.process_hand(
                        hand=hand.handedness,
                        position=hand.center,
                        gesture=hand.gesture.value,
                        confidence=hand.confidence,
                        depth=hand_depth,
                        bbox_area=hand.bbox[2] * hand.bbox[3]  # width * height como fallback
                    )
                
                # Limpiar manos que ya no se detectan
                for hand_name in ["Left", "Right"]:
                    if hand_name not in active_hands:
                        self.interaction_engine.clear_hand(hand_name)
                
                # Obtener datos de interacción para el frontend
                interaction_data = self.interaction_engine.get_interaction_summary()
                interaction_data['events'] = [
                    e.to_dict() for e in self.interaction_engine.get_pending_events()
                ]

            # Procesar control del mouse si está habilitado
            if self.enable_mouse_control and self.mouse_controller:
                for hand in hands_data:
                    # Convertir landmarks a formato dict para el controlador
                    landmarks_list = [
                        {'x': lm.x, 'y': lm.y, 'z': lm.z}
                        for lm in hand.landmarks
                    ]

                    # Obtener profundidad de la mano desde el Kinect
                    hand_depth = self._get_hand_depth(
                        kinect_frame.depth,
                        hand.center,
                        hand.bbox
                    )

                    # Procesar con el controlador táctil (usa PINCH para clic)
                    mouse_result = self.mouse_controller.process_hand(
                        landmarks=landmarks_list,
                        handedness=hand.handedness,
                        hand_depth=hand_depth,
                        confidence=hand.confidence,
                        gesture=hand.gesture.value if hand.gesture else ""
                    )

                    # Agregar info del mouse al interaction_data
                    if interaction_data is None:
                        interaction_data = {}
                    if 'mouse' not in interaction_data:
                        interaction_data['mouse'] = {}
                    interaction_data['mouse'][hand.handedness] = mouse_result

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
        
        # Añadir datos de interacción si están disponibles
        if interaction_data is not None:
            result['interaction'] = interaction_data
        
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
            
            # Aplicar flip de calibración a los puntos
            if self.coordinate_mapper and pc.points is not None:
                cal = self.coordinate_mapper.calibration
                points = pc.points.copy()
                
                if cal.flip_x:
                    points[:, 0] = -points[:, 0]
                if cal.flip_y:
                    points[:, 1] = -points[:, 1]
                if cal.flip_z:
                    points[:, 2] = -points[:, 2]
                
                pc.points = points
            
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
                    'video_flip_h': self.video_flip_h,
                    'video_flip_v': self.video_flip_v,
                    'kinect_tilt_angle': self.kinect_tilt_angle,
                    'interactions_enabled': self.enable_interactions,
                    'turbo_jpeg': TURBO_AVAILABLE,
                    'calibration': {
                        'is_calibrated': self.coordinate_mapper.calibration.table_plane is not None,
                        'has_intrinsics': self.coordinate_mapper.calibration.intrinsics is not None,
                        'flip': {
                            'x': self.coordinate_mapper.calibration.flip_x,
                            'y': self.coordinate_mapper.calibration.flip_y,
                            'z': self.coordinate_mapper.calibration.flip_z
                        }
                    },
                    'interaction': {
                        'enabled': self.enable_interactions,
                        'gesture_mappings': len(self.interaction_engine.action_mapper.mappings) if self.interaction_engine else 0
                    },
                    'mouse_control': {
                        'available': is_mouse_available(),
                        'enabled': self.enable_mouse_control,
                        'state': self.mouse_controller.get_state() if self.mouse_controller else None
                    }
                }
            }))
            
            # Escuchar mensajes
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(websocket, data)
                except json.JSONDecodeError:
                    logger.error(f"Mensaje inválido (JSON): {message}")
                except Exception as e:
                    # Capturar cualquier excepción inesperada en handle_message
                    # para que NO cierre la conexión WebSocket.
                    logger.error(f"Error procesando mensaje '{data.get('type', '?')}': {e}", exc_info=True)
        
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
        
        # ========== Handlers de Interacción ==========
        
        elif msg_type == 'toggle_interactions':
            self.enable_interactions = not self.enable_interactions
            await websocket.send(json.dumps({
                'type': 'interactions_toggled',
                'enabled': self.enable_interactions
            }))
            logger.info(f"🎮 Interacciones: {'activadas' if self.enable_interactions else 'desactivadas'}")

        # ========== Handlers de Control del Mouse ==========

        elif msg_type == 'toggle_mouse_control':
            if not self.mouse_controller:
                await websocket.send(json.dumps({
                    'type': 'mouse_control_error',
                    'error': 'Mouse controller no disponible. Instalar: pip install pyautogui'
                }))
                return

            self.enable_mouse_control = not self.enable_mouse_control
            if self.enable_mouse_control:
                self.mouse_controller.enable()
            else:
                self.mouse_controller.disable()

            await websocket.send(json.dumps({
                'type': 'mouse_control_toggled',
                'enabled': self.enable_mouse_control,
                'state': self.mouse_controller.get_state()
            }))
            logger.info(f"🖱️ Control del mouse: {'ACTIVADO' if self.enable_mouse_control else 'DESACTIVADO'}")

        elif msg_type == 'get_mouse_state':
            if self.mouse_controller:
                await websocket.send(json.dumps({
                    'type': 'mouse_state',
                    'enabled': self.enable_mouse_control,
                    'state': self.mouse_controller.get_state()
                }))
            else:
                await websocket.send(json.dumps({
                    'type': 'mouse_state',
                    'enabled': False,
                    'available': False,
                    'error': 'Mouse controller no disponible'
                }))

        elif msg_type == 'set_mouse_sensitivity':
            # Sensibilidad ahora controla el suavizado (menor suavizado = más sensible)
            if self.mouse_controller:
                sensitivity = data.get('sensitivity', 1.5)
                # Mayor sensibilidad = menor suavizado
                smoothing = max(0.1, min(0.9, 1.0 - (sensitivity / 3.0)))
                self.mouse_controller.set_smoothing(smoothing)
                await websocket.send(json.dumps({
                    'type': 'mouse_sensitivity_changed',
                    'sensitivity': sensitivity,
                    'smoothing': self.mouse_controller.config.smoothing
                }))

        elif msg_type == 'set_mouse_smoothing':
            if self.mouse_controller:
                smoothing = data.get('smoothing', 0.7)
                self.mouse_controller.set_smoothing(smoothing)
                await websocket.send(json.dumps({
                    'type': 'mouse_smoothing_changed',
                    'smoothing': self.mouse_controller.config.smoothing
                }))

        elif msg_type == 'recalibrate_mouse':
            if self.mouse_controller:
                self.mouse_controller.recalibrate()
                await websocket.send(json.dumps({
                    'type': 'mouse_recalibrated',
                    'message': 'Estado del mouse reseteado'
                }))
                logger.info("🖱️ Estado del mouse reseteado")

        elif msg_type == 'set_mouse_flip':
            # Configurar flip de ejes (debe coincidir con calibración del video)
            if self.mouse_controller:
                flip_x = data.get('flip_x')
                flip_y = data.get('flip_y')
                self.mouse_controller.set_flip(flip_x, flip_y)
                await websocket.send(json.dumps({
                    'type': 'mouse_flip_changed',
                    'flip': {
                        'x': self.mouse_controller.config.flip_x,
                        'y': self.mouse_controller.config.flip_y
                    }
                }))
                logger.info(f"🖱️ Flip del mouse: X={self.mouse_controller.config.flip_x}, Y={self.mouse_controller.config.flip_y}")

        elif msg_type == 'set_mouse_screen_area':
            # Configurar área de pantalla activa (para múltiples monitores)
            if self.mouse_controller:
                x = data.get('x', 0)
                y = data.get('y', 0)
                width = data.get('width', 1920)
                height = data.get('height', 1080)
                self.mouse_controller.set_screen_area(x, y, width, height)
                await websocket.send(json.dumps({
                    'type': 'mouse_screen_area_changed',
                    'area': {'x': x, 'y': y, 'width': width, 'height': height}
                }))
                logger.info(f"🖱️ Área de pantalla: ({x}, {y}) {width}x{height}")

        elif msg_type == 'set_mouse_active_hand':
            if self.mouse_controller:
                hand = data.get('hand', 'Right')
                self.mouse_controller.set_active_hand(hand)
                await websocket.send(json.dumps({
                    'type': 'mouse_active_hand_changed',
                    'hand': self.mouse_controller.config.active_hand
                }))

        elif msg_type == 'get_interaction_state':
            if self.interaction_engine:
                state = self.interaction_engine.to_dict()
                await websocket.send(json.dumps({
                    'type': 'interaction_state',
                    'state': state
                }))
            else:
                await websocket.send(json.dumps({
                    'type': 'interaction_state',
                    'state': None,
                    'error': 'Interaction engine no inicializado'
                }))
        
        elif msg_type == 'deselect_all':
            if self.interaction_engine:
                self.interaction_engine.deselect_all()
                await websocket.send(json.dumps({
                    'type': 'deselect_complete'
                }))
        
        elif msg_type == 'get_action_mappings':
            if self.interaction_engine:
                mappings = self.interaction_engine.action_mapper.to_dict()
                await websocket.send(json.dumps({
                    'type': 'action_mappings',
                    'mappings': mappings
                }))
        
        elif msg_type == 'add_demo_objects':
            # Agregar objetos de demostración 2D para pruebas
            if self.interaction_engine:
                count = self.interaction_engine.add_demo_objects()
                await websocket.send(json.dumps({
                    'type': 'demo_objects_added',
                    'count': count,
                    'objects': [obj.to_dict() for obj in self.interaction_engine.objects.values()]
                }))
                logger.info(f"🎮 Agregados {count} objetos de demostración 2D")
        
        elif msg_type == 'add_demo_objects_3d':
            # Agregar objetos de demostración 3D
            if self.interaction_engine:
                count = self.interaction_engine.add_demo_objects_3d()
                await websocket.send(json.dumps({
                    'type': 'demo_objects_added',
                    'count': count,
                    'mode': '3d',
                    'objects': [obj.to_dict() for obj in self.interaction_engine.objects.values()]
                }))
                logger.info(f"🎮 Agregados {count} objetos de demostración 3D")
        
        elif msg_type == 'clear_demo_objects':
            # Limpiar objetos de demostración
            if self.interaction_engine:
                self.interaction_engine.clear_objects()
                await websocket.send(json.dumps({
                    'type': 'demo_objects_cleared'
                }))
                logger.info("🎮 Objetos de demostración limpiados")
        
        elif msg_type == 'get_demo_objects':
            # Obtener lista de objetos de demo
            if self.interaction_engine:
                await websocket.send(json.dumps({
                    'type': 'demo_objects',
                    'objects': [obj.to_dict() for obj in self.interaction_engine.objects.values()]
                }))
        
        # ========== Handlers de Calibración ==========
        
        elif msg_type == 'calibration_start':
            # Iniciar modo calibración
            self.calibration_mode = True
            self.table_calibrator.reset()
            status = self.table_calibrator.get_status()
            await websocket.send(json.dumps({
                'type': 'calibration_started',
                'status': status
            }))
            logger.info("🎯 Modo calibración iniciado")
        
        elif msg_type == 'calibration_cancel':
            # Cancelar calibración
            self.calibration_mode = False
            self.table_calibrator.reset()
            await websocket.send(json.dumps({
                'type': 'calibration_cancelled'
            }))
            logger.info("❌ Calibración cancelada")
        
        elif msg_type == 'calibration_capture':
            # Capturar punto de calibración
            if not self.calibration_mode:
                await websocket.send(json.dumps({
                    'type': 'calibration_error',
                    'error': 'Calibración no iniciada'
                }))
                return
            
            # Obtener frame actual
            frame = self.kinect.get_frame()
            if frame is None:
                await websocket.send(json.dumps({
                    'type': 'calibration_error',
                    'error': 'No se pudo capturar frame'
                }))
                return
            
            # Coordenadas del click (en espacio de imagen RGB 640x480)
            click_x = data.get('x', 320)
            click_y = data.get('y', 240)
            
            # Aplicar flip inverso si el video está volteado (para obtener coordenadas originales)
            if self.video_flip_h:
                click_x = 640 - click_x
            if self.video_flip_v:
                click_y = 480 - click_y
            
            # Escalar coordenadas de RGB (640x480) a Depth (puede ser diferente)
            depth_h, depth_w = frame.depth.shape[:2]
            scale_x = depth_w / 640.0
            scale_y = depth_h / 480.0
            
            x_depth = int(click_x * scale_x)
            y_depth = int(click_y * scale_y)
            
            # Limitar a bordes
            x_depth = max(0, min(depth_w - 1, x_depth))
            y_depth = max(0, min(depth_h - 1, y_depth))
            
            # Obtener profundidad con muestreo de área para mayor robustez
            sample_size = 10
            x1 = max(0, x_depth - sample_size)
            x2 = min(depth_w, x_depth + sample_size)
            y1 = max(0, y_depth - sample_size)
            y2 = min(depth_h, y_depth + sample_size)
            
            roi = frame.depth[y1:y2, x1:x2]
            
            # Filtrar valores válidos:
            # - Kinect v1: 0 = sin datos, 2047 = sin datos/saturado
            # - Kinect v2: 0 = sin datos
            valid_depths = roi[(roi > 0) & (roi < 2047) & (roi < 10000)]
            
            if len(valid_depths) == 0:
                # Intentar con rango más amplio por si es Kinect v2
                valid_depths = roi[(roi > 0) & (roi < 10000)]
            
            if len(valid_depths) == 0:
                await websocket.send(json.dumps({
                    'type': 'calibration_error',
                    'error': f'Sin profundidad válida en ({click_x}, {click_y}). El Kinect no puede ver esa área (puede estar muy cerca o muy lejos).'
                }))
                return
            
            depth_value = float(np.median(valid_depths))
            
            # Convertir a metros según tipo de Kinect
            # Detectar formato automáticamente basándose en el rango de valores
            if depth_value < 2047:  # Kinect v1 con libfreenect (valores crudos 0-2046)
                # Fórmula de conversión para Kinect v1
                depth_m = 0.1236 * np.tan(depth_value / 2842.5 + 1.1863)
                conversion_type = "v1_raw"
            elif depth_value < 100:  # Ya está en metros (valor muy pequeño)
                depth_m = depth_value
                conversion_type = "meters"
            else:  # Kinect v2 o SDK (valores en mm)
                depth_m = depth_value / 1000.0
                conversion_type = "mm"
            
            logger.info(f"📏 Profundidad: raw={depth_value:.1f}, conv={conversion_type}, metros={depth_m:.3f}")
            
            # Validar rango razonable (Kinect v1: 0.4-4m, v2: 0.5-4.5m)
            if depth_m < 0.3 or depth_m > 6.0:
                await websocket.send(json.dumps({
                    'type': 'calibration_error',
                    'error': f'Profundidad fuera de rango válido (0.3-6m): {depth_m:.3f}m. Mueve el punto a una zona donde el Kinect tenga mejor lectura.'
                }))
                return
            
            # Convertir a 3D usando coordenadas de imagen RGB
            intrinsics = self.coordinate_mapper.calibration.intrinsics
            px = (click_x - intrinsics.cx) * depth_m / intrinsics.fx
            py = (click_y - intrinsics.cy) * depth_m / intrinsics.fy
            pz = depth_m
            
            point_3d = np.array([float(px), float(py), float(pz)])
            
            logger.info(f"📍 Punto capturado: click=({click_x}, {click_y}), depth={depth_m:.3f}m, 3D={point_3d}")
            
            # Registrar punto
            completed, msg = self.table_calibrator.advance_calibration_step(point_3d)
            status = self.table_calibrator.get_status()
            
            await websocket.send(json.dumps({
                'type': 'calibration_point_captured',
                'point_3d': point_3d.tolist(),
                'depth_m': float(depth_m),
                'completed': completed,
                'message': msg,
                'status': status
            }))
            
            if completed:
                # Copiar el plano calculado al coordinate_mapper antes de guardar.
                # advance_calibration_step() almacena el resultado en table_calibrator,
                # pero _apply_and_save_calibration() guarda coordinate_mapper.calibration,
                # que tiene table_plane=None si no se copia explícitamente.
                self.coordinate_mapper.calibration.table_plane = self.table_calibrator.table_plane
                self.coordinate_mapper.calibration.table_height = self.table_calibrator.table_height
                await self._apply_and_save_calibration(websocket)
        
        elif msg_type == 'calibration_auto_plane':
            # Detectar plano automáticamente
            frame = self.kinect.get_frame()
            if frame is None:
                await websocket.send(json.dumps({
                    'type': 'calibration_error',
                    'error': 'No se pudo capturar frame'
                }))
                return
            
            # Generar nube de puntos
            pc = self.pc_generator.depth_to_pointcloud(frame.depth, downsample=2)
            
            if pc.num_points < 1000:
                await websocket.send(json.dumps({
                    'type': 'calibration_error',
                    'error': f'Muy pocos puntos: {pc.num_points}'
                }))
                return
            
            # Detectar plano
            success, plane = self.table_calibrator.detect_table_plane_ransac(pc.points)
            
            if success:
                # Aplicar calibración
                self.coordinate_mapper.calibration.table_plane = plane
                self.coordinate_mapper.calibration.table_height = self.table_calibrator.table_height
                await self._apply_and_save_calibration(websocket)
                
                await websocket.send(json.dumps({
                    'type': 'calibration_auto_complete',
                    'plane': plane.tolist(),
                    'table_height': self.table_calibrator.table_height
                }))
            else:
                await websocket.send(json.dumps({
                    'type': 'calibration_error',
                    'error': 'No se pudo detectar plano de mesa'
                }))
        
        elif msg_type == 'calibration_set_flip':
            # Ajustar flip de ejes (para nube de puntos)
            flip_x = data.get('flip_x')
            flip_y = data.get('flip_y')
            flip_z = data.get('flip_z')
            
            logger.info(f"Actualizando flip: x={flip_x}, y={flip_y}, z={flip_z}")
            
            self.coordinate_mapper.set_flip(flip_x, flip_y, flip_z)
            
            # Guardar cambios inmediatamente
            try:
                self.coordinate_mapper.save_calibration(str(self.calibration_file))
                logger.info(f"✅ Configuración de flip guardada")
            except Exception as e:
                logger.error(f"Error guardando flip: {e}")
            
            await websocket.send(json.dumps({
                'type': 'calibration_flip_updated',
                'flip': {
                    'x': self.coordinate_mapper.calibration.flip_x,
                    'y': self.coordinate_mapper.calibration.flip_y,
                    'z': self.coordinate_mapper.calibration.flip_z
                }
            }))
        
        elif msg_type == 'set_video_flip':
            # Voltear el stream de video
            self.video_flip_h = data.get('flip_h', self.video_flip_h)
            self.video_flip_v = data.get('flip_v', self.video_flip_v)
            
            logger.info(f"🔄 Video flip: H={self.video_flip_h}, V={self.video_flip_v}")
            
            await websocket.send(json.dumps({
                'type': 'video_flip_updated',
                'flip_h': self.video_flip_h,
                'flip_v': self.video_flip_v
            }))
        
        elif msg_type == 'set_kinect_tilt':
            # Configurar ángulo de inclinación del Kinect
            angle = data.get('angle', 0.0)
            self.kinect_tilt_angle = float(angle)
            
            # Aplicar al motor de interacción
            if self.interaction_engine:
                self.interaction_engine.set_kinect_tilt(self.kinect_tilt_angle)
            
            logger.info(f"📐 Ángulo de inclinación del Kinect: {self.kinect_tilt_angle}°")
            
            await websocket.send(json.dumps({
                'type': 'kinect_tilt_updated',
                'angle': self.kinect_tilt_angle
            }))
        
        elif msg_type == 'calibration_get_status':
            # Obtener estado de calibración
            cal_status = self.coordinate_mapper.get_calibration_status()
            table_status = self.table_calibrator.get_status()
            
            await websocket.send(json.dumps({
                'type': 'calibration_status',
                'calibration': cal_status,
                'table': table_status,
                'mode_active': self.calibration_mode
            }))
        
        elif msg_type == 'calibration_reset':
            # Reiniciar calibración
            self.coordinate_mapper = CoordinateMapper()
            self.table_calibrator.reset()
            
            # Eliminar archivo si existe
            if self.calibration_file.exists():
                self.calibration_file.unlink()
            
            await websocket.send(json.dumps({
                'type': 'calibration_reset_complete'
            }))
            logger.info("🔄 Calibración reiniciada")
        
        elif msg_type == 'server_restart':
            # Reiniciar servidor
            logger.info("⚡ Solicitud de reinicio del servidor recibida")
            await websocket.send(json.dumps({
                'type': 'server_restarting'
            }))
            
            # Programar reinicio después de enviar respuesta
            asyncio.create_task(self._restart_server())
    
    async def _restart_server(self):
        """Reiniciar el servidor"""
        import sys
        import subprocess
        import os
        
        logger.info("⚡ Reiniciando servidor en 1 segundo...")
        await asyncio.sleep(1)
        
        # Notificar a todos los clientes
        for client in self.clients:
            try:
                await client.send(json.dumps({
                    'type': 'server_restarting',
                    'message': 'El servidor se está reiniciando...'
                }))
            except:
                pass
        
        await asyncio.sleep(0.5)
        
        # Detener sistema actual
        self.running = False
        
        # Cerrar Kinect y recursos
        if self.kinect:
            self.kinect.release()
        
        logger.info("⚡ Ejecutando reinicio...")
        python = sys.executable
        script = str(Path(__file__).absolute())
        
        # En Windows, usar subprocess para reiniciar en nueva consola
        if sys.platform == 'win32':
            # Crear nuevo proceso con nueva consola
            subprocess.Popen(
                [python, script],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=str(Path(__file__).parent.parent)
            )
        else:
            # En Linux/Mac
            subprocess.Popen([python, script])
        
        # Dar tiempo para que el nuevo proceso inicie
        await asyncio.sleep(0.5)
        
        # Terminar proceso actual
        logger.info("⚡ Cerrando proceso actual...")
        os._exit(0)
    
    async def _apply_and_save_calibration(self, websocket):
        """Aplicar y guardar calibración"""
        from datetime import datetime
        
        # Actualizar fecha
        self.coordinate_mapper.calibration.calibration_date = datetime.now().isoformat()
        
        # Guardar
        self.coordinate_mapper.save_calibration(str(self.calibration_file))
        
        # Aplicar a generador de nube de puntos
        if self.pc_generator and self.coordinate_mapper.calibration.intrinsics:
            intr = self.coordinate_mapper.calibration.intrinsics
            self.pc_generator.set_intrinsics(
                fx=intr.fx, fy=intr.fy,
                cx=intr.cx, cy=intr.cy
            )
        
        self.calibration_mode = False

        logger.info(f"✅ Calibración guardada en: {self.calibration_file}")

        # Notificar a quien hizo la petición
        await websocket.send(json.dumps({
            'type': 'calibration_saved',
            'file': str(self.calibration_file)
        }))

        # Difundir el estado actualizado a TODOS los clientes para que
        # cualquier frontend conectado muestre is_calibrated=true sin tener
        # que enviar calibration_get_status manualmente.
        cal_status = self.coordinate_mapper.get_calibration_status()
        broadcast_msg = json.dumps({
            'type': 'calibration_status',
            'calibration': cal_status,
            'table': self.table_calibrator.get_status(),
            'mode_active': self.calibration_mode,
        })
        if self.clients:
            await asyncio.gather(
                *[c.send(broadcast_msg) for c in self.clients],
                return_exceptions=True,
            )
    
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
