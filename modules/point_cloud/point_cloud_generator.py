"""
Point Cloud Generator
=====================
Genera nube de puntos 3D desde datos de profundidad del Kinect Xbox 360
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class PointCloud:
    """Estructura de datos para una nube de puntos"""
    points: np.ndarray          # (N, 3) coordenadas XYZ en metros
    colors: Optional[np.ndarray] = None  # (N, 3) colores RGB normalizados [0-1]
    normals: Optional[np.ndarray] = None  # (N, 3) vectores normales
    num_points: int = 0
    timestamp: float = 0.0
    
    def __post_init__(self):
        self.num_points = len(self.points) if self.points is not None else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario para serialización"""
        result = {
            'num_points': self.num_points,
            'timestamp': self.timestamp,
            'bounds': self.get_bounds() if self.num_points > 0 else None
        }
        return result
    
    def get_bounds(self) -> Dict[str, Tuple[float, float]]:
        """Obtener límites de la nube de puntos"""
        if self.num_points == 0:
            return {'x': (0, 0), 'y': (0, 0), 'z': (0, 0)}
        
        return {
            'x': (float(self.points[:, 0].min()), float(self.points[:, 0].max())),
            'y': (float(self.points[:, 1].min()), float(self.points[:, 1].max())),
            'z': (float(self.points[:, 2].min()), float(self.points[:, 2].max()))
        }


class PointCloudGenerator:
    """
    Generador de nube de puntos 3D desde datos de profundidad del Kinect
    
    Parámetros intrínsecos del Kinect Xbox 360:
    - Resolución: 640x480
    - FOV horizontal: ~57°
    - FOV vertical: ~43°
    - Rango de profundidad: 0.8m - 4.0m
    """
    
    # Parámetros intrínsecos del Kinect Xbox 360 (valores aproximados)
    # Estos valores pueden ajustarse con calibración
    KINECT_V1_INTRINSICS = {
        'fx': 594.21,    # Focal length X (calibrado para Kinect v1)
        'fy': 591.04,    # Focal length Y
        'cx': 339.5,     # Centro óptico X
        'cy': 242.7,     # Centro óptico Y
        'width': 640,
        'height': 480,
        'depth_scale': 1.0,     # libfreenect devuelve valores raw 11-bit
        'min_depth': 0.4,       # Profundidad mínima válida (metros)
        'max_depth': 8.0,       # Profundidad máxima válida (metros)
        'use_freenect_conversion': True  # Usar conversión especial para libfreenect
    }
    
    def __init__(
        self,
        intrinsics: Dict[str, float] = None,
        depth_scale: float = None,
        min_depth: float = None,
        max_depth: float = None
    ):
        """
        Inicializar generador de nube de puntos
        
        Args:
            intrinsics: Parámetros intrínsecos de la cámara
            depth_scale: Factor de escala de profundidad (mm -> m)
            min_depth: Profundidad mínima válida (metros)
            max_depth: Profundidad máxima válida (metros)
        """
        self.intrinsics = intrinsics or self.KINECT_V1_INTRINSICS.copy()
        
        if depth_scale is not None:
            self.intrinsics['depth_scale'] = depth_scale
        if min_depth is not None:
            self.intrinsics['min_depth'] = min_depth
        if max_depth is not None:
            self.intrinsics['max_depth'] = max_depth
        
        # Pre-calcular coordenadas de píxeles para eficiencia
        self._pixel_coords = None
        self._init_pixel_coords()
        
        logger.info(f"PointCloudGenerator inicializado")
        logger.info(f"  Resolución: {self.intrinsics['width']}x{self.intrinsics['height']}")
        logger.info(f"  Rango depth: {self.intrinsics['min_depth']:.1f}m - {self.intrinsics['max_depth']:.1f}m")
    
    def _init_pixel_coords(self):
        """Pre-calcular coordenadas de píxeles (u, v) para eficiencia"""
        width = self.intrinsics['width']
        height = self.intrinsics['height']
        
        # Crear grid de coordenadas de píxeles
        u = np.arange(width)
        v = np.arange(height)
        u, v = np.meshgrid(u, v)
        
        self._pixel_coords = (u.flatten(), v.flatten())
    
    def depth_to_pointcloud(
        self,
        depth: np.ndarray,
        rgb: np.ndarray = None,
        downsample: int = 1
    ) -> PointCloud:
        """
        Convertir imagen de profundidad a nube de puntos 3D
        
        Args:
            depth: Imagen de profundidad (H, W) uint16 en mm
            rgb: Imagen RGB opcional (H, W, 3) uint8 para colorizar puntos
            downsample: Factor de reducción de resolución (1 = sin reducción)
            
        Returns:
            PointCloud con coordenadas 3D y colores opcionales
        """
        if depth is None or depth.size == 0:
            return PointCloud(points=np.empty((0, 3)), num_points=0)
        
        # Aplicar downsampling si es necesario
        if downsample > 1:
            depth = depth[::downsample, ::downsample]
            if rgb is not None:
                rgb = rgb[::downsample, ::downsample]
        
        # Obtener dimensiones
        height, width = depth.shape
        
        # Ajustar parámetros intrínsecos para el downsampling
        fx = self.intrinsics['fx'] / downsample
        fy = self.intrinsics['fy'] / downsample
        cx = self.intrinsics['cx'] / downsample
        cy = self.intrinsics['cy'] / downsample
        
        # Crear grid de coordenadas de píxeles
        u, v = np.meshgrid(np.arange(width), np.arange(height))
        
        # Convertir profundidad a metros
        depth_float = depth.astype(np.float32)
        
        if self.intrinsics.get('use_freenect_conversion', False):
            # Conversión especial para Kinect v1 con libfreenect (modo 11BIT raw)
            # Los datos raw son valores de 11-bit (0-2047)
            # Valor 2047 = saturado/inválido
            
            # Usar la fórmula estándar de conversión para Kinect v1
            # depth_meters = 1.0 / (raw * -0.0030711016 + 3.3309495161)
            # Pero necesitamos evitar división por cero
            
            raw = depth_float
            # Marcar valores inválidos (0 y 2047)
            invalid_mask = (raw <= 0) | (raw >= 2047)
            
            # Convertir valores válidos
            # Fórmula alternativa más robusta basada en la documentación de OpenKinect
            raw_safe = np.where(invalid_mask, 1, raw)  # Evitar div by zero
            depth_meters = 0.1236 * np.tan(raw_safe / 2842.5 + 1.1863)
            
            # Marcar inválidos como 0
            depth_meters = np.where(invalid_mask, 0, depth_meters)
            
        else:
            # Conversión estándar (profundidad en mm)
            depth_meters = depth_float / self.intrinsics['depth_scale']
        
        # Filtrar valores de profundidad inválidos
        valid_mask = (
            (depth_meters > self.intrinsics['min_depth']) &
            (depth_meters < self.intrinsics['max_depth']) &
            (depth > 0) &  # Excluir ceros
            (depth < 2047) &  # Excluir saturados (para modo 11BIT)
            np.isfinite(depth_meters)  # Excluir infinitos y NaN
        )
        
        # Calcular coordenadas 3D usando modelo pinhole inverso
        # X = (u - cx) * Z / fx
        # Y = (v - cy) * Z / fy
        # Z = depth
        z = depth_meters[valid_mask]
        x = (u[valid_mask] - cx) * z / fx
        y = (v[valid_mask] - cy) * z / fy
        
        # Apilar coordenadas
        points = np.stack([x, y, z], axis=-1).astype(np.float32)
        
        # Extraer colores si están disponibles
        colors = None
        if rgb is not None:
            colors = rgb[valid_mask].astype(np.float32) / 255.0
            # Asegurar orden BGR -> RGB si es necesario (OpenCV usa BGR)
            if colors.shape[-1] == 3:
                colors = colors[:, ::-1]  # BGR -> RGB
        
        return PointCloud(
            points=points,
            colors=colors,
            num_points=len(points)
        )
    
    def generate_colored_pointcloud(
        self,
        depth: np.ndarray,
        rgb: np.ndarray,
        downsample: int = 2
    ) -> PointCloud:
        """
        Generar nube de puntos con colores RGB
        
        Args:
            depth: Imagen de profundidad
            rgb: Imagen RGB
            downsample: Factor de reducción
            
        Returns:
            PointCloud coloreada
        """
        return self.depth_to_pointcloud(depth, rgb, downsample)
    
    def generate_depth_colored_pointcloud(
        self,
        depth: np.ndarray,
        colormap: str = 'jet',
        downsample: int = 2
    ) -> PointCloud:
        """
        Generar nube de puntos con colores basados en profundidad
        
        Args:
            depth: Imagen de profundidad
            colormap: Mapa de colores ('jet', 'viridis', 'plasma', 'turbo')
            downsample: Factor de reducción
            
        Returns:
            PointCloud coloreada por profundidad
        """
        import cv2
        
        # Generar nube de puntos base
        pc = self.depth_to_pointcloud(depth, None, downsample)
        
        if pc.num_points == 0:
            return pc
        
        # Normalizar profundidad para colormap
        z_values = pc.points[:, 2]
        z_min, z_max = z_values.min(), z_values.max()
        z_normalized = ((z_values - z_min) / (z_max - z_min + 1e-6) * 255).astype(np.uint8)
        
        # Seleccionar colormap
        colormaps = {
            'jet': cv2.COLORMAP_JET,
            'viridis': cv2.COLORMAP_VIRIDIS,
            'plasma': cv2.COLORMAP_PLASMA,
            'turbo': cv2.COLORMAP_TURBO,
            'hot': cv2.COLORMAP_HOT,
            'cool': cv2.COLORMAP_COOL
        }
        cmap = colormaps.get(colormap, cv2.COLORMAP_JET)
        
        # Aplicar colormap
        colors_bgr = cv2.applyColorMap(z_normalized.reshape(-1, 1), cmap)
        colors = colors_bgr.reshape(-1, 3)[:, ::-1].astype(np.float32) / 255.0  # BGR -> RGB
        
        pc.colors = colors
        return pc
    
    def generate_height_colored_pointcloud(
        self,
        depth: np.ndarray,
        floor_height: float = 0.0,
        colormap: str = 'viridis',
        downsample: int = 2
    ) -> PointCloud:
        """
        Generar nube de puntos con colores basados en altura sobre el suelo
        
        Args:
            depth: Imagen de profundidad
            floor_height: Altura del suelo en metros
            colormap: Mapa de colores
            downsample: Factor de reducción
            
        Returns:
            PointCloud coloreada por altura
        """
        import cv2
        
        pc = self.depth_to_pointcloud(depth, None, downsample)
        
        if pc.num_points == 0:
            return pc
        
        # En el sistema de coordenadas del Kinect, Y apunta hacia abajo
        # Invertir Y para que sea altura
        heights = -pc.points[:, 1] - floor_height
        
        # Normalizar altura
        h_min, h_max = heights.min(), heights.max()
        h_normalized = ((heights - h_min) / (h_max - h_min + 1e-6) * 255).astype(np.uint8)
        
        # Aplicar colormap
        colormaps = {
            'jet': cv2.COLORMAP_JET,
            'viridis': cv2.COLORMAP_VIRIDIS,
            'plasma': cv2.COLORMAP_PLASMA,
            'turbo': cv2.COLORMAP_TURBO
        }
        cmap = colormaps.get(colormap, cv2.COLORMAP_VIRIDIS)
        
        colors_bgr = cv2.applyColorMap(h_normalized.reshape(-1, 1), cmap)
        colors = colors_bgr.reshape(-1, 3)[:, ::-1].astype(np.float32) / 255.0
        
        pc.colors = colors
        return pc
    
    def set_intrinsics(
        self,
        fx: float = None,
        fy: float = None,
        cx: float = None,
        cy: float = None
    ):
        """
        Actualizar parámetros intrínsecos de la cámara
        
        Args:
            fx, fy: Focal lengths
            cx, cy: Centro óptico
        """
        if fx is not None:
            self.intrinsics['fx'] = fx
        if fy is not None:
            self.intrinsics['fy'] = fy
        if cx is not None:
            self.intrinsics['cx'] = cx
        if cy is not None:
            self.intrinsics['cy'] = cy
        
        logger.info(f"Intrínsecos actualizados: fx={self.intrinsics['fx']}, fy={self.intrinsics['fy']}")
    
    def set_depth_range(self, min_depth: float, max_depth: float):
        """
        Establecer rango de profundidad válido
        
        Args:
            min_depth: Profundidad mínima en metros
            max_depth: Profundidad máxima en metros
        """
        self.intrinsics['min_depth'] = min_depth
        self.intrinsics['max_depth'] = max_depth
        logger.info(f"Rango depth: {min_depth:.1f}m - {max_depth:.1f}m")
    
    def get_intrinsics(self) -> Dict[str, float]:
        """Obtener parámetros intrínsecos actuales"""
        return self.intrinsics.copy()


# Test del módulo
if __name__ == "__main__":
    import time
    
    print("=" * 60)
    print("POINT CLOUD GENERATOR - TEST")
    print("=" * 60)
    
    # Crear generador
    generator = PointCloudGenerator()
    
    # Crear depth frame de prueba (simulado)
    depth = np.random.randint(500, 4000, (480, 640), dtype=np.uint16)
    rgb = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # Generar nube de puntos
    start = time.time()
    pc = generator.generate_colored_pointcloud(depth, rgb, downsample=2)
    elapsed = time.time() - start
    
    print(f"\nResultados:")
    print(f"  Puntos generados: {pc.num_points:,}")
    print(f"  Tiempo: {elapsed*1000:.1f}ms")
    print(f"  Límites: {pc.get_bounds()}")
    
    # Test de diferentes modos de color
    pc_depth = generator.generate_depth_colored_pointcloud(depth, 'jet', downsample=4)
    print(f"\n  PC por profundidad: {pc_depth.num_points:,} puntos")
    
    pc_height = generator.generate_height_colored_pointcloud(depth, 0, 'viridis', downsample=4)
    print(f"  PC por altura: {pc_height.num_points:,} puntos")
    
    print("\n✅ Test completado")
