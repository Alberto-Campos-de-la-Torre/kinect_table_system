"""
Object Detection Module
=======================
Detección de objetos usando YOLOv8 (Ultralytics)
Optimizado para detección en tiempo real sobre mesa-pantalla
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Intentar importar YOLO
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("Ultralytics YOLO no disponible")
    logger.info("Instala con: pip install ultralytics")


@dataclass
class Detection:
    """Estructura de datos para una detección de objeto"""
    class_id: int                    # ID de la clase
    class_name: str                  # Nombre de la clase
    confidence: float                # Confianza (0-1)
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    center: Tuple[float, float]      # Centro del objeto
    mask: Optional[np.ndarray]       # Máscara de segmentación (opcional)
    
    @property
    def area(self) -> int:
        """Área del bounding box"""
        return self.bbox[2] * self.bbox[3]
    
    @property
    def corners(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Esquinas del bounding box (top-left, bottom-right)"""
        x, y, w, h = self.bbox
        return ((x, y), (x + w, y + h))


class ObjectDetector:
    """
    Detector de objetos usando YOLOv8
    
    Características:
    - Detección en tiempo real
    - Tracking temporal para estabilidad
    - Suavizado de bounding boxes
    - Histéresis para evitar parpadeo
    """
    
    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        device: str = "auto",
        max_detections: int = 10,
        stability_frames: int = 3,  # Frames para estabilidad
        smoothing_factor: float = 0.7  # Suavizado de bbox (0-1)
    ):
        """
        Inicializar detector
        
        Args:
            model_name: Nombre del modelo YOLO
            confidence_threshold: Umbral de confianza mínima
            iou_threshold: Umbral de IoU para NMS
            device: Dispositivo ('cpu', 'cuda', 'auto')
            max_detections: Número máximo de detecciones por frame
            stability_frames: Frames que un objeto debe persistir para mostrarse
            smoothing_factor: Factor de suavizado para bounding boxes
        """
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.max_detections = max_detections
        self.stability_frames = stability_frames
        self.smoothing_factor = smoothing_factor
        
        self.model = None
        self.class_names = None
        self.is_initialized = False
        
        # Estadísticas
        self.total_detections = 0
        self.frames_processed = 0
        
        # Tracking temporal para estabilidad
        self.tracked_objects: Dict[int, dict] = {}  # id -> {detection, frames_seen, frames_missing, smoothed_bbox}
        self.next_track_id = 0
        self.max_missing_frames = 5  # Frames antes de eliminar objeto
        
        # Inicializar modelo
        self._initialize_model(device)
    
    def _initialize_model(self, device: str = "auto"):
        """Inicializar modelo YOLO"""
        if not YOLO_AVAILABLE:
            logger.error("YOLO no está disponible")
            return
        
        try:
            logger.info(f"Cargando modelo YOLO: {self.model_name}")
            
            # Detectar dispositivo automáticamente
            if device == "auto":
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info(f"Dispositivo detectado: {device}")
            
            # Cargar modelo
            self.model = YOLO(self.model_name)
            
            # Obtener nombres de clases
            self.class_names = self.model.names
            
            # Configurar
            self.model.conf = self.confidence_threshold
            self.model.iou = self.iou_threshold
            self.model.max_det = self.max_detections
            
            self.is_initialized = True
            
            logger.info(f"✅ Modelo cargado: {len(self.class_names)} clases")
            logger.info(f"   Confianza mínima: {self.confidence_threshold}")
            logger.info(f"   Dispositivo: {device}")
            
        except Exception as e:
            logger.error(f"Error cargando modelo: {e}")
            self.is_initialized = False
    
    def detect(
        self, 
        frame: np.ndarray,
        classes: Optional[List[int]] = None,
        min_area: int = 100
    ) -> List[Detection]:
        """
        Detectar objetos en un frame
        
        Args:
            frame: Frame BGR de OpenCV
            classes: Lista de IDs de clases a detectar (None = todas)
            min_area: Área mínima del bounding box
            
        Returns:
            Lista de detecciones
        """
        if not self.is_initialized:
            logger.warning("Detector no inicializado")
            return []
        
        try:
            # Ejecutar detección
            results = self.model(frame, verbose=False)
            
            # Procesar resultados
            detections = []
            
            if len(results) > 0:
                result = results[0]
                boxes = result.boxes
                
                if boxes is not None:
                    for box in boxes:
                        # Extraer datos
                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])
                        xyxy = box.xyxy[0].cpu().numpy()
                        
                        # Filtrar por clase si se especificó
                        if classes is not None and class_id not in classes:
                            continue
                        
                        # Convertir a formato (x, y, w, h)
                        x1, y1, x2, y2 = map(int, xyxy)
                        x, y = x1, y1
                        w, h = x2 - x1, y2 - y1
                        
                        # Filtrar por área mínima
                        if w * h < min_area:
                            continue
                        
                        # Calcular centro
                        cx = x + w // 2
                        cy = y + h // 2
                        
                        # Crear detección
                        detection = Detection(
                            class_id=class_id,
                            class_name=self.class_names[class_id],
                            confidence=confidence,
                            bbox=(x, y, w, h),
                            center=(cx, cy),
                            mask=None
                        )
                        
                        detections.append(detection)
                        self.total_detections += 1
            
            self.frames_processed += 1
            
            # Aplicar tracking temporal para estabilidad
            stable_detections = self._apply_temporal_tracking(detections)
            
            return stable_detections
            
        except Exception as e:
            logger.error(f"Error en detección: {e}")
            return []
    
    def _apply_temporal_tracking(self, detections: List[Detection]) -> List[Detection]:
        """
        Aplicar tracking temporal para estabilizar detecciones
        Evita que los objetos aparezcan y desaparezcan rápidamente
        """
        # Marcar todos los tracked objects como no vistos este frame
        for track_id in self.tracked_objects:
            self.tracked_objects[track_id]['seen_this_frame'] = False
        
        # Asociar detecciones con tracked objects existentes
        for detection in detections:
            best_match_id = None
            best_iou = 0.3  # Umbral mínimo de IoU para matching
            
            for track_id, tracked in self.tracked_objects.items():
                if tracked['class_id'] != detection.class_id:
                    continue
                
                iou = self._calculate_iou(detection.bbox, tracked['bbox'])
                if iou > best_iou:
                    best_iou = iou
                    best_match_id = track_id
            
            if best_match_id is not None:
                # Actualizar objeto existente con suavizado
                tracked = self.tracked_objects[best_match_id]
                tracked['frames_seen'] += 1
                tracked['frames_missing'] = 0
                tracked['seen_this_frame'] = True
                tracked['confidence'] = detection.confidence
                
                # Suavizar bounding box
                old_bbox = tracked['smoothed_bbox']
                new_bbox = detection.bbox
                smoothed = tuple(
                    int(self.smoothing_factor * old + (1 - self.smoothing_factor) * new)
                    for old, new in zip(old_bbox, new_bbox)
                )
                tracked['smoothed_bbox'] = smoothed
                tracked['bbox'] = detection.bbox
            else:
                # Nuevo objeto
                self.tracked_objects[self.next_track_id] = {
                    'class_id': detection.class_id,
                    'class_name': detection.class_name,
                    'bbox': detection.bbox,
                    'smoothed_bbox': detection.bbox,
                    'confidence': detection.confidence,
                    'frames_seen': 1,
                    'frames_missing': 0,
                    'seen_this_frame': True
                }
                self.next_track_id += 1
        
        # Incrementar frames_missing para objetos no vistos
        tracks_to_remove = []
        for track_id, tracked in self.tracked_objects.items():
            if not tracked['seen_this_frame']:
                tracked['frames_missing'] += 1
                if tracked['frames_missing'] > self.max_missing_frames:
                    tracks_to_remove.append(track_id)
        
        # Eliminar tracks antiguos
        for track_id in tracks_to_remove:
            del self.tracked_objects[track_id]
        
        # Generar detecciones estables (solo objetos con suficientes frames)
        stable_detections = []
        for track_id, tracked in self.tracked_objects.items():
            # Solo mostrar si ha sido visto suficientes frames
            if tracked['frames_seen'] >= self.stability_frames:
                x, y, w, h = tracked['smoothed_bbox']
                detection = Detection(
                    class_id=tracked['class_id'],
                    class_name=tracked['class_name'],
                    confidence=tracked['confidence'],
                    bbox=tracked['smoothed_bbox'],
                    center=(x + w // 2, y + h // 2),
                    mask=None
                )
                stable_detections.append(detection)
        
        return stable_detections
    
    def _calculate_iou(self, bbox1: Tuple, bbox2: Tuple) -> float:
        """Calcular Intersection over Union entre dos bounding boxes"""
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Coordenadas de intersección
        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(x1 + w1, x2 + w2)
        yi2 = min(y1 + h1, y2 + h2)
        
        if xi2 <= xi1 or yi2 <= yi1:
            return 0.0
        
        inter_area = (xi2 - xi1) * (yi2 - yi1)
        bbox1_area = w1 * h1
        bbox2_area = w2 * h2
        union_area = bbox1_area + bbox2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0
    
    def detect_and_draw(
        self,
        frame: np.ndarray,
        classes: Optional[List[int]] = None,
        min_area: int = 100,
        show_labels: bool = True,
        show_confidence: bool = True,
        thickness: int = 2
    ) -> Tuple[np.ndarray, List[Detection]]:
        """
        Detectar y dibujar objetos en el frame
        
        Args:
            frame: Frame BGR de OpenCV
            classes: Clases a detectar
            min_area: Área mínima
            show_labels: Mostrar etiquetas
            show_confidence: Mostrar confianza
            thickness: Grosor de las líneas
            
        Returns:
            Tuple de (frame anotado, lista de detecciones)
        """
        # Detectar
        detections = self.detect(frame, classes, min_area)
        
        # Dibujar
        annotated_frame = frame.copy()
        
        for detection in detections:
            # Color basado en clase (usar hash para consistencia)
            color = self._get_class_color(detection.class_id)
            
            # Dibujar bounding box
            (x1, y1), (x2, y2) = detection.corners
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, thickness)
            
            # Dibujar etiqueta
            if show_labels:
                label = detection.class_name
                if show_confidence:
                    label += f" {detection.confidence:.2f}"
                
                # Fondo para texto
                (text_w, text_h), _ = cv2.getTextSize(
                    label, 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.6, 
                    thickness
                )
                
                cv2.rectangle(
                    annotated_frame,
                    (x1, y1 - text_h - 10),
                    (x1 + text_w, y1),
                    color,
                    -1
                )
                
                cv2.putText(
                    annotated_frame,
                    label,
                    (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    thickness
                )
            
            # Dibujar centro
            cx, cy = detection.center
            cv2.circle(annotated_frame, (int(cx), int(cy)), 4, color, -1)
        
        return annotated_frame, detections
    
    def _get_class_color(self, class_id: int) -> Tuple[int, int, int]:
        """Obtener color consistente para una clase"""
        # Generar color usando hash del ID
        np.random.seed(class_id)
        color = tuple(map(int, np.random.randint(0, 255, 3)))
        return color
    
    def get_class_names(self) -> Dict[int, str]:
        """Obtener diccionario de nombres de clases"""
        if self.class_names:
            return self.class_names
        return {}
    
    def filter_by_classes(
        self, 
        detections: List[Detection], 
        class_names: List[str]
    ) -> List[Detection]:
        """
        Filtrar detecciones por nombres de clase
        
        Args:
            detections: Lista de detecciones
            class_names: Lista de nombres de clase a mantener
            
        Returns:
            Lista filtrada de detecciones
        """
        return [
            det for det in detections 
            if det.class_name in class_names
        ]
    
    def get_stats(self) -> Dict[str, any]:
        """Obtener estadísticas del detector"""
        return {
            'model': self.model_name,
            'is_initialized': self.is_initialized,
            'confidence_threshold': self.confidence_threshold,
            'iou_threshold': self.iou_threshold,
            'frames_processed': self.frames_processed,
            'total_detections': self.total_detections,
            'avg_detections_per_frame': (
                self.total_detections / self.frames_processed 
                if self.frames_processed > 0 else 0
            )
        }
    
    def release(self):
        """Liberar recursos"""
        logger.info("Liberando detector...")
        self.model = None
        self.is_initialized = False


# Clases de objetos comunes en mesa
MESA_OBJECTS = [
    'person',       # 0
    'cup',          # 41
    'bottle',       # 39
    'bowl',         # 45
    'book',         # 73
    'cell phone',   # 67
    'laptop',       # 63
    'mouse',        # 64
    'keyboard',     # 66
    'scissors',     # 76
    'pen',          # No está en COCO
    'spoon',        # 44
    'fork',         # 43
    'knife',        # 42
]


def get_mesa_class_ids() -> List[int]:
    """Obtener IDs de clases relevantes para mesa"""
    # IDs de COCO dataset para objetos de mesa
    return [0, 39, 41, 42, 43, 44, 45, 63, 64, 66, 67, 73, 76]


# Demo standalone
if __name__ == "__main__":
    print("=" * 60)
    print("OBJECT DETECTION MODULE - DEMO")
    print("=" * 60)
    print()
    
    if not YOLO_AVAILABLE:
        print("❌ YOLO no está disponible")
        print("   Instala con: pip install ultralytics")
        exit(1)
    
    print("Controles:")
    print("  'q' - Salir")
    print("  's' - Guardar screenshot")
    print("  'i' - Mostrar info")
    print("  'm' - Filtrar solo objetos de mesa")
    print()
    
    # Inicializar detector
    detector = ObjectDetector(
        model_name="yolov8n.pt",  # Modelo más ligero
        confidence_threshold=0.5,
        device="auto"
    )
    
    if not detector.is_initialized:
        print("❌ No se pudo inicializar el detector")
        exit(1)
    
    # Inicializar cámara
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ No se pudo abrir la cámara")
        exit(1)
    
    # Configurar cámara
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    screenshot_count = 0
    filter_mesa = False
    
    try:
        while True:
            # Capturar frame
            ret, frame = cap.read()
            
            if not ret:
                print("⚠️ No se pudo leer frame")
                continue
            
            # Detectar y dibujar
            if filter_mesa:
                mesa_ids = get_mesa_class_ids()
                annotated_frame, detections = detector.detect_and_draw(
                    frame, 
                    classes=mesa_ids
                )
            else:
                annotated_frame, detections = detector.detect_and_draw(frame)
            
            # Mostrar frame
            cv2.imshow('Object Detection - YOLO', annotated_frame)
            
            # Manejar teclas
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                print("\n👋 Saliendo...")
                break
            elif key == ord('s'):
                screenshot_count += 1
                cv2.imwrite(f'detection_{screenshot_count}.jpg', annotated_frame)
                print(f"📸 Screenshot guardado ({screenshot_count})")
            elif key == ord('i'):
                stats = detector.get_stats()
                print(f"\n📊 Stats:")
                print(f"   Frames procesados: {stats['frames_processed']}")
                print(f"   Detecciones totales: {stats['total_detections']}")
                print(f"   Promedio por frame: {stats['avg_detections_per_frame']:.2f}")
            elif key == ord('m'):
                filter_mesa = not filter_mesa
                status = "ACTIVADO" if filter_mesa else "DESACTIVADO"
                print(f"\n🔍 Filtro objetos de mesa: {status}")
    
    except KeyboardInterrupt:
        print("\n⚠️ Interrupción detectada")
    
    finally:
        detector.release()
        cap.release()
        cv2.destroyAllWindows()
        print("\n✅ Demo finalizado")
