"""
Coordinate Mapper
=================
Transformaciones de coordenadas entre sistemas:
- Kinect 3D (X, Y, Z en metros)
- Imagen 2D (u, v en píxeles)
- Mesa/Pantalla (x, y normalizado o en píxeles de pantalla)
"""

import numpy as np
import cv2
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Tuple, Optional, Dict, Any, List
from pathlib import Path
import logging

from .intrinsic_calibration import CameraIntrinsics, load_or_create_intrinsics

logger = logging.getLogger(__name__)


@dataclass
class CalibrationData:
    """Datos completos de calibración del sistema"""
    
    # Intrinsics de la cámara
    intrinsics: CameraIntrinsics = None
    
    # Transformación del plano de la mesa
    table_plane: np.ndarray = None  # [a, b, c, d] para ax + by + cz + d = 0
    table_height: float = 0.0       # Altura de la mesa en metros
    
    # Homografía mesa -> pantalla
    homography: np.ndarray = None   # Matriz 3x3
    homography_inverse: np.ndarray = None
    
    # Puntos de calibración (4 esquinas)
    kinect_points: np.ndarray = None   # Puntos 3D del Kinect (4x3)
    screen_points: np.ndarray = None   # Puntos 2D de pantalla (4x2)
    
    # Región de interés (ROI) de la mesa
    roi_min: np.ndarray = None  # [x_min, y_min, z_min]
    roi_max: np.ndarray = None  # [x_max, y_max, z_max]
    
    # Transformación de rotación/traslación
    rotation_matrix: np.ndarray = None  # 3x3
    translation_vector: np.ndarray = None  # 3x1
    
    # Flags de orientación
    flip_x: bool = False
    flip_y: bool = True   # Kinect v1 típicamente tiene Y invertido
    flip_z: bool = False
    
    # Metadatos
    calibration_date: str = ""
    screen_width: int = 1920
    screen_height: int = 1080
    
    def __post_init__(self):
        if self.intrinsics is None:
            self.intrinsics = load_or_create_intrinsics()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario serializable"""
        def convert(obj):
            if obj is None:
                return None
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, CameraIntrinsics):
                return obj.to_dict()
            elif isinstance(obj, (np.floating, np.float32, np.float64)):
                return float(obj)
            elif isinstance(obj, (np.integer, np.int32, np.int64)):
                return int(obj)
            elif isinstance(obj, (list, tuple)):
                return [convert(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            return obj
        
        return {k: convert(v) for k, v in asdict(self).items()}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CalibrationData':
        """Crear desde diccionario"""
        def convert(key, value):
            if value is None:
                return None
            if key == 'intrinsics':
                return CameraIntrinsics.from_dict(value)
            if key in ['table_plane', 'homography', 'homography_inverse', 
                      'kinect_points', 'screen_points', 'roi_min', 'roi_max',
                      'rotation_matrix', 'translation_vector']:
                return np.array(value) if value else None
            return value
        
        converted = {k: convert(k, v) for k, v in data.items() 
                    if k in cls.__dataclass_fields__}
        return cls(**converted)
    
    def save(self, filepath: str):
        """Guardar calibración a archivo"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Calibración guardada en: {filepath}")
    
    @classmethod
    def load(cls, filepath: str) -> 'CalibrationData':
        """Cargar calibración desde archivo"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        logger.info(f"Calibración cargada desde: {filepath}")
        return cls.from_dict(data)


class CoordinateMapper:
    """
    Mapeador de coordenadas entre sistemas de referencia
    
    Sistemas soportados:
    - kinect_3d: Coordenadas 3D del Kinect (metros)
    - image_2d: Coordenadas de imagen (píxeles)
    - screen_2d: Coordenadas de pantalla (píxeles)
    - table_2d: Coordenadas normalizadas de mesa (0-1)
    """
    
    def __init__(self, calibration: CalibrationData = None):
        """
        Inicializar mapeador
        
        Args:
            calibration: Datos de calibración (opcional)
        """
        self.calibration = calibration or CalibrationData()
        logger.info("CoordinateMapper inicializado")
    
    # ==========================================
    # Transformaciones básicas
    # ==========================================
    
    def kinect_3d_to_image_2d(
        self, 
        points_3d: np.ndarray
    ) -> np.ndarray:
        """
        Proyectar puntos 3D del Kinect a coordenadas de imagen 2D
        
        Args:
            points_3d: Array (N, 3) de puntos XYZ en metros
            
        Returns:
            Array (N, 2) de puntos UV en píxeles
        """
        if points_3d.ndim == 1:
            points_3d = points_3d.reshape(1, -1)
        
        intrinsics = self.calibration.intrinsics
        
        # Aplicar flip si es necesario
        x = points_3d[:, 0].copy()
        y = points_3d[:, 1].copy()
        z = points_3d[:, 2].copy()
        
        if self.calibration.flip_x:
            x = -x
        if self.calibration.flip_y:
            y = -y
        if self.calibration.flip_z:
            z = -z
        
        # Proyección pinhole: u = fx * X/Z + cx, v = fy * Y/Z + cy
        # Evitar división por cero
        z_safe = np.where(z > 0.001, z, 0.001)
        
        u = intrinsics.fx * x / z_safe + intrinsics.cx
        v = intrinsics.fy * y / z_safe + intrinsics.cy
        
        return np.stack([u, v], axis=-1)
    
    def image_2d_to_kinect_3d(
        self,
        points_2d: np.ndarray,
        depths: np.ndarray
    ) -> np.ndarray:
        """
        Convertir puntos 2D de imagen a 3D del Kinect dado profundidad
        
        Args:
            points_2d: Array (N, 2) de puntos UV en píxeles
            depths: Array (N,) de profundidades en metros
            
        Returns:
            Array (N, 3) de puntos XYZ en metros
        """
        if points_2d.ndim == 1:
            points_2d = points_2d.reshape(1, -1)
        if depths.ndim == 0:
            depths = np.array([depths])
        
        intrinsics = self.calibration.intrinsics
        
        u = points_2d[:, 0]
        v = points_2d[:, 1]
        z = depths
        
        # Modelo pinhole inverso
        x = (u - intrinsics.cx) * z / intrinsics.fx
        y = (v - intrinsics.cy) * z / intrinsics.fy
        
        # Aplicar flip inverso si es necesario
        if self.calibration.flip_x:
            x = -x
        if self.calibration.flip_y:
            y = -y
        if self.calibration.flip_z:
            z = -z
        
        return np.stack([x, y, z], axis=-1)
    
    # ==========================================
    # Transformaciones mesa/pantalla
    # ==========================================
    
    def kinect_3d_to_screen_2d(
        self,
        points_3d: np.ndarray
    ) -> np.ndarray:
        """
        Convertir puntos 3D del Kinect a coordenadas de pantalla
        
        Args:
            points_3d: Array (N, 3) de puntos XYZ
            
        Returns:
            Array (N, 2) de puntos de pantalla
        """
        if self.calibration.homography is None:
            logger.warning("No hay homografía calibrada, usando proyección simple")
            return self.kinect_3d_to_image_2d(points_3d)
        
        if points_3d.ndim == 1:
            points_3d = points_3d.reshape(1, -1)
        
        # Primero proyectar a 2D de imagen
        points_2d = self.kinect_3d_to_image_2d(points_3d)
        
        # Aplicar homografía
        points_2d_h = np.hstack([points_2d, np.ones((len(points_2d), 1))])
        screen_points_h = (self.calibration.homography @ points_2d_h.T).T
        
        # Normalizar coordenadas homogéneas
        screen_points = screen_points_h[:, :2] / screen_points_h[:, 2:3]
        
        return screen_points
    
    def screen_2d_to_kinect_3d(
        self,
        screen_points: np.ndarray,
        default_depth: float = 1.0
    ) -> np.ndarray:
        """
        Convertir coordenadas de pantalla a 3D del Kinect (en plano de mesa)
        
        Args:
            screen_points: Array (N, 2) de puntos de pantalla
            default_depth: Profundidad por defecto si no hay plano de mesa
            
        Returns:
            Array (N, 3) de puntos XYZ
        """
        if self.calibration.homography_inverse is None:
            logger.warning("No hay homografía inversa calibrada")
            return None
        
        if screen_points.ndim == 1:
            screen_points = screen_points.reshape(1, -1)
        
        # Aplicar homografía inversa
        screen_h = np.hstack([screen_points, np.ones((len(screen_points), 1))])
        image_h = (self.calibration.homography_inverse @ screen_h.T).T
        image_points = image_h[:, :2] / image_h[:, 2:3]
        
        # Convertir a 3D usando altura de mesa
        depth = self.calibration.table_height if self.calibration.table_height > 0 else default_depth
        depths = np.full(len(image_points), depth)
        
        return self.image_2d_to_kinect_3d(image_points, depths)
    
    def kinect_3d_to_table_normalized(
        self,
        points_3d: np.ndarray
    ) -> np.ndarray:
        """
        Convertir puntos 3D a coordenadas normalizadas de mesa (0-1)
        
        Args:
            points_3d: Array (N, 3) de puntos XYZ
            
        Returns:
            Array (N, 2) de coordenadas normalizadas (0-1)
        """
        screen_points = self.kinect_3d_to_screen_2d(points_3d)
        
        # Normalizar a rango 0-1
        normalized = screen_points.copy()
        normalized[:, 0] /= self.calibration.screen_width
        normalized[:, 1] /= self.calibration.screen_height
        
        return np.clip(normalized, 0, 1)
    
    # ==========================================
    # Transformación de orientación
    # ==========================================
    
    def apply_rotation(self, points_3d: np.ndarray) -> np.ndarray:
        """
        Aplicar rotación calibrada a puntos 3D
        
        Args:
            points_3d: Array (N, 3) de puntos XYZ
            
        Returns:
            Array (N, 3) de puntos rotados
        """
        if self.calibration.rotation_matrix is None:
            return points_3d
        
        if points_3d.ndim == 1:
            points_3d = points_3d.reshape(1, -1)
        
        rotated = (self.calibration.rotation_matrix @ points_3d.T).T
        
        if self.calibration.translation_vector is not None:
            rotated += self.calibration.translation_vector.flatten()
        
        return rotated
    
    def set_flip(self, flip_x: bool = None, flip_y: bool = None, flip_z: bool = None):
        """
        Configurar inversión de ejes
        
        Args:
            flip_x, flip_y, flip_z: True para invertir el eje
        """
        if flip_x is not None:
            self.calibration.flip_x = flip_x
        if flip_y is not None:
            self.calibration.flip_y = flip_y
        if flip_z is not None:
            self.calibration.flip_z = flip_z
        
        logger.info(f"Flip configurado: X={self.calibration.flip_x}, "
                   f"Y={self.calibration.flip_y}, Z={self.calibration.flip_z}")
    
    # ==========================================
    # Calibración de homografía
    # ==========================================
    
    def calibrate_homography(
        self,
        kinect_points_2d: np.ndarray,
        screen_points: np.ndarray
    ) -> bool:
        """
        Calcular homografía de imagen Kinect a pantalla
        
        Args:
            kinect_points_2d: 4+ puntos de imagen del Kinect (N, 2)
            screen_points: 4+ puntos correspondientes de pantalla (N, 2)
            
        Returns:
            True si la calibración fue exitosa
        """
        if len(kinect_points_2d) < 4 or len(screen_points) < 4:
            logger.error("Se necesitan al menos 4 puntos para la homografía")
            return False
        
        kinect_points_2d = np.array(kinect_points_2d, dtype=np.float32)
        screen_points = np.array(screen_points, dtype=np.float32)
        
        # Calcular homografía
        H, mask = cv2.findHomography(kinect_points_2d, screen_points, cv2.RANSAC, 5.0)
        
        if H is None:
            logger.error("No se pudo calcular homografía")
            return False
        
        self.calibration.homography = H
        self.calibration.homography_inverse = np.linalg.inv(H)
        
        logger.info("✅ Homografía calibrada correctamente")
        return True
    
    def calibrate_from_corners(
        self,
        kinect_corners_3d: np.ndarray,
        screen_size: Tuple[int, int] = (1920, 1080)
    ) -> bool:
        """
        Calibrar usando 4 esquinas 3D del Kinect
        
        Las esquinas deben ser en orden: top-left, top-right, bottom-right, bottom-left
        
        Args:
            kinect_corners_3d: 4 esquinas 3D (4, 3)
            screen_size: (width, height) de la pantalla
            
        Returns:
            True si la calibración fue exitosa
        """
        self.calibration.screen_width = screen_size[0]
        self.calibration.screen_height = screen_size[1]
        
        # Guardar puntos 3D
        self.calibration.kinect_points = np.array(kinect_corners_3d)
        
        # Definir esquinas de pantalla
        w, h = screen_size
        screen_corners = np.array([
            [0, 0],      # top-left
            [w, 0],      # top-right
            [w, h],      # bottom-right
            [0, h]       # bottom-left
        ], dtype=np.float32)
        self.calibration.screen_points = screen_corners
        
        # Proyectar puntos 3D a 2D
        kinect_2d = self.kinect_3d_to_image_2d(kinect_corners_3d)
        
        # Calcular homografía
        return self.calibrate_homography(kinect_2d, screen_corners)
    
    # ==========================================
    # Utilidades
    # ==========================================
    
    def is_point_in_roi(self, point_3d: np.ndarray) -> bool:
        """Verificar si un punto está dentro del ROI"""
        if self.calibration.roi_min is None or self.calibration.roi_max is None:
            return True
        
        return np.all(point_3d >= self.calibration.roi_min) and \
               np.all(point_3d <= self.calibration.roi_max)
    
    def set_roi(self, min_point: np.ndarray, max_point: np.ndarray):
        """Establecer región de interés"""
        self.calibration.roi_min = np.array(min_point)
        self.calibration.roi_max = np.array(max_point)
        logger.info(f"ROI establecido: {min_point} -> {max_point}")
    
    def get_calibration_status(self) -> Dict[str, Any]:
        """Obtener estado de calibración"""
        return {
            'has_intrinsics': self.calibration.intrinsics is not None,
            'has_homography': self.calibration.homography is not None,
            'has_table_plane': self.calibration.table_plane is not None,
            'has_roi': self.calibration.roi_min is not None,
            'flip': {
                'x': self.calibration.flip_x,
                'y': self.calibration.flip_y,
                'z': self.calibration.flip_z
            },
            'screen_size': (self.calibration.screen_width, self.calibration.screen_height)
        }
    
    def save_calibration(self, filepath: str = "data/calibration_data.json"):
        """Guardar calibración actual"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self.calibration.save(filepath)
    
    def load_calibration(self, filepath: str = "data/calibration_data.json") -> bool:
        """Cargar calibración desde archivo"""
        if not os.path.exists(filepath):
            logger.warning(f"Archivo de calibración no encontrado: {filepath}")
            return False
        
        try:
            self.calibration = CalibrationData.load(filepath)
            return True
        except Exception as e:
            logger.error(f"Error cargando calibración: {e}")
            return False


# Test del módulo
if __name__ == "__main__":
    print("=" * 60)
    print("COORDINATE MAPPER - TEST")
    print("=" * 60)
    
    # Crear mapper
    mapper = CoordinateMapper()
    
    print(f"\nEstado de calibración:")
    print(f"  {mapper.get_calibration_status()}")
    
    # Test de transformaciones básicas
    point_3d = np.array([[0, 0, 2.0]])  # Punto a 2m de distancia
    
    point_2d = mapper.kinect_3d_to_image_2d(point_3d)
    print(f"\nPunto 3D {point_3d[0]} -> 2D {point_2d[0]}")
    
    # Reconstruir
    point_3d_back = mapper.image_2d_to_kinect_3d(point_2d, np.array([2.0]))
    print(f"Punto 2D {point_2d[0]} + depth=2.0 -> 3D {point_3d_back[0]}")
    
    # Test de flip
    print("\nTest de flip Y (invertir):")
    mapper.set_flip(flip_y=True)
    point_2d_flipped = mapper.kinect_3d_to_image_2d(point_3d)
    print(f"  Con flip_y: {point_2d_flipped[0]}")
    
    print("\n✅ Test completado")
