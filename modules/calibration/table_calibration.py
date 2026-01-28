"""
Table Calibration
=================
Calibración automática y manual del plano de mesa
- Detección automática del plano horizontal
- Calibración manual con marcadores
- Definición de ROI de trabajo
"""

import numpy as np
import cv2
from typing import Tuple, Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class TableCalibrator:
    """
    Calibrador del plano de mesa
    
    Soporta dos modos:
    1. Automático: Detecta el plano horizontal más grande usando RANSAC
    2. Manual: El usuario coloca objetos en marcadores visuales
    """
    
    def __init__(
        self,
        screen_size: Tuple[int, int] = (1920, 1080),
        marker_size: int = 50
    ):
        """
        Inicializar calibrador de mesa
        
        Args:
            screen_size: Tamaño de la pantalla/mesa en píxeles
            marker_size: Tamaño de los marcadores de calibración
        """
        self.screen_size = screen_size
        self.marker_size = marker_size
        
        # Esquinas de calibración (en coordenadas de pantalla)
        self.corner_names = ['top_left', 'top_right', 'bottom_right', 'bottom_left']
        self.screen_corners = self._get_screen_corners()
        
        # Puntos 3D detectados
        self.detected_corners_3d: Dict[str, np.ndarray] = {}
        
        # Plano de mesa detectado
        self.table_plane: Optional[np.ndarray] = None  # [a, b, c, d]
        self.table_normal: Optional[np.ndarray] = None
        self.table_height: float = 0.0
        
        # Estado de calibración
        self.calibration_step = 0
        self.is_calibrated = False
        
        logger.info(f"TableCalibrator inicializado")
        logger.info(f"  Pantalla: {screen_size[0]}x{screen_size[1]}")
    
    def _get_screen_corners(self) -> Dict[str, np.ndarray]:
        """Obtener coordenadas de las 4 esquinas de la pantalla"""
        w, h = self.screen_size
        margin = self.marker_size
        
        return {
            'top_left': np.array([margin, margin]),
            'top_right': np.array([w - margin, margin]),
            'bottom_right': np.array([w - margin, h - margin]),
            'bottom_left': np.array([margin, h - margin])
        }
    
    # ==========================================
    # Calibración manual con marcadores
    # ==========================================
    
    def get_current_marker_position(self) -> Tuple[str, np.ndarray]:
        """
        Obtener posición del marcador actual a mostrar
        
        Returns:
            (nombre de esquina, posición en pantalla)
        """
        if self.calibration_step >= len(self.corner_names):
            return None, None
        
        corner_name = self.corner_names[self.calibration_step]
        position = self.screen_corners[corner_name]
        
        return corner_name, position
    
    def set_corner_point(self, corner_name: str, point_3d: np.ndarray) -> bool:
        """
        Registrar punto 3D para una esquina
        
        Args:
            corner_name: Nombre de la esquina
            point_3d: Coordenadas 3D del Kinect
            
        Returns:
            True si se registró correctamente
        """
        if corner_name not in self.corner_names:
            logger.error(f"Esquina desconocida: {corner_name}")
            return False
        
        self.detected_corners_3d[corner_name] = np.array(point_3d)
        logger.info(f"Esquina '{corner_name}' registrada: {point_3d}")
        
        return True
    
    def advance_calibration_step(self, point_3d: np.ndarray) -> Tuple[bool, str]:
        """
        Avanzar al siguiente paso de calibración
        
        Args:
            point_3d: Punto 3D detectado para el paso actual
            
        Returns:
            (completado, mensaje)
        """
        if self.calibration_step >= len(self.corner_names):
            return True, "Calibración ya completada"
        
        corner_name = self.corner_names[self.calibration_step]
        self.set_corner_point(corner_name, point_3d)
        
        self.calibration_step += 1
        
        if self.calibration_step >= len(self.corner_names):
            # Calcular plano y homografía
            success = self._finalize_calibration()
            if success:
                return True, "✅ Calibración completada"
            else:
                return False, "❌ Error finalizando calibración"
        
        next_corner = self.corner_names[self.calibration_step]
        return False, f"Siguiente: {next_corner}"
    
    def _finalize_calibration(self) -> bool:
        """Finalizar calibración manual calculando plano y homografía"""
        if len(self.detected_corners_3d) < 4:
            logger.error("No hay suficientes esquinas detectadas")
            return False
        
        # Obtener puntos en orden
        points_3d = np.array([
            self.detected_corners_3d[name]
            for name in self.corner_names
        ])
        
        # Calcular plano de la mesa (ajuste de plano a 4 puntos)
        self.table_plane = self._fit_plane(points_3d)
        self.table_normal = self.table_plane[:3]
        
        # Altura media de la mesa (coordenada Z promedio)
        self.table_height = points_3d[:, 2].mean()
        
        self.is_calibrated = True
        
        logger.info(f"Mesa calibrada:")
        logger.info(f"  Plano: {self.table_plane}")
        logger.info(f"  Altura: {self.table_height:.3f}m")
        
        return True
    
    def _fit_plane(self, points: np.ndarray) -> np.ndarray:
        """
        Ajustar plano a conjunto de puntos usando SVD
        
        Args:
            points: Array (N, 3) de puntos
            
        Returns:
            Coeficientes del plano [a, b, c, d]
        """
        # Centrar puntos
        centroid = points.mean(axis=0)
        centered = points - centroid
        
        # SVD para encontrar normal del plano
        _, _, vh = np.linalg.svd(centered)
        normal = vh[-1]  # Último vector singular = normal del plano
        
        # Normalizar
        normal = normal / np.linalg.norm(normal)
        
        # Calcular d: ax + by + cz + d = 0 -> d = -(a*x0 + b*y0 + c*z0)
        d = -np.dot(normal, centroid)
        
        return np.array([normal[0], normal[1], normal[2], d])
    
    # ==========================================
    # Calibración automática con RANSAC
    # ==========================================
    
    def detect_table_plane_ransac(
        self,
        points_3d: np.ndarray,
        distance_threshold: float = 0.02,
        min_inliers_ratio: float = 0.3,
        max_iterations: int = 1000
    ) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Detectar plano de mesa automáticamente usando RANSAC
        
        Args:
            points_3d: Nube de puntos 3D (N, 3)
            distance_threshold: Distancia máxima al plano para ser inlier
            min_inliers_ratio: Ratio mínimo de inliers
            max_iterations: Iteraciones máximas
            
        Returns:
            (éxito, coeficientes del plano [a, b, c, d])
        """
        if len(points_3d) < 100:
            logger.warning("Muy pocos puntos para detectar plano")
            return False, None
        
        n_points = len(points_3d)
        best_inliers = 0
        best_plane = None
        
        for _ in range(max_iterations):
            # Seleccionar 3 puntos aleatorios
            indices = np.random.choice(n_points, 3, replace=False)
            p1, p2, p3 = points_3d[indices]
            
            # Calcular normal del plano
            v1 = p2 - p1
            v2 = p3 - p1
            normal = np.cross(v1, v2)
            norm = np.linalg.norm(normal)
            
            if norm < 1e-10:
                continue
            
            normal /= norm
            d = -np.dot(normal, p1)
            
            # Verificar que sea horizontal (normal apuntando hacia arriba/abajo)
            # En el sistema Kinect, Y suele ser vertical
            verticality = abs(normal[1])
            if verticality < 0.7:  # No es suficientemente horizontal
                continue
            
            # Contar inliers
            distances = np.abs(np.dot(points_3d, normal) + d)
            inliers = np.sum(distances < distance_threshold)
            
            if inliers > best_inliers:
                best_inliers = inliers
                best_plane = np.array([normal[0], normal[1], normal[2], d])
        
        min_inliers = int(n_points * min_inliers_ratio)
        
        if best_inliers < min_inliers:
            logger.warning(f"No se encontró plano válido ({best_inliers}/{min_inliers} inliers)")
            return False, None
        
        self.table_plane = best_plane
        self.table_normal = best_plane[:3]
        
        # Calcular altura del plano
        # Para un punto en el plano: ax + by + cz + d = 0
        # Si x=0, y=0: cz + d = 0 -> z = -d/c
        if abs(best_plane[2]) > 0.001:
            self.table_height = -best_plane[3] / best_plane[2]
        else:
            self.table_height = 0
        
        self.is_calibrated = True
        
        logger.info(f"✅ Plano de mesa detectado automáticamente")
        logger.info(f"   Normal: {self.table_normal}")
        logger.info(f"   Altura: {self.table_height:.3f}m")
        logger.info(f"   Inliers: {best_inliers}/{n_points}")
        
        return True, best_plane
    
    # ==========================================
    # Utilidades de visualización
    # ==========================================
    
    def draw_calibration_marker(
        self,
        image: np.ndarray,
        corner_name: str = None,
        color: Tuple[int, int, int] = (0, 255, 0)
    ) -> np.ndarray:
        """
        Dibujar marcador de calibración en imagen
        
        Args:
            image: Imagen donde dibujar
            corner_name: Esquina específica o None para la actual
            color: Color del marcador (BGR)
            
        Returns:
            Imagen con marcador
        """
        if corner_name is None:
            corner_name, _ = self.get_current_marker_position()
        
        if corner_name is None:
            return image
        
        pos = self.screen_corners[corner_name]
        x, y = int(pos[0]), int(pos[1])
        size = self.marker_size
        
        # Dibujar cruz
        cv2.line(image, (x - size, y), (x + size, y), color, 3)
        cv2.line(image, (x, y - size), (x, y + size), color, 3)
        
        # Dibujar círculo
        cv2.circle(image, (x, y), size // 2, color, 2)
        
        # Etiqueta
        cv2.putText(
            image, corner_name.upper().replace('_', ' '),
            (x - 40, y - size - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2
        )
        
        return image
    
    def draw_all_markers(
        self,
        image: np.ndarray,
        detected_color: Tuple[int, int, int] = (0, 255, 0),
        pending_color: Tuple[int, int, int] = (0, 165, 255)
    ) -> np.ndarray:
        """
        Dibujar todos los marcadores de calibración
        
        Args:
            image: Imagen donde dibujar
            detected_color: Color para esquinas ya detectadas
            pending_color: Color para esquinas pendientes
            
        Returns:
            Imagen con marcadores
        """
        for name in self.corner_names:
            if name in self.detected_corners_3d:
                color = detected_color
            else:
                color = pending_color
            
            image = self.draw_calibration_marker(image, name, color)
        
        return image
    
    def generate_calibration_overlay(
        self,
        width: int = None,
        height: int = None
    ) -> np.ndarray:
        """
        Generar imagen de overlay para calibración
        
        Args:
            width, height: Tamaño de la imagen (por defecto usa screen_size)
            
        Returns:
            Imagen BGRA con fondo transparente
        """
        w = width or self.screen_size[0]
        h = height or self.screen_size[1]
        
        # Crear imagen transparente
        overlay = np.zeros((h, w, 4), dtype=np.uint8)
        
        # Dibujar marcadores
        for i, name in enumerate(self.corner_names):
            pos = self.screen_corners[name]
            x, y = int(pos[0] * w / self.screen_size[0]), int(pos[1] * h / self.screen_size[1])
            size = self.marker_size * w // self.screen_size[0]
            
            # Color según estado
            if name in self.detected_corners_3d:
                color = (0, 255, 0, 255)  # Verde
            elif i == self.calibration_step:
                color = (0, 255, 255, 255)  # Amarillo (actual)
            else:
                color = (128, 128, 128, 200)  # Gris
            
            # Dibujar cruz
            cv2.line(overlay, (x - size, y), (x + size, y), color, 3)
            cv2.line(overlay, (x, y - size), (x, y + size), color, 3)
            cv2.circle(overlay, (x, y), size // 2, color, 2)
        
        return overlay
    
    # ==========================================
    # Estado y reset
    # ==========================================
    
    def reset(self):
        """Reiniciar calibración"""
        self.detected_corners_3d.clear()
        self.table_plane = None
        self.table_normal = None
        self.table_height = 0.0
        self.calibration_step = 0
        self.is_calibrated = False
        logger.info("Calibración de mesa reiniciada")
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado de calibración"""
        # Convertir valores numpy a tipos Python nativos para JSON
        table_height = float(self.table_height) if self.table_height is not None else None
        table_plane = self.table_plane.tolist() if self.table_plane is not None else None
        
        return {
            'is_calibrated': self.is_calibrated,
            'calibration_step': self.calibration_step,
            'total_steps': len(self.corner_names),
            'current_corner': self.corner_names[self.calibration_step] if self.calibration_step < len(self.corner_names) else None,
            'detected_corners': list(self.detected_corners_3d.keys()),
            'table_height': table_height,
            'table_plane': table_plane
        }
    
    def get_calibration_data(self) -> Dict[str, Any]:
        """Obtener datos de calibración para guardar"""
        if not self.is_calibrated:
            return None
        
        return {
            'table_plane': self.table_plane.tolist(),
            'table_height': self.table_height,
            'corners_3d': {k: v.tolist() for k, v in self.detected_corners_3d.items()},
            'screen_size': list(self.screen_size)
        }


# Test del módulo
if __name__ == "__main__":
    print("=" * 60)
    print("TABLE CALIBRATION - TEST")
    print("=" * 60)
    
    # Crear calibrador
    calibrator = TableCalibrator(screen_size=(1920, 1080))
    
    print(f"\nEstado inicial:")
    print(f"  {calibrator.get_status()}")
    
    # Simular calibración manual
    print("\nSimulando calibración manual...")
    
    # Puntos 3D simulados (en una superficie plana)
    test_corners = {
        'top_left': np.array([-0.5, -0.3, 1.5]),
        'top_right': np.array([0.5, -0.3, 1.5]),
        'bottom_right': np.array([0.5, 0.3, 1.5]),
        'bottom_left': np.array([-0.5, 0.3, 1.5])
    }
    
    for name, point in test_corners.items():
        completed, msg = calibrator.advance_calibration_step(point)
        print(f"  {name}: {msg}")
    
    print(f"\nEstado final:")
    print(f"  {calibrator.get_status()}")
    
    # Test RANSAC
    print("\n--- Test RANSAC ---")
    calibrator.reset()
    
    # Generar nube de puntos simulada (plano + ruido)
    n_points = 1000
    points = np.random.randn(n_points, 3) * 0.5
    points[:, 2] = 1.5 + np.random.randn(n_points) * 0.01  # Plano en Z=1.5
    
    success, plane = calibrator.detect_table_plane_ransac(points)
    print(f"  Detección: {'✅' if success else '❌'}")
    if success:
        print(f"  Plano: {plane}")
    
    print("\n✅ Test completado")
