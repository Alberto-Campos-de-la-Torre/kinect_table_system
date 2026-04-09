"""
Kinect Capture Module - Soporte para Kinect Xbox 360 y Xbox One
================================================================
- Kinect Xbox 360 (v1): libfreenect - RGB 640x480, Depth 640x480
- Kinect Xbox One (v2): libfreenect2 - RGB 1920x1080, Depth 512x424
"""

import numpy as np
import cv2
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
import logging
import platform
import os
import ctypes
from ctypes import c_void_p, c_int, c_uint32, POINTER, CFUNCTYPE, byref
import time
import threading

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================
# Resoluciones de los Kinects
# ============================================
# Kinect Xbox 360 (v1)
KINECT_V1_RGB_RES = (640, 480)
KINECT_V1_DEPTH_RES = (640, 480)

# Kinect Xbox One (v2)
KINECT_V2_RGB_RES = (1920, 1080)
KINECT_V2_DEPTH_RES = (512, 424)


# ============================================
# Constantes de libfreenect
# ============================================

# Resoluciones
FREENECT_RESOLUTION_LOW = 0     # 320x240
FREENECT_RESOLUTION_MEDIUM = 1  # 640x480
FREENECT_RESOLUTION_HIGH = 2    # 1280x1024

# Formatos de video
FREENECT_VIDEO_RGB = 0
FREENECT_VIDEO_BAYER = 1
FREENECT_VIDEO_YUV_RGB = 5

# Formatos de profundidad
FREENECT_DEPTH_11BIT = 0
FREENECT_DEPTH_10BIT = 1
FREENECT_DEPTH_REGISTERED = 4
FREENECT_DEPTH_MM = 5

# Device flags
FREENECT_DEVICE_MOTOR = 0x01
FREENECT_DEVICE_CAMERA = 0x02
FREENECT_DEVICE_AUDIO = 0x04


@dataclass
class KinectFrame:
    """Estructura de datos para un frame del Kinect"""
    rgb: np.ndarray
    depth: np.ndarray
    timestamp: float
    frame_number: int
    
    @property
    def rgb_resolution(self) -> Tuple[int, int]:
        return (self.rgb.shape[1], self.rgb.shape[0])
    
    @property
    def depth_resolution(self) -> Tuple[int, int]:
        return (self.depth.shape[1], self.depth.shape[0])


# ============================================
# Backend: libfreenect con ctypes
# ============================================

class FreenectBackend:
    """
    Backend para Kinect Xbox 360 usando libfreenect
    Carga libfreenect.so directamente con ctypes en Ubuntu/Linux
    """

    # Rutas de las bibliotecas en Ubuntu/Linux
    FREENECT_LIB_PATHS = [
        "/usr/lib/libfreenect.so",
        "/usr/lib/x86_64-linux-gnu/libfreenect.so",
        "/usr/local/lib/libfreenect.so",
        "/usr/lib/libfreenect.so.0",
        "/usr/lib/x86_64-linux-gnu/libfreenect.so.0",
        "/usr/local/lib/libfreenect.so.0",
    ]

    LIBUSB_LIB_PATHS = [
        "/usr/lib/libusb-1.0.so",
        "/usr/lib/x86_64-linux-gnu/libusb-1.0.so",
        "/usr/local/lib/libusb-1.0.so",
        "/usr/lib/libusb-1.0.so.0",
        "/usr/lib/x86_64-linux-gnu/libusb-1.0.so.0",
    ]
    
    def __init__(self):
        self.freenect = None
        self.ctx = None
        self.dev = None
        self.running = False
        self.thread = None
        
        # Buffers para frames
        self.rgb_buffer = None
        self.depth_buffer = None
        self.rgb_timestamp = 0
        self.depth_timestamp = 0
        self.lock = threading.Lock()
        
        # Callbacks (guardamos referencia para evitar garbage collection)
        self._video_cb = None
        self._depth_cb = None
    
    def _find_lib(self, paths: list) -> Optional[str]:
        """Encontrar biblioteca compartida en las rutas posibles"""
        for path in paths:
            if os.path.exists(path):
                return path
        return None

    def _load_libs(self) -> bool:
        """Cargar las bibliotecas necesarias en Ubuntu/Linux"""
        # Cargar libusb primero
        libusb_path = self._find_lib(self.LIBUSB_LIB_PATHS)
        if libusb_path:
            try:
                ctypes.CDLL(libusb_path)
                logger.info(f"✅ libusb cargado: {libusb_path}")
            except Exception as e:
                logger.warning(f"No se pudo cargar libusb: {e}")

        # Cargar freenect
        freenect_path = self._find_lib(self.FREENECT_LIB_PATHS)
        if not freenect_path:
            logger.error("❌ libfreenect.so no encontrado")
            logger.error("   Instalar con: sudo apt-get install libfreenect-dev freenect")
            return False

        try:
            self.freenect = ctypes.CDLL(freenect_path)
            logger.info(f"✅ freenect cargado: {freenect_path}")
            return True
        except Exception as e:
            logger.error(f"Error cargando freenect: {e}")
            return False
    
    def _setup_functions(self):
        """Configurar prototipos de funciones"""
        f = self.freenect
        
        # freenect_init
        f.freenect_init.argtypes = [POINTER(c_void_p), c_void_p]
        f.freenect_init.restype = c_int
        
        # freenect_shutdown
        f.freenect_shutdown.argtypes = [c_void_p]
        f.freenect_shutdown.restype = c_int
        
        # freenect_num_devices
        f.freenect_num_devices.argtypes = [c_void_p]
        f.freenect_num_devices.restype = c_int
        
        # freenect_open_device
        f.freenect_open_device.argtypes = [c_void_p, POINTER(c_void_p), c_int]
        f.freenect_open_device.restype = c_int
        
        # freenect_close_device
        f.freenect_close_device.argtypes = [c_void_p]
        f.freenect_close_device.restype = c_int
        
        # freenect_set_video_mode
        f.freenect_set_video_mode.argtypes = [c_void_p, c_int]  # Simplificado
        f.freenect_set_video_mode.restype = c_int
        
        # freenect_set_depth_mode  
        f.freenect_set_depth_mode.argtypes = [c_void_p, c_int]  # Simplificado
        f.freenect_set_depth_mode.restype = c_int
        
        # freenect_start_video
        f.freenect_start_video.argtypes = [c_void_p]
        f.freenect_start_video.restype = c_int
        
        # freenect_stop_video
        f.freenect_stop_video.argtypes = [c_void_p]
        f.freenect_stop_video.restype = c_int
        
        # freenect_start_depth
        f.freenect_start_depth.argtypes = [c_void_p]
        f.freenect_start_depth.restype = c_int
        
        # freenect_stop_depth
        f.freenect_stop_depth.argtypes = [c_void_p]
        f.freenect_stop_depth.restype = c_int
        
        # freenect_process_events
        f.freenect_process_events.argtypes = [c_void_p]
        f.freenect_process_events.restype = c_int
        
        # freenect_process_events_timeout (con timeout)
        try:
            f.freenect_process_events_timeout.argtypes = [c_void_p, c_void_p]
            f.freenect_process_events_timeout.restype = c_int
        except:
            pass
        
        # Callbacks
        self.VIDEO_CB = CFUNCTYPE(None, c_void_p, c_void_p, c_uint32)
        self.DEPTH_CB = CFUNCTYPE(None, c_void_p, c_void_p, c_uint32)
        
        # freenect_set_video_callback
        f.freenect_set_video_callback.argtypes = [c_void_p, self.VIDEO_CB]
        f.freenect_set_video_callback.restype = None
        
        # freenect_set_depth_callback
        f.freenect_set_depth_callback.argtypes = [c_void_p, self.DEPTH_CB]
        f.freenect_set_depth_callback.restype = None
        
        # freenect_select_subdevices
        try:
            f.freenect_select_subdevices.argtypes = [c_void_p, c_int]
            f.freenect_select_subdevices.restype = None
        except:
            pass
        
        # freenect_set_log_level - para silenciar mensajes de debug
        try:
            f.freenect_set_log_level.argtypes = [c_void_p, c_int]
            f.freenect_set_log_level.restype = None
        except:
            pass
    
    def _video_callback(self, dev, data, timestamp):
        """Callback para frames de video"""
        with self.lock:
            # Copiar datos RGB (640x480x3)
            size = 640 * 480 * 3
            buffer = ctypes.cast(data, POINTER(ctypes.c_uint8 * size))
            self.rgb_buffer = np.frombuffer(buffer.contents, dtype=np.uint8).reshape((480, 640, 3)).copy()
            self.rgb_timestamp = timestamp
    
    def _depth_callback(self, dev, data, timestamp):
        """Callback para frames de profundidad"""
        with self.lock:
            # Copiar datos de profundidad (640x480 uint16)
            size = 640 * 480
            buffer = ctypes.cast(data, POINTER(ctypes.c_uint16 * size))
            self.depth_buffer = np.frombuffer(buffer.contents, dtype=np.uint16).reshape((480, 640)).copy()
            self.depth_timestamp = timestamp
    
    def _process_loop(self):
        """Loop de procesamiento de eventos"""
        while self.running:
            try:
                ret = self.freenect.freenect_process_events(self.ctx)
                if ret < 0:
                    logger.error(f"Error procesando eventos: {ret}")
                    break
            except Exception as e:
                logger.error(f"Excepción en loop: {e}")
                break
    
    def initialize(self) -> bool:
        """Inicializar libfreenect"""
        logger.info("Inicializando libfreenect...")

        # Cargar bibliotecas compartidas (.so)
        if not self._load_libs():
            return False
        
        # Configurar funciones
        self._setup_functions()
        
        # Inicializar contexto
        ctx_ptr = c_void_p()
        ret = self.freenect.freenect_init(byref(ctx_ptr), None)
        if ret < 0:
            logger.error(f"❌ Error en freenect_init: {ret}")
            return False
        
        self.ctx = ctx_ptr
        logger.info("✅ Contexto freenect creado")
        
        # Silenciar mensajes de debug de libfreenect (solo mostrar errores)
        # Niveles: 0=FATAL, 1=ERROR, 2=WARNING, 3=NOTICE, 4=INFO, 5=DEBUG
        try:
            FREENECT_LOG_ERROR = 1
            self.freenect.freenect_set_log_level(self.ctx, FREENECT_LOG_ERROR)
        except:
            pass
        
        # Seleccionar subdevices (solo cámara)
        try:
            self.freenect.freenect_select_subdevices(self.ctx, FREENECT_DEVICE_CAMERA)
        except:
            pass
        
        # Verificar dispositivos
        num_devices = self.freenect.freenect_num_devices(self.ctx)
        logger.info(f"Dispositivos encontrados: {num_devices}")
        
        if num_devices < 1:
            logger.error("❌ No hay Kinect conectado")
            return False
        
        # Abrir dispositivo
        dev_ptr = c_void_p()
        ret = self.freenect.freenect_open_device(self.ctx, byref(dev_ptr), 0)
        if ret < 0:
            logger.error(f"❌ Error abriendo dispositivo: {ret}")
            return False
        
        self.dev = dev_ptr
        logger.info("✅ Dispositivo abierto")
        
        # Configurar modo de profundidad (MM = milímetros para conversión directa)
        # Intentar usar modo MM, si falla usar 11BIT por defecto
        try:
            # El modo se pasa como una estructura freenect_frame_mode comprimida
            # Para simplificar, usamos el modo por defecto y convertimos manualmente
            # ret = self.freenect.freenect_set_depth_mode(self.dev, FREENECT_DEPTH_MM)
            # if ret < 0:
            #     logger.warning(f"No se pudo configurar modo depth MM, usando 11BIT")
            logger.info("Usando modo de profundidad 11BIT (raw)")
        except Exception as e:
            logger.warning(f"Error configurando modo depth: {e}")
        
        # Configurar callbacks
        self._video_cb = self.VIDEO_CB(self._video_callback)
        self._depth_cb = self.DEPTH_CB(self._depth_callback)
        
        self.freenect.freenect_set_video_callback(self.dev, self._video_cb)
        self.freenect.freenect_set_depth_callback(self.dev, self._depth_cb)
        
        # Iniciar streams
        ret = self.freenect.freenect_start_video(self.dev)
        if ret < 0:
            logger.warning(f"Error iniciando video: {ret}")
        else:
            logger.info("✅ Stream de video iniciado")
        
        ret = self.freenect.freenect_start_depth(self.dev)
        if ret < 0:
            logger.warning(f"Error iniciando depth: {ret}")
        else:
            logger.info("✅ Stream de profundidad iniciado")
        
        # Iniciar thread de procesamiento
        self.running = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()
        
        logger.info("✅ libfreenect inicializado correctamente")
        return True
    
    def get_color_frame(self) -> Optional[np.ndarray]:
        """Obtener frame de color"""
        with self.lock:
            if self.rgb_buffer is not None:
                # Convertir RGB a BGR para OpenCV
                return cv2.cvtColor(self.rgb_buffer, cv2.COLOR_RGB2BGR)
        return None
    
    def get_depth_frame(self) -> Optional[np.ndarray]:
        """Obtener frame de profundidad"""
        with self.lock:
            if self.depth_buffer is not None:
                return self.depth_buffer.copy()
        return None
    
    def shutdown(self):
        """Cerrar libfreenect"""
        logger.info("Cerrando libfreenect...")
        
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=2.0)
        
        if self.dev and self.freenect:
            try:
                self.freenect.freenect_stop_video(self.dev)
                self.freenect.freenect_stop_depth(self.dev)
                self.freenect.freenect_close_device(self.dev)
            except:
                pass
        
        if self.ctx and self.freenect:
            try:
                self.freenect.freenect_shutdown(self.ctx)
            except:
                pass
        
        self.dev = None
        self.ctx = None
        logger.info("✅ libfreenect cerrado")


# ============================================
# Backend: libfreenect2 (Kinect Xbox One / v2)
# ============================================

class Freenect2Backend:
    """
    Backend para Kinect Xbox One (v2) usando libfreenect2
    Resoluciones: RGB 1920x1080, Depth 512x424
    """

    def __init__(self):
        self.freenect2 = None
        self.device = None
        self.listener = None
        self.running = False
        self.thread = None

        # Buffers para frames (actualizados por thread)
        self.rgb_buffer = None
        self.depth_buffer = None
        self.lock = threading.Lock()

        # Resoluciones de Kinect v2
        self.rgb_width = 1920
        self.rgb_height = 1080
        self.depth_width = 512
        self.depth_height = 424

        # Referencias a módulos de pylibfreenect2
        self._frame_type = None

    def _capture_loop(self):
        """Thread de captura continua de frames"""
        while self.running:
            try:
                # waitForNewFrame() bloquea hasta recibir frame (sin timeout)
                frames = self.listener.waitForNewFrame()

                if frames:
                    with self.lock:
                        # Capturar frame de color (BGRA -> BGR)
                        color_frame = frames[self._frame_type.Color]
                        self.rgb_buffer = color_frame.asarray()[:, :, :3].copy()

                        # Capturar frame de profundidad (float32 mm)
                        depth_frame = frames[self._frame_type.Depth]
                        self.depth_buffer = depth_frame.asarray().astype(np.uint16).copy()

                    # Liberar frames
                    self.listener.release(frames)

            except Exception as e:
                if self.running:
                    logger.debug(f"Error en captura: {e}")
                time.sleep(0.01)

    def initialize(self) -> bool:
        """Inicializar libfreenect2 usando pylibfreenect2"""
        logger.info("Intentando inicializar Kinect Xbox One (libfreenect2)...")

        try:
            from pylibfreenect2 import Freenect2, SyncMultiFrameListener
            from pylibfreenect2 import FrameType
            from pylibfreenect2 import createConsoleLogger, setGlobalLogger
            from pylibfreenect2 import LoggerLevel

            # Reducir logs
            setGlobalLogger(createConsoleLogger(LoggerLevel.Warning))

            fn2 = Freenect2()
            num_devices = fn2.enumerateDevices()

            if num_devices == 0:
                logger.info("No se encontró Kinect Xbox One")
                return False

            serial = fn2.getDeviceSerialNumber(0)
            logger.info(f"Kinect Xbox One encontrado: {serial}")

            # Abrir dispositivo
            self.device = fn2.openDevice(serial)

            if not self.device:
                logger.error("No se pudo abrir Kinect Xbox One")
                return False

            # Crear listener para frames (Color + Depth)
            self.listener = SyncMultiFrameListener(
                FrameType.Color | FrameType.Depth
            )

            self.device.setColorFrameListener(self.listener)
            self.device.setIrAndDepthFrameListener(self.listener)

            # Iniciar streams
            self.device.start()

            # Guardar referencias
            self.freenect2 = fn2
            self._frame_type = FrameType

            # Iniciar thread de captura
            self.running = True
            self.thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.thread.start()

            # Esperar primer frame
            time.sleep(0.5)

            logger.info("✅ Kinect Xbox One inicializado (pylibfreenect2)")
            logger.info(f"   RGB: {self.rgb_width}x{self.rgb_height}")
            logger.info(f"   Depth: {self.depth_width}x{self.depth_height}")
            return True

        except ImportError:
            logger.info("pylibfreenect2 no disponible")
        except Exception as e:
            logger.warning(f"Error con pylibfreenect2: {e}")
            import traceback
            traceback.print_exc()

        return False

    def get_color_frame(self) -> Optional[np.ndarray]:
        """Obtener frame de color del buffer"""
        with self.lock:
            if self.rgb_buffer is not None:
                return self.rgb_buffer.copy()
        return None

    def get_depth_frame(self) -> Optional[np.ndarray]:
        """Obtener frame de profundidad del buffer"""
        with self.lock:
            if self.depth_buffer is not None:
                return self.depth_buffer.copy()
        return None

    def shutdown(self):
        """Cerrar libfreenect2"""
        logger.info("Cerrando Kinect Xbox One...")

        self.running = False

        # Esperar que termine el thread
        if self.thread:
            self.thread.join(timeout=2.0)

        if self.device:
            try:
                self.device.stop()
                self.device.close()
            except Exception as e:
                logger.warning(f"Error cerrando device: {e}")

        self.device = None
        self.listener = None
        self.rgb_buffer = None
        self.depth_buffer = None
        logger.info("✅ Kinect Xbox One cerrado")


# ============================================
# Backend: Simulación (webcam)
# ============================================

class SimulationBackend:
    """Backend de simulación usando webcam"""
    
    def __init__(self):
        self.capture = None
    
    def initialize(self) -> bool:
        """Inicializar webcam"""
        logger.info("Inicializando modo simulación (webcam)...")
        
        self.capture = cv2.VideoCapture(0)
        
        if not self.capture.isOpened():
            logger.warning("No se pudo abrir la webcam")
            return False
        
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        logger.warning("⚠️ Modo simulación (sin profundidad real)")
        return True
    
    def get_color_frame(self) -> Optional[np.ndarray]:
        """Obtener frame de color"""
        ret, rgb = self.capture.read()
        return rgb if ret else None
    
    def get_depth_frame(self) -> Optional[np.ndarray]:
        """Simular frame de profundidad"""
        ret, rgb = self.capture.read()
        if not ret:
            return None
        gray = cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY)
        return gray.astype(np.uint16) * 16
    
    def shutdown(self):
        """Liberar recursos"""
        if self.capture:
            self.capture.release()


# ============================================
# Clase Principal: KinectCapture
# ============================================

class KinectCapture:
    """
    Captura de Kinect Xbox 360 y Xbox One

    Prioridad:
    1. libfreenect2 (Kinect Xbox One / v2)
    2. libfreenect (Kinect Xbox 360 / v1)
    3. Simulación con webcam
    """

    def __init__(
        self,
        rgb_resolution: Tuple[int, int] = None,
        depth_resolution: Tuple[int, int] = None,
        **kwargs
    ):
        self._requested_rgb_res = rgb_resolution
        self._requested_depth_res = depth_resolution
        
        self.rgb_resolution = KINECT_V1_RGB_RES
        self.depth_resolution = KINECT_V1_DEPTH_RES
        
        self.backend = None
        self.backend_instance = None
        self.is_running = False
        self.frame_count = 0
        self.kinect_version = "v1"
        self.platform = platform.system()
        
        self._auto_initialize()
    
    def _auto_initialize(self):
        """Inicializar automáticamente - prueba v2 primero, luego v1"""
        logger.info("=" * 60)
        logger.info("KINECT - DETECCIÓN AUTOMÁTICA")
        logger.info("=" * 60)

        # 1. Intentar Kinect Xbox One (v2) con libfreenect2
        logger.info("Buscando Kinect Xbox One (v2)...")
        freenect2 = Freenect2Backend()
        if freenect2.initialize():
            self.backend = "freenect2"
            self.backend_instance = freenect2
            self.kinect_version = "v2"
            self.rgb_resolution = KINECT_V2_RGB_RES
            self.depth_resolution = KINECT_V2_DEPTH_RES
            self.is_running = True
            logger.info("=" * 60)
            logger.info("✅ Kinect Xbox One (v2) listo")
            logger.info(f"   RGB: {self.rgb_resolution}")
            logger.info(f"   Depth: {self.depth_resolution}")
            logger.info("=" * 60)
            return

        # 2. Intentar Kinect Xbox 360 (v1) con libfreenect
        logger.info("Buscando Kinect Xbox 360 (v1)...")
        freenect = FreenectBackend()
        if freenect.initialize():
            self.backend = "freenect"
            self.backend_instance = freenect
            self.kinect_version = "v1"
            self.rgb_resolution = KINECT_V1_RGB_RES
            self.depth_resolution = KINECT_V1_DEPTH_RES
            self.is_running = True
            logger.info("=" * 60)
            logger.info("✅ Kinect Xbox 360 (v1) listo")
            logger.info(f"   RGB: {self.rgb_resolution}")
            logger.info(f"   Depth: {self.depth_resolution}")
            logger.info("=" * 60)
            return

        # 3. Fallback a simulación
        logger.warning("No se encontró Kinect, usando simulación...")
        self._init_simulation()
    
    def _init_simulation(self):
        """Inicializar simulación"""
        sim = SimulationBackend()
        if sim.initialize():
            self.backend = "simulation"
            self.backend_instance = sim
            self.kinect_version = "simulation"
            self.is_running = True
        else:
            self.is_running = False
    
    def get_frame(self) -> Optional[KinectFrame]:
        """Capturar un frame"""
        if not self.is_running or not self.backend_instance:
            return None
        
        rgb = self.backend_instance.get_color_frame()
        depth = self.backend_instance.get_depth_frame()
        
        if rgb is None:
            return None
        
        if depth is None:
            depth = np.zeros((480, 640), dtype=np.uint16)
        
        # Redimensionar si se solicitó
        if self._requested_rgb_res and rgb.shape[:2][::-1] != self._requested_rgb_res:
            rgb = cv2.resize(rgb, self._requested_rgb_res)
        
        if self._requested_depth_res and depth.shape[::-1] != self._requested_depth_res:
            depth = cv2.resize(depth, self._requested_depth_res, interpolation=cv2.INTER_NEAREST)
        
        self.frame_count += 1
        
        return KinectFrame(
            rgb=rgb,
            depth=depth,
            timestamp=time.time(),
            frame_number=self.frame_count
        )
    
    def get_info(self) -> Dict[str, Any]:
        """Obtener información del dispositivo"""
        return {
            'backend': self.backend,
            'kinect_version': self.kinect_version,
            'platform': self.platform,
            'is_running': self.is_running,
            'rgb_resolution': self.rgb_resolution,
            'depth_resolution': self.depth_resolution,
            'frames_captured': self.frame_count
        }
    
    def release(self):
        """Liberar recursos"""
        logger.info("Liberando recursos...")
        
        if self.backend_instance:
            self.backend_instance.shutdown()
        
        self.backend_instance = None
        self.is_running = False
        logger.info("✅ Recursos liberados")


def depth_to_color(depth: np.ndarray, colormap: int = cv2.COLORMAP_JET) -> np.ndarray:
    """Convertir mapa de profundidad a imagen colorizada"""
    depth_normalized = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX)
    return cv2.applyColorMap(depth_normalized.astype(np.uint8), colormap)


# ============================================
# Test
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("KINECT XBOX 360 - TEST LIBFREENECT")
    print("=" * 60)
    print("Presiona 'q' para salir")
    print()
    
    kinect = KinectCapture()
    
    if not kinect.is_running:
        print("\n❌ No se pudo inicializar")
        exit(1)
    
    info = kinect.get_info()
    print(f"\nBackend: {info['backend']}")
    print(f"RGB: {info['rgb_resolution']}")
    print(f"Depth: {info['depth_resolution']}")
    
    # Esperar a que lleguen frames
    time.sleep(1)
    
    try:
        while True:
            frame = kinect.get_frame()
            
            if frame is None:
                time.sleep(0.01)
                continue
            
            cv2.imshow('RGB', frame.rgb)
            cv2.imshow('Depth', depth_to_color(frame.depth))
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    except KeyboardInterrupt:
        pass
    
    finally:
        kinect.release()
        cv2.destroyAllWindows()
        print("✅ Finalizado")
