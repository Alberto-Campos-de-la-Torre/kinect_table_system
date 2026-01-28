"""
Intrinsic Calibration
=====================
Calibración de parámetros intrínsecos del Kinect usando tablero de ajedrez
"""

import numpy as np
import cv2
import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class CameraIntrinsics:
    """Parámetros intrínsecos de la cámara"""
    # Matriz de cámara (3x3)
    fx: float = 594.21      # Focal length X
    fy: float = 591.04      # Focal length Y
    cx: float = 339.5       # Centro óptico X
    cy: float = 242.7       # Centro óptico Y
    
    # Coeficientes de distorsión [k1, k2, p1, p2, k3]
    k1: float = 0.0
    k2: float = 0.0
    p1: float = 0.0
    p2: float = 0.0
    k3: float = 0.0
    
    # Resolución
    width: int = 640
    height: int = 480
    
    # Metadatos
    calibration_date: str = ""
    reprojection_error: float = 0.0
    num_images_used: int = 0
    
    @property
    def camera_matrix(self) -> np.ndarray:
        """Obtener matriz de cámara 3x3"""
        return np.array([
            [self.fx, 0, self.cx],
            [0, self.fy, self.cy],
            [0, 0, 1]
        ], dtype=np.float64)
    
    @property
    def dist_coeffs(self) -> np.ndarray:
        """Obtener coeficientes de distorsión"""
        return np.array([self.k1, self.k2, self.p1, self.p2, self.k3], dtype=np.float64)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CameraIntrinsics':
        """Crear desde diccionario"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def save(self, filepath: str):
        """Guardar a archivo JSON"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Calibración guardada en: {filepath}")
    
    @classmethod
    def load(cls, filepath: str) -> 'CameraIntrinsics':
        """Cargar desde archivo JSON"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        logger.info(f"Calibración cargada desde: {filepath}")
        return cls.from_dict(data)


class IntrinsicCalibrator:
    """
    Calibrador de parámetros intrínsecos usando tablero de ajedrez
    
    Proceso:
    1. Capturar múltiples imágenes del tablero desde diferentes ángulos
    2. Detectar esquinas del tablero en cada imagen
    3. Calcular parámetros intrínsecos con OpenCV
    4. Validar y guardar calibración
    """
    
    # Valores por defecto del Kinect v1
    DEFAULT_INTRINSICS = CameraIntrinsics(
        fx=594.21, fy=591.04,
        cx=339.5, cy=242.7,
        width=640, height=480
    )
    
    def __init__(
        self,
        board_size: Tuple[int, int] = (9, 6),  # Esquinas internas del tablero
        square_size: float = 0.025,  # Tamaño del cuadrado en metros (25mm)
        min_images: int = 10,
        max_images: int = 30
    ):
        """
        Inicializar calibrador
        
        Args:
            board_size: (columnas, filas) de esquinas internas
            square_size: Tamaño del cuadrado en metros
            min_images: Mínimo de imágenes para calibración
            max_images: Máximo de imágenes a usar
        """
        self.board_size = board_size
        self.square_size = square_size
        self.min_images = min_images
        self.max_images = max_images
        
        # Puntos del tablero en coordenadas del objeto (3D)
        self.objp = np.zeros((board_size[0] * board_size[1], 3), np.float32)
        self.objp[:, :2] = np.mgrid[0:board_size[0], 0:board_size[1]].T.reshape(-1, 2)
        self.objp *= square_size
        
        # Listas para puntos detectados
        self.object_points: List[np.ndarray] = []  # Puntos 3D del tablero
        self.image_points: List[np.ndarray] = []   # Puntos 2D en imagen
        self.images: List[np.ndarray] = []         # Imágenes capturadas
        
        # Criterios de terminación para cornerSubPix
        self.criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        
        # Resultado de calibración
        self.intrinsics: Optional[CameraIntrinsics] = None
        
        logger.info(f"IntrinsicCalibrator inicializado")
        logger.info(f"  Tablero: {board_size[0]}x{board_size[1]} esquinas")
        logger.info(f"  Tamaño cuadrado: {square_size*1000:.1f}mm")
    
    def detect_corners(self, image: np.ndarray) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Detectar esquinas del tablero en una imagen
        
        Args:
            image: Imagen BGR o grayscale
            
        Returns:
            (éxito, esquinas) - esquinas refinadas si se detectaron
        """
        # Convertir a grayscale si es necesario
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Detectar esquinas del tablero
        ret, corners = cv2.findChessboardCorners(
            gray, self.board_size,
            cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
        )
        
        if ret:
            # Refinar posición de esquinas
            corners_refined = cv2.cornerSubPix(
                gray, corners, (11, 11), (-1, -1), self.criteria
            )
            return True, corners_refined
        
        return False, None
    
    def add_image(self, image: np.ndarray) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Agregar imagen al conjunto de calibración
        
        Args:
            image: Imagen con tablero visible
            
        Returns:
            (éxito, imagen con esquinas dibujadas)
        """
        if len(self.images) >= self.max_images:
            logger.warning(f"Máximo de imágenes alcanzado ({self.max_images})")
            return False, None
        
        ret, corners = self.detect_corners(image)
        
        if ret:
            self.object_points.append(self.objp)
            self.image_points.append(corners)
            self.images.append(image.copy())
            
            # Dibujar esquinas para visualización
            vis_image = image.copy()
            cv2.drawChessboardCorners(vis_image, self.board_size, corners, ret)
            
            logger.info(f"Imagen {len(self.images)} añadida")
            return True, vis_image
        
        return False, None
    
    def calibrate(self) -> Tuple[bool, Optional[CameraIntrinsics]]:
        """
        Ejecutar calibración con las imágenes capturadas
        
        Returns:
            (éxito, intrinsics)
        """
        if len(self.images) < self.min_images:
            logger.error(f"Insuficientes imágenes: {len(self.images)}/{self.min_images}")
            return False, None
        
        # Obtener tamaño de imagen
        h, w = self.images[0].shape[:2]
        
        logger.info(f"Calibrando con {len(self.images)} imágenes...")
        
        # Calibrar cámara
        ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
            self.object_points,
            self.image_points,
            (w, h),
            None, None,
            flags=cv2.CALIB_FIX_K3  # Fijar k3 para evitar sobreajuste
        )
        
        if not ret:
            logger.error("Calibración fallida")
            return False, None
        
        # Calcular error de reproyección
        total_error = 0
        for i in range(len(self.object_points)):
            img_points2, _ = cv2.projectPoints(
                self.object_points[i], rvecs[i], tvecs[i],
                camera_matrix, dist_coeffs
            )
            error = cv2.norm(self.image_points[i], img_points2, cv2.NORM_L2)
            total_error += error ** 2
        
        mean_error = np.sqrt(total_error / len(self.object_points))
        
        # Crear objeto de intrinsics
        from datetime import datetime
        self.intrinsics = CameraIntrinsics(
            fx=camera_matrix[0, 0],
            fy=camera_matrix[1, 1],
            cx=camera_matrix[0, 2],
            cy=camera_matrix[1, 2],
            k1=dist_coeffs[0, 0] if dist_coeffs.ndim > 1 else dist_coeffs[0],
            k2=dist_coeffs[0, 1] if dist_coeffs.ndim > 1 else dist_coeffs[1],
            p1=dist_coeffs[0, 2] if dist_coeffs.ndim > 1 else dist_coeffs[2],
            p2=dist_coeffs[0, 3] if dist_coeffs.ndim > 1 else dist_coeffs[3],
            k3=dist_coeffs[0, 4] if dist_coeffs.ndim > 1 and dist_coeffs.shape[1] > 4 else 0,
            width=w,
            height=h,
            calibration_date=datetime.now().isoformat(),
            reprojection_error=mean_error,
            num_images_used=len(self.images)
        )
        
        logger.info(f"✅ Calibración exitosa")
        logger.info(f"   Error de reproyección: {mean_error:.4f} píxeles")
        logger.info(f"   fx={self.intrinsics.fx:.2f}, fy={self.intrinsics.fy:.2f}")
        logger.info(f"   cx={self.intrinsics.cx:.2f}, cy={self.intrinsics.cy:.2f}")
        
        return True, self.intrinsics
    
    def undistort_image(self, image: np.ndarray) -> np.ndarray:
        """
        Corregir distorsión de una imagen usando la calibración
        
        Args:
            image: Imagen con distorsión
            
        Returns:
            Imagen corregida
        """
        if self.intrinsics is None:
            logger.warning("No hay calibración disponible")
            return image
        
        return cv2.undistort(
            image,
            self.intrinsics.camera_matrix,
            self.intrinsics.dist_coeffs
        )
    
    def get_optimal_camera_matrix(self, alpha: float = 1.0) -> np.ndarray:
        """
        Obtener matriz de cámara óptima para undistort
        
        Args:
            alpha: 0 = sin píxeles negros, 1 = todos los píxeles originales
            
        Returns:
            Nueva matriz de cámara
        """
        if self.intrinsics is None:
            return None
        
        new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
            self.intrinsics.camera_matrix,
            self.intrinsics.dist_coeffs,
            (self.intrinsics.width, self.intrinsics.height),
            alpha
        )
        return new_camera_matrix
    
    def reset(self):
        """Reiniciar calibrador"""
        self.object_points.clear()
        self.image_points.clear()
        self.images.clear()
        self.intrinsics = None
        logger.info("Calibrador reiniciado")
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del calibrador"""
        return {
            'images_captured': len(self.images),
            'min_images': self.min_images,
            'max_images': self.max_images,
            'ready_to_calibrate': len(self.images) >= self.min_images,
            'calibrated': self.intrinsics is not None,
            'reprojection_error': self.intrinsics.reprojection_error if self.intrinsics else None
        }


def load_or_create_intrinsics(filepath: str = "data/camera_intrinsics.json") -> CameraIntrinsics:
    """
    Cargar calibración existente o usar valores por defecto
    
    Args:
        filepath: Ruta al archivo de calibración
        
    Returns:
        CameraIntrinsics
    """
    if os.path.exists(filepath):
        try:
            return CameraIntrinsics.load(filepath)
        except Exception as e:
            logger.warning(f"Error cargando calibración: {e}")
    
    logger.info("Usando calibración por defecto para Kinect v1")
    return IntrinsicCalibrator.DEFAULT_INTRINSICS


# Test del módulo
if __name__ == "__main__":
    print("=" * 60)
    print("INTRINSIC CALIBRATION - TEST")
    print("=" * 60)
    
    # Crear calibrador
    calibrator = IntrinsicCalibrator(board_size=(9, 6), square_size=0.025)
    
    print(f"\nEstado inicial:")
    print(f"  {calibrator.get_status()}")
    
    # Simular imágenes con tablero (en producción se usarían imágenes reales)
    print("\nPara calibrar en producción:")
    print("  1. Imprimir tablero de ajedrez 9x6")
    print("  2. Capturar 10-20 imágenes desde diferentes ángulos")
    print("  3. Ejecutar calibrator.calibrate()")
    print("  4. Guardar con intrinsics.save('data/camera_intrinsics.json')")
    
    # Probar valores por defecto
    intrinsics = load_or_create_intrinsics()
    print(f"\nIntrinsics por defecto:")
    print(f"  fx={intrinsics.fx:.2f}, fy={intrinsics.fy:.2f}")
    print(f"  cx={intrinsics.cx:.2f}, cy={intrinsics.cy:.2f}")
    
    print("\n✅ Test completado")
