"""
Configuración Global del Sistema Kinect Table
==============================================
Este archivo contiene todas las constantes y parámetros configurables del sistema.
"""

import os
from pathlib import Path

# ==========================================
# RUTAS DEL PROYECTO
# ==========================================
PROJECT_ROOT = Path(__file__).parent.resolve()
MODULES_DIR = PROJECT_ROOT / "modules"
MODELS_DIR = PROJECT_ROOT / "models"
DATA_DIR = PROJECT_ROOT / "data"
CALIBRATION_DIR = DATA_DIR / "calibration"
OBJECTS_DB_DIR = DATA_DIR / "objects_db"
TEMPLATES_DIR = DATA_DIR / "templates"
UTILS_DIR = PROJECT_ROOT / "utils"
TESTS_DIR = PROJECT_ROOT / "tests"
LOGS_DIR = PROJECT_ROOT / "logs"

# Crear directorios si no existen
for directory in [LOGS_DIR, CALIBRATION_DIR, OBJECTS_DB_DIR, TEMPLATES_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ==========================================
# CONFIGURACIÓN DEL KINECT
# ==========================================
class KinectConfig:
    """Configuración del sensor Kinect"""
    
    # Resoluciones
    RGB_WIDTH = 1920
    RGB_HEIGHT = 1080
    DEPTH_WIDTH = 512
    DEPTH_HEIGHT = 424
    
    # Frame rate objetivo
    FPS_TARGET = 30
    
    # Rango de profundidad (en milímetros)
    MIN_DEPTH = 500   # 0.5 metros
    MAX_DEPTH = 4500  # 4.5 metros
    
    # Distancia óptima de trabajo para vista cenital
    OPTIMAL_DISTANCE_MIN = 1500  # 1.5 metros
    OPTIMAL_DISTANCE_MAX = 2500  # 2.5 metros
    
    # Campo de visión (grados)
    HORIZONTAL_FOV = 70
    VERTICAL_FOV = 60
    
    # Modo de operación
    USE_DEPTH = True
    USE_RGB = True
    USE_INFRARED = False
    USE_SKELETON = False  # Para tracking de cuerpo completo


# ==========================================
# CONFIGURACIÓN DE DETECCIÓN DE OBJETOS
# ==========================================
class DetectionConfig:
    """Configuración del sistema de detección de objetos"""
    
    # Modelo YOLO
    MODEL_NAME = "yolov8n"  # yolov8n (nano), yolov8s (small), yolov8m (medium)
    MODEL_PATH = MODELS_DIR / "yolov8n.pt"
    
    # Parámetros de detección
    CONFIDENCE_THRESHOLD = 0.5  # Confianza mínima para detección
    IOU_THRESHOLD = 0.45        # IoU para Non-Maximum Suppression
    MAX_DETECTIONS = 10         # Máximo de objetos a detectar simultáneamente
    
    # Clases de objetos a detectar (COCO dataset)
    # None = todas las clases, o lista específica: [0, 1, 2, ...] 
    DETECT_CLASSES = None  # Detectar todas las clases
    
    # Tamaño de entrada del modelo
    INPUT_SIZE = 640  # 640x640 pixels
    
    # Usar GPU si está disponible
    USE_GPU = True
    GPU_DEVICE = 0  # ID del dispositivo GPU


# ==========================================
# CONFIGURACIÓN DE SEGMENTACIÓN
# ==========================================
class SegmentationConfig:
    """Configuración del sistema de segmentación"""
    
    # Detección del plano de la mesa
    RANSAC_THRESHOLD = 0.01  # Umbral en metros
    RANSAC_MAX_ITERATIONS = 1000
    
    # Segmentación de objetos
    MIN_OBJECT_HEIGHT = 0.02  # 2cm mínimo sobre la mesa
    MAX_OBJECT_HEIGHT = 0.50  # 50cm máximo
    MIN_OBJECT_AREA = 500     # Área mínima en pixels
    
    # Clustering
    CLUSTERING_METHOD = "DBSCAN"  # DBSCAN, KMeans, MeanShift
    DBSCAN_EPS = 0.02
    DBSCAN_MIN_SAMPLES = 50
    
    # Filtrado de ruido
    BILATERAL_FILTER_D = 5
    BILATERAL_FILTER_SIGMA_COLOR = 50
    BILATERAL_FILTER_SIGMA_SPACE = 50


# ==========================================
# CONFIGURACIÓN DE GESTOS
# ==========================================
class GestureConfig:
    """Configuración del sistema de reconocimiento de gestos"""
    
    # MediaPipe Hands
    MAX_NUM_HANDS = 2
    MIN_DETECTION_CONFIDENCE = 0.7
    MIN_TRACKING_CONFIDENCE = 0.5
    
    # Gestos soportados
    GESTURES = {
        "OPEN_PALM": "open_palm",
        "CLOSED_FIST": "closed_fist",
        "THUMBS_UP": "thumbs_up",
        "THUMBS_DOWN": "thumbs_down",
        "PINCH": "pinch",
        "SWIPE_LEFT": "swipe_left",
        "SWIPE_RIGHT": "swipe_right",
        "SWIPE_UP": "swipe_up",
        "SWIPE_DOWN": "swipe_down",
        "ROTATE_CW": "rotate_cw",
        "ROTATE_CCW": "rotate_ccw"
    }
    
    # Parámetros de detección de gestos
    SWIPE_THRESHOLD = 100  # Pixels de movimiento para detectar swipe
    PINCH_THRESHOLD = 0.05  # Distancia normalizada para pinch
    ROTATION_THRESHOLD = 30  # Grados para detectar rotación
    
    # Zona de activación (evitar falsos positivos)
    GESTURE_ZONE_MARGIN = 50  # Pixels desde el borde
    
    # Cooldown entre gestos (milisegundos)
    GESTURE_COOLDOWN = 500


# ==========================================
# CONFIGURACIÓN DE VISUALIZACIÓN
# ==========================================
class VisualizationConfig:
    """Configuración de la interfaz visual"""
    
    # Pantalla
    FULLSCREEN = True
    WINDOW_WIDTH = 1920
    WINDOW_HEIGHT = 1080
    
    # Colores (RGB)
    BACKGROUND_COLOR = (20, 20, 20)
    OBJECT_OUTLINE_COLOR = (0, 255, 0)
    GESTURE_HIGHLIGHT_COLOR = (255, 0, 255)
    TEXT_COLOR = (255, 255, 255)
    
    # Efectos visuales
    GLOW_EFFECT = True
    GLOW_INTENSITY = 15
    SHADOW_EFFECT = True
    
    # Información de objetos
    SHOW_LABELS = True
    SHOW_CONFIDENCE = True
    SHOW_DIMENSIONS = True
    SHOW_DISTANCE = True
    
    # Font
    FONT_NAME = "Arial"
    FONT_SIZE_LARGE = 32
    FONT_SIZE_MEDIUM = 24
    FONT_SIZE_SMALL = 16
    
    # FPS display
    SHOW_FPS = True
    FPS_UPDATE_INTERVAL = 0.5  # Segundos
    
    # Animaciones
    ANIMATION_DURATION = 300  # Milisegundos
    EASING_FUNCTION = "ease_in_out"  # linear, ease_in, ease_out, ease_in_out


# ==========================================
# CONFIGURACIÓN DE CALIBRACIÓN
# ==========================================
class CalibrationConfig:
    """Configuración del proceso de calibración"""
    
    # Patrón de calibración (tablero de ajedrez)
    CHESSBOARD_ROWS = 9
    CHESSBOARD_COLS = 6
    SQUARE_SIZE = 0.025  # 25mm
    
    # Número de imágenes para calibración
    MIN_CALIBRATION_IMAGES = 20
    
    # Archivo de calibración
    CALIBRATION_FILE = CALIBRATION_DIR / "calibration_data.npz"
    
    # Auto-calibración al inicio
    AUTO_CALIBRATE = False


# ==========================================
# CONFIGURACIÓN DE LOGGING
# ==========================================
class LogConfig:
    """Configuración del sistema de logging"""
    
    LOG_FILE = LOGS_DIR / "kinect_table_system.log"
    LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    
    # Rotación de logs
    LOG_ROTATION = "10 MB"
    LOG_RETENTION = "1 week"
    
    # Logs en consola
    CONSOLE_LOG = True


# ==========================================
# CONFIGURACIÓN DE RENDIMIENTO
# ==========================================
class PerformanceConfig:
    """Configuración de optimización de rendimiento"""
    
    # Multi-threading
    USE_MULTIPROCESSING = True
    NUM_WORKERS = 4  # Número de procesos paralelos
    
    # Buffer de frames
    FRAME_BUFFER_SIZE = 5
    
    # Suavizado temporal
    TEMPORAL_SMOOTHING = True
    SMOOTHING_WINDOW = 5  # Frames
    
    # Reducción de resolución para procesamiento
    DOWNSCALE_FACTOR = 1.0  # 1.0 = sin reducción, 0.5 = mitad de resolución
    
    # Optimizaciones
    USE_CUDA = True
    USE_TENSORRT = False  # Requiere instalación adicional
    
    # Límite de latencia (milisegundos)
    MAX_LATENCY = 100


# ==========================================
# CONFIGURACIÓN DE DATOS
# ==========================================
class DataConfig:
    """Configuración de almacenamiento de datos"""
    
    # Base de datos de objetos
    OBJECTS_DB_FILE = OBJECTS_DB_DIR / "objects.json"
    
    # Guardar histórico
    SAVE_HISTORY = True
    HISTORY_FILE = DATA_DIR / "detection_history.csv"
    
    # Screenshots
    SCREENSHOT_DIR = DATA_DIR / "screenshots"
    SCREENSHOT_FORMAT = "png"
    
    # Exportación
    EXPORT_FORMAT = "json"  # json, csv, xml


# ==========================================
# CONFIGURACIÓN DE DESARROLLO
# ==========================================
class DevConfig:
    """Configuración para desarrollo y debugging"""
    
    DEBUG_MODE = True
    VERBOSE_LOGGING = True
    
    # Modo de simulación (sin Kinect físico)
    SIMULATION_MODE = False
    SIMULATION_VIDEO = None  # Path a video para simular
    
    # Benchmarking
    ENABLE_PROFILING = False
    PROFILE_OUTPUT = LOGS_DIR / "profile.prof"
    
    # Tests
    RUN_UNIT_TESTS_ON_START = False


# ==========================================
# CONFIGURACIÓN AVANZADA
# ==========================================
class AdvancedConfig:
    """Configuraciones avanzadas y experimentales"""
    
    # OCR para texto en objetos
    ENABLE_OCR = False
    OCR_LANGUAGE = "spa"  # Español
    
    # QR/Barcode detection
    ENABLE_BARCODE = False
    
    # Reconocimiento de acciones
    ENABLE_ACTION_RECOGNITION = False
    
    # Realidad aumentada
    ENABLE_AR = False
    
    # Multi-Kinect (futuro)
    ENABLE_MULTI_KINECT = False
    NUM_KINECTS = 1


# ==========================================
# EXPORTAR CONFIGURACIONES
# ==========================================
# Para facilitar el acceso desde otros módulos
CONFIG = {
    "kinect": KinectConfig,
    "detection": DetectionConfig,
    "segmentation": SegmentationConfig,
    "gesture": GestureConfig,
    "visualization": VisualizationConfig,
    "calibration": CalibrationConfig,
    "log": LogConfig,
    "performance": PerformanceConfig,
    "data": DataConfig,
    "dev": DevConfig,
    "advanced": AdvancedConfig
}


# ==========================================
# FUNCIÓN DE AYUDA
# ==========================================
def get_config(section: str = None):
    """
    Obtener configuración específica
    
    Args:
        section: Nombre de la sección (kinect, detection, etc.)
                Si es None, retorna todas las configuraciones
    
    Returns:
        Clase de configuración o diccionario completo
    """
    if section is None:
        return CONFIG
    return CONFIG.get(section.lower())


def print_config():
    """Imprimir toda la configuración actual"""
    print("=" * 60)
    print("CONFIGURACIÓN DEL SISTEMA KINECT TABLE")
    print("=" * 60)
    for section_name, section_class in CONFIG.items():
        print(f"\n[{section_name.upper()}]")
        for attr in dir(section_class):
            if not attr.startswith("_"):
                value = getattr(section_class, attr)
                print(f"  {attr}: {value}")
    print("=" * 60)


if __name__ == "__main__":
    # Test de configuración
    print_config()
