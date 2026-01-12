"""
Point Cloud Streaming
=====================
Streaming optimizado de nubes de puntos para WebSocket
- Compresión de datos
- Serialización eficiente
- Control de rate/bandwidth
"""

import numpy as np
import base64
import json
import zlib
import struct
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
import time

from .point_cloud_generator import PointCloud

logger = logging.getLogger(__name__)


@dataclass
class StreamingConfig:
    """Configuración de streaming"""
    max_points: int = 50000          # Máximo de puntos a enviar
    compression: bool = True          # Usar compresión zlib
    compression_level: int = 6        # Nivel de compresión (1-9)
    quantize_position: bool = True    # Cuantizar posiciones
    quantize_bits: int = 16           # Bits para cuantización
    include_colors: bool = True       # Incluir colores
    target_fps: int = 15              # FPS objetivo de streaming


class PointCloudStreamer:
    """
    Streamer optimizado para nubes de puntos via WebSocket
    
    Formatos de salida:
    - JSON: Compatible, más grande
    - Binary: Compacto, más eficiente
    """
    
    def __init__(self, config: StreamingConfig = None):
        """
        Inicializar streamer
        
        Args:
            config: Configuración de streaming
        """
        self.config = config or StreamingConfig()
        
        # Estadísticas
        self.stats = {
            'frames_sent': 0,
            'bytes_sent': 0,
            'avg_compression_ratio': 0.0,
            'last_encode_time': 0.0
        }
        
        # Control de rate
        self.last_send_time = 0
        self.min_interval = 1.0 / self.config.target_fps
        
        logger.info(f"PointCloudStreamer inicializado")
        logger.info(f"  Max puntos: {self.config.max_points}")
        logger.info(f"  Compresión: {self.config.compression}")
        logger.info(f"  Target FPS: {self.config.target_fps}")
    
    def should_send(self) -> bool:
        """Verificar si se debe enviar un nuevo frame según el rate limit"""
        current_time = time.time()
        if current_time - self.last_send_time >= self.min_interval:
            self.last_send_time = current_time
            return True
        return False
    
    def encode_json(self, pc: PointCloud, include_stats: bool = True) -> Dict[str, Any]:
        """
        Codificar nube de puntos a formato JSON
        
        Args:
            pc: Nube de puntos
            include_stats: Incluir estadísticas
            
        Returns:
            Diccionario JSON-serializable
        """
        start_time = time.time()
        
        if pc.num_points == 0:
            return {
                'type': 'pointcloud',
                'format': 'json',
                'num_points': 0,
                'points': [],
                'colors': []
            }
        
        # Limitar número de puntos si es necesario
        points = pc.points
        colors = pc.colors
        
        if pc.num_points > self.config.max_points:
            indices = np.random.choice(pc.num_points, self.config.max_points, replace=False)
            points = points[indices]
            if colors is not None:
                colors = colors[indices]
        
        # Convertir a listas
        points_list = points.tolist()
        colors_list = colors.tolist() if colors is not None and self.config.include_colors else None
        
        result = {
            'type': 'pointcloud',
            'format': 'json',
            'num_points': len(points_list),
            'points': points_list,
            'colors': colors_list,
            'bounds': pc.get_bounds(),
            'timestamp': pc.timestamp
        }
        
        if include_stats:
            result['stats'] = {
                'original_points': pc.num_points,
                'encode_time_ms': (time.time() - start_time) * 1000
            }
        
        self.stats['last_encode_time'] = (time.time() - start_time) * 1000
        
        return result
    
    def encode_binary(self, pc: PointCloud) -> Dict[str, Any]:
        """
        Codificar nube de puntos a formato binario comprimido
        
        Formato binario:
        - Header: num_points (4 bytes), has_colors (1 byte)
        - Points: N * 3 * float32 (o cuantizado si está habilitado)
        - Colors: N * 3 * uint8 (si tiene colores)
        
        Args:
            pc: Nube de puntos
            
        Returns:
            Diccionario con datos binarios en base64
        """
        start_time = time.time()
        
        if pc.num_points == 0:
            return {
                'type': 'pointcloud',
                'format': 'binary',
                'num_points': 0,
                'data': ''
            }
        
        # Limitar puntos
        points = pc.points
        colors = pc.colors
        
        if pc.num_points > self.config.max_points:
            indices = np.random.choice(pc.num_points, self.config.max_points, replace=False)
            points = points[indices]
            if colors is not None:
                colors = colors[indices]
        
        num_points = len(points)
        has_colors = colors is not None and self.config.include_colors
        
        # Cuantizar posiciones si está habilitado
        if self.config.quantize_position:
            points_data = self._quantize_points(points)
        else:
            points_data = points.astype(np.float32).tobytes()
        
        # Preparar colores (uint8)
        if has_colors:
            colors_uint8 = (colors * 255).clip(0, 255).astype(np.uint8)
            colors_data = colors_uint8.tobytes()
        else:
            colors_data = b''
        
        # Crear header
        header = struct.pack('<IB', num_points, 1 if has_colors else 0)
        
        # Combinar datos
        raw_data = header + points_data + colors_data
        raw_size = len(raw_data)
        
        # Comprimir si está habilitado
        if self.config.compression:
            compressed_data = zlib.compress(raw_data, self.config.compression_level)
            compression_ratio = raw_size / len(compressed_data)
        else:
            compressed_data = raw_data
            compression_ratio = 1.0
        
        # Codificar a base64
        encoded_data = base64.b64encode(compressed_data).decode('ascii')
        
        # Actualizar estadísticas
        encode_time = (time.time() - start_time) * 1000
        self.stats['frames_sent'] += 1
        self.stats['bytes_sent'] += len(encoded_data)
        self.stats['avg_compression_ratio'] = (
            self.stats['avg_compression_ratio'] * 0.9 + compression_ratio * 0.1
        )
        self.stats['last_encode_time'] = encode_time
        
        # Calcular bounds para el frontend
        bounds = {
            'min': points.min(axis=0).tolist(),
            'max': points.max(axis=0).tolist()
        }
        
        return {
            'type': 'pointcloud',
            'format': 'binary',
            'num_points': num_points,
            'data': encoded_data,
            'compressed': self.config.compression,
            'quantized': self.config.quantize_position,
            'has_colors': has_colors,
            'bounds': bounds,
            'timestamp': pc.timestamp,
            'stats': {
                'raw_size': raw_size,
                'compressed_size': len(compressed_data),
                'compression_ratio': compression_ratio,
                'encode_time_ms': encode_time
            }
        }
    
    def _quantize_points(self, points: np.ndarray) -> bytes:
        """
        Cuantizar puntos a enteros de N bits para compresión
        
        Args:
            points: Array de puntos (N, 3)
            
        Returns:
            Bytes cuantizados
        """
        # Calcular rango de valores
        min_vals = points.min(axis=0)
        max_vals = points.max(axis=0)
        range_vals = max_vals - min_vals + 1e-6
        
        # Cuantizar a uint16 (0-65535)
        max_val = (1 << self.config.quantize_bits) - 1
        normalized = (points - min_vals) / range_vals
        quantized = (normalized * max_val).astype(np.uint16)
        
        # Empaquetar: primero los bounds (6 floats), luego los puntos cuantizados
        bounds_data = np.array([*min_vals, *range_vals], dtype=np.float32).tobytes()
        points_data = quantized.tobytes()
        
        return bounds_data + points_data
    
    def encode_optimized(
        self,
        pc: PointCloud,
        color_mode: str = 'rgb'
    ) -> Dict[str, Any]:
        """
        Codificación optimizada para streaming en tiempo real
        
        Args:
            pc: Nube de puntos
            color_mode: 'rgb', 'depth', 'height', 'none'
            
        Returns:
            Datos optimizados para WebSocket
        """
        if not self.should_send():
            return None
        
        return self.encode_binary(pc)
    
    def decode_binary(self, data: Dict[str, Any]) -> PointCloud:
        """
        Decodificar datos binarios a PointCloud
        
        Args:
            data: Datos recibidos del WebSocket
            
        Returns:
            PointCloud reconstruida
        """
        if data.get('num_points', 0) == 0:
            return PointCloud(points=np.empty((0, 3)), num_points=0)
        
        # Decodificar base64
        compressed_data = base64.b64decode(data['data'])
        
        # Descomprimir si es necesario
        if data.get('compressed', False):
            raw_data = zlib.decompress(compressed_data)
        else:
            raw_data = compressed_data
        
        # Parsear header
        num_points, has_colors = struct.unpack('<IB', raw_data[:5])
        offset = 5
        
        # Parsear puntos
        if data.get('quantized', False):
            # Leer bounds (6 floats)
            bounds = np.frombuffer(raw_data[offset:offset+24], dtype=np.float32)
            min_vals = bounds[:3]
            range_vals = bounds[3:6]
            offset += 24
            
            # Leer puntos cuantizados
            points_size = num_points * 3 * 2  # uint16
            quantized = np.frombuffer(
                raw_data[offset:offset+points_size],
                dtype=np.uint16
            ).reshape(-1, 3)
            offset += points_size
            
            # Dequantizar
            max_val = (1 << 16) - 1
            points = (quantized.astype(np.float32) / max_val) * range_vals + min_vals
        else:
            points_size = num_points * 3 * 4  # float32
            points = np.frombuffer(
                raw_data[offset:offset+points_size],
                dtype=np.float32
            ).reshape(-1, 3)
            offset += points_size
        
        # Parsear colores
        colors = None
        if has_colors:
            colors_size = num_points * 3
            colors_uint8 = np.frombuffer(
                raw_data[offset:offset+colors_size],
                dtype=np.uint8
            ).reshape(-1, 3)
            colors = colors_uint8.astype(np.float32) / 255.0
        
        return PointCloud(
            points=points,
            colors=colors,
            num_points=num_points,
            timestamp=data.get('timestamp', 0)
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de streaming"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Resetear estadísticas"""
        self.stats = {
            'frames_sent': 0,
            'bytes_sent': 0,
            'avg_compression_ratio': 0.0,
            'last_encode_time': 0.0
        }


# Funciones de utilidad para el servidor
def create_pointcloud_message(
    pc: PointCloud,
    streamer: PointCloudStreamer = None,
    format: str = 'binary'
) -> Optional[Dict[str, Any]]:
    """
    Crear mensaje de nube de puntos para WebSocket
    
    Args:
        pc: Nube de puntos
        streamer: Streamer configurado (opcional)
        format: 'binary' o 'json'
        
    Returns:
        Mensaje listo para enviar
    """
    if streamer is None:
        streamer = PointCloudStreamer()
    
    if format == 'binary':
        return streamer.encode_binary(pc)
    else:
        return streamer.encode_json(pc)


# Test del módulo
if __name__ == "__main__":
    print("=" * 60)
    print("POINT CLOUD STREAMING - TEST")
    print("=" * 60)
    
    # Crear nube de puntos de prueba
    num_points = 30000
    points = np.random.randn(num_points, 3).astype(np.float32)
    points[:, 2] += 2  # Desplazar en Z
    colors = np.random.rand(num_points, 3).astype(np.float32)
    
    pc = PointCloud(
        points=points,
        colors=colors,
        num_points=num_points,
        timestamp=time.time()
    )
    
    print(f"\nNube de prueba: {pc.num_points} puntos")
    
    # Crear streamer
    config = StreamingConfig(
        max_points=20000,
        compression=True,
        quantize_position=True
    )
    streamer = PointCloudStreamer(config)
    
    # Test JSON encoding
    start = time.time()
    json_data = streamer.encode_json(pc)
    json_time = (time.time() - start) * 1000
    json_size = len(json.dumps(json_data))
    print(f"\nJSON encoding:")
    print(f"  Tiempo: {json_time:.1f}ms")
    print(f"  Tamaño: {json_size / 1024:.1f} KB")
    print(f"  Puntos: {json_data['num_points']}")
    
    # Test Binary encoding
    start = time.time()
    binary_data = streamer.encode_binary(pc)
    binary_time = (time.time() - start) * 1000
    binary_size = len(binary_data['data'])
    print(f"\nBinary encoding:")
    print(f"  Tiempo: {binary_time:.1f}ms")
    print(f"  Tamaño: {binary_size / 1024:.1f} KB")
    print(f"  Compresión: {binary_data['stats']['compression_ratio']:.1f}x")
    print(f"  Puntos: {binary_data['num_points']}")
    
    # Test decode
    start = time.time()
    decoded_pc = streamer.decode_binary(binary_data)
    decode_time = (time.time() - start) * 1000
    print(f"\nDecode:")
    print(f"  Tiempo: {decode_time:.1f}ms")
    print(f"  Puntos recuperados: {decoded_pc.num_points}")
    
    # Verificar integridad
    if decoded_pc.num_points > 0:
        error = np.abs(decoded_pc.points[:100] - points[:100]).max()
        print(f"  Error máximo (100 puntos): {error:.6f}m")
    
    print(f"\nStats del streamer:")
    for k, v in streamer.get_stats().items():
        print(f"  {k}: {v}")
    
    print("\n✅ Test completado")
