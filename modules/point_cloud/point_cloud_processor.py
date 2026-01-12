"""
Point Cloud Processor
=====================
Procesamiento y filtrado de nubes de puntos 3D
- Filtrado de outliers
- Segmentación de planos (RANSAC)
- Clustering de objetos (DBSCAN)
- Downsampling
"""

import numpy as np
from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass
import logging

from .point_cloud_generator import PointCloud

logger = logging.getLogger(__name__)


@dataclass
class PlaneModel:
    """Modelo de plano detectado"""
    coefficients: np.ndarray  # [a, b, c, d] para ax + by + cz + d = 0
    inliers: np.ndarray       # Índices de puntos que pertenecen al plano
    normal: np.ndarray        # Vector normal del plano
    center: np.ndarray        # Centro del plano
    
    @property
    def num_inliers(self) -> int:
        return len(self.inliers)


@dataclass 
class Cluster:
    """Cluster de puntos (objeto segmentado)"""
    points: np.ndarray        # Coordenadas de los puntos
    colors: Optional[np.ndarray] = None
    label: int = -1           # ID del cluster
    centroid: np.ndarray = None
    bbox: Tuple[np.ndarray, np.ndarray] = None  # (min_corner, max_corner)
    
    def __post_init__(self):
        if self.centroid is None and len(self.points) > 0:
            self.centroid = self.points.mean(axis=0)
        if self.bbox is None and len(self.points) > 0:
            self.bbox = (self.points.min(axis=0), self.points.max(axis=0))


class PointCloudProcessor:
    """
    Procesador de nubes de puntos con algoritmos de filtrado y segmentación
    """
    
    def __init__(self):
        """Inicializar procesador"""
        logger.info("PointCloudProcessor inicializado")
    
    # ==========================================
    # Filtrado de outliers
    # ==========================================
    
    def statistical_outlier_removal(
        self,
        pc: PointCloud,
        k_neighbors: int = 20,
        std_ratio: float = 2.0
    ) -> PointCloud:
        """
        Filtrar outliers usando análisis estadístico de distancias
        
        Args:
            pc: Nube de puntos de entrada
            k_neighbors: Número de vecinos para análisis
            std_ratio: Umbral de desviación estándar
            
        Returns:
            PointCloud filtrada
        """
        if pc.num_points < k_neighbors:
            return pc
        
        try:
            from sklearn.neighbors import NearestNeighbors
            
            # Encontrar k vecinos más cercanos
            nbrs = NearestNeighbors(n_neighbors=k_neighbors, algorithm='auto')
            nbrs.fit(pc.points)
            distances, _ = nbrs.kneighbors(pc.points)
            
            # Calcular distancia media a vecinos (excluyendo el punto mismo)
            mean_distances = distances[:, 1:].mean(axis=1)
            
            # Calcular umbral usando media y desviación estándar
            global_mean = mean_distances.mean()
            global_std = mean_distances.std()
            threshold = global_mean + std_ratio * global_std
            
            # Filtrar puntos
            inlier_mask = mean_distances < threshold
            
            filtered_points = pc.points[inlier_mask]
            filtered_colors = pc.colors[inlier_mask] if pc.colors is not None else None
            
            logger.debug(f"SOR: {pc.num_points} -> {len(filtered_points)} puntos")
            
            return PointCloud(
                points=filtered_points,
                colors=filtered_colors,
                num_points=len(filtered_points),
                timestamp=pc.timestamp
            )
            
        except ImportError:
            logger.warning("sklearn no disponible, saltando filtrado SOR")
            return pc
    
    def radius_outlier_removal(
        self,
        pc: PointCloud,
        radius: float = 0.05,
        min_neighbors: int = 5
    ) -> PointCloud:
        """
        Filtrar outliers por radio: eliminar puntos con pocos vecinos
        
        Args:
            pc: Nube de puntos
            radius: Radio de búsqueda en metros
            min_neighbors: Mínimo de vecinos para mantener el punto
            
        Returns:
            PointCloud filtrada
        """
        if pc.num_points < min_neighbors:
            return pc
        
        try:
            from sklearn.neighbors import BallTree
            
            tree = BallTree(pc.points)
            counts = tree.query_radius(pc.points, r=radius, count_only=True)
            
            # El conteo incluye el punto mismo, así que comparamos con min_neighbors + 1
            inlier_mask = counts >= (min_neighbors + 1)
            
            filtered_points = pc.points[inlier_mask]
            filtered_colors = pc.colors[inlier_mask] if pc.colors is not None else None
            
            return PointCloud(
                points=filtered_points,
                colors=filtered_colors,
                num_points=len(filtered_points),
                timestamp=pc.timestamp
            )
            
        except ImportError:
            logger.warning("sklearn no disponible, saltando filtrado ROR")
            return pc
    
    # ==========================================
    # Downsampling
    # ==========================================
    
    def voxel_downsample(
        self,
        pc: PointCloud,
        voxel_size: float = 0.01
    ) -> PointCloud:
        """
        Reducir densidad de puntos usando voxel grid
        
        Args:
            pc: Nube de puntos
            voxel_size: Tamaño del voxel en metros
            
        Returns:
            PointCloud reducida
        """
        if pc.num_points == 0:
            return pc
        
        # Calcular índices de voxel para cada punto
        voxel_indices = np.floor(pc.points / voxel_size).astype(np.int32)
        
        # Crear claves únicas para cada voxel
        # Usar un hash simple basado en coordenadas
        multipliers = np.array([1, 1e6, 1e12])
        voxel_keys = (voxel_indices * multipliers).sum(axis=1)
        
        # Encontrar voxels únicos y promediar puntos dentro de cada uno
        unique_keys, inverse_indices = np.unique(voxel_keys, return_inverse=True)
        
        # Calcular centroide de cada voxel
        num_voxels = len(unique_keys)
        downsampled_points = np.zeros((num_voxels, 3), dtype=np.float32)
        counts = np.zeros(num_voxels)
        
        np.add.at(downsampled_points, inverse_indices, pc.points)
        np.add.at(counts, inverse_indices, 1)
        
        downsampled_points /= counts[:, np.newaxis]
        
        # Promediar colores si existen
        downsampled_colors = None
        if pc.colors is not None:
            downsampled_colors = np.zeros((num_voxels, 3), dtype=np.float32)
            np.add.at(downsampled_colors, inverse_indices, pc.colors)
            downsampled_colors /= counts[:, np.newaxis]
        
        logger.debug(f"Voxel: {pc.num_points} -> {num_voxels} puntos")
        
        return PointCloud(
            points=downsampled_points,
            colors=downsampled_colors,
            num_points=num_voxels,
            timestamp=pc.timestamp
        )
    
    def random_downsample(
        self,
        pc: PointCloud,
        target_points: int = 10000
    ) -> PointCloud:
        """
        Reducir puntos mediante muestreo aleatorio
        
        Args:
            pc: Nube de puntos
            target_points: Número objetivo de puntos
            
        Returns:
            PointCloud reducida
        """
        if pc.num_points <= target_points:
            return pc
        
        indices = np.random.choice(pc.num_points, target_points, replace=False)
        
        return PointCloud(
            points=pc.points[indices],
            colors=pc.colors[indices] if pc.colors is not None else None,
            num_points=target_points,
            timestamp=pc.timestamp
        )
    
    # ==========================================
    # Segmentación de planos (RANSAC)
    # ==========================================
    
    def segment_plane_ransac(
        self,
        pc: PointCloud,
        distance_threshold: float = 0.01,
        max_iterations: int = 1000,
        min_inliers_ratio: float = 0.1
    ) -> Tuple[PlaneModel, PointCloud]:
        """
        Segmentar plano dominante usando RANSAC
        
        Args:
            pc: Nube de puntos
            distance_threshold: Distancia máxima al plano para ser inlier (metros)
            max_iterations: Iteraciones máximas de RANSAC
            min_inliers_ratio: Ratio mínimo de inliers para aceptar plano
            
        Returns:
            Tuple de (PlaneModel, PointCloud sin el plano)
        """
        if pc.num_points < 3:
            return None, pc
        
        points = pc.points
        best_inliers = np.array([])
        best_plane = None
        min_inliers = int(pc.num_points * min_inliers_ratio)
        
        for _ in range(max_iterations):
            # Seleccionar 3 puntos aleatorios
            sample_indices = np.random.choice(pc.num_points, 3, replace=False)
            p1, p2, p3 = points[sample_indices]
            
            # Calcular normal del plano
            v1 = p2 - p1
            v2 = p3 - p1
            normal = np.cross(v1, v2)
            norm = np.linalg.norm(normal)
            
            if norm < 1e-10:
                continue
            
            normal /= norm
            d = -np.dot(normal, p1)
            
            # Calcular distancias de todos los puntos al plano
            distances = np.abs(np.dot(points, normal) + d)
            
            # Encontrar inliers
            inliers = np.where(distances < distance_threshold)[0]
            
            if len(inliers) > len(best_inliers):
                best_inliers = inliers
                best_plane = np.append(normal, d)
        
        if len(best_inliers) < min_inliers:
            logger.debug("No se encontró plano significativo")
            return None, pc
        
        # Crear modelo de plano
        plane_model = PlaneModel(
            coefficients=best_plane,
            inliers=best_inliers,
            normal=best_plane[:3],
            center=points[best_inliers].mean(axis=0)
        )
        
        # Crear nube de puntos sin el plano
        outlier_mask = np.ones(pc.num_points, dtype=bool)
        outlier_mask[best_inliers] = False
        
        remaining_pc = PointCloud(
            points=points[outlier_mask],
            colors=pc.colors[outlier_mask] if pc.colors is not None else None,
            num_points=outlier_mask.sum(),
            timestamp=pc.timestamp
        )
        
        logger.debug(f"Plano detectado: {plane_model.num_inliers} inliers")
        
        return plane_model, remaining_pc
    
    def segment_table_plane(
        self,
        pc: PointCloud,
        distance_threshold: float = 0.02,
        min_height: float = 0.5,
        max_height: float = 1.5
    ) -> Tuple[Optional[PlaneModel], PointCloud]:
        """
        Segmentar plano de mesa (plano horizontal dominante)
        
        Args:
            pc: Nube de puntos
            distance_threshold: Tolerancia de distancia
            min_height: Altura mínima de la mesa (metros)
            max_height: Altura máxima de la mesa (metros)
            
        Returns:
            Tuple de (PlaneModel de la mesa, puntos sobre la mesa)
        """
        # Filtrar puntos por altura (en sistema Kinect, Y es hacia abajo)
        # Invertimos la lógica: Y más negativo = más alto
        height_mask = (pc.points[:, 1] > -max_height) & (pc.points[:, 1] < -min_height)
        
        if height_mask.sum() < 100:
            logger.debug("No hay suficientes puntos en el rango de altura de mesa")
            return None, pc
        
        # Crear subconjunto de puntos en el rango de altura
        filtered_pc = PointCloud(
            points=pc.points[height_mask],
            colors=pc.colors[height_mask] if pc.colors is not None else None,
            num_points=height_mask.sum()
        )
        
        # Buscar plano horizontal (normal apuntando hacia arriba: Y negativo)
        plane_model, remaining = self.segment_plane_ransac(
            filtered_pc,
            distance_threshold=distance_threshold,
            max_iterations=500
        )
        
        if plane_model is None:
            return None, pc
        
        # Verificar que el plano es horizontal (normal casi vertical)
        normal = plane_model.normal
        verticality = abs(normal[1])  # Y component
        
        if verticality < 0.8:  # No es suficientemente horizontal
            logger.debug(f"Plano no horizontal: verticality={verticality:.2f}")
            return None, pc
        
        return plane_model, remaining
    
    # ==========================================
    # Clustering de objetos (DBSCAN)
    # ==========================================
    
    def cluster_objects_dbscan(
        self,
        pc: PointCloud,
        eps: float = 0.05,
        min_samples: int = 10,
        min_cluster_size: int = 50
    ) -> List[Cluster]:
        """
        Segmentar objetos usando DBSCAN clustering
        
        Args:
            pc: Nube de puntos
            eps: Distancia máxima entre puntos del mismo cluster
            min_samples: Mínimo de puntos para formar core point
            min_cluster_size: Tamaño mínimo de cluster para aceptarlo
            
        Returns:
            Lista de Clusters detectados
        """
        if pc.num_points < min_samples:
            return []
        
        try:
            from sklearn.cluster import DBSCAN
            
            # Ejecutar DBSCAN
            clustering = DBSCAN(eps=eps, min_samples=min_samples)
            labels = clustering.fit_predict(pc.points)
            
            # Extraer clusters (ignorar ruido con label -1)
            unique_labels = set(labels)
            unique_labels.discard(-1)
            
            clusters = []
            for label in unique_labels:
                mask = labels == label
                cluster_points = pc.points[mask]
                
                if len(cluster_points) < min_cluster_size:
                    continue
                
                cluster_colors = pc.colors[mask] if pc.colors is not None else None
                
                clusters.append(Cluster(
                    points=cluster_points,
                    colors=cluster_colors,
                    label=label
                ))
            
            logger.debug(f"DBSCAN: {len(clusters)} clusters encontrados")
            
            return clusters
            
        except ImportError:
            logger.warning("sklearn no disponible, no se puede hacer clustering")
            return []
    
    # ==========================================
    # Pipeline de procesamiento
    # ==========================================
    
    def process_for_table(
        self,
        pc: PointCloud,
        voxel_size: float = 0.01,
        table_height_range: Tuple[float, float] = (0.5, 1.2)
    ) -> Dict:
        """
        Pipeline completo para detección de mesa y objetos
        
        Args:
            pc: Nube de puntos de entrada
            voxel_size: Tamaño de voxel para downsampling
            table_height_range: (min, max) altura de mesa en metros
            
        Returns:
            Dict con 'table_plane', 'objects', 'processed_pc'
        """
        result = {
            'table_plane': None,
            'objects': [],
            'processed_pc': pc,
            'stats': {}
        }
        
        if pc.num_points == 0:
            return result
        
        # 1. Downsampling
        pc_downsampled = self.voxel_downsample(pc, voxel_size)
        result['stats']['points_after_voxel'] = pc_downsampled.num_points
        
        # 2. Filtrado de outliers
        pc_filtered = self.statistical_outlier_removal(pc_downsampled, k_neighbors=15, std_ratio=1.5)
        result['stats']['points_after_filter'] = pc_filtered.num_points
        
        # 3. Segmentar plano de mesa
        table_plane, remaining_pc = self.segment_table_plane(
            pc_filtered,
            min_height=table_height_range[0],
            max_height=table_height_range[1]
        )
        result['table_plane'] = table_plane
        result['stats']['table_inliers'] = table_plane.num_inliers if table_plane else 0
        
        # 4. Clustering de objetos sobre la mesa
        if remaining_pc.num_points > 50:
            objects = self.cluster_objects_dbscan(remaining_pc, eps=0.03, min_samples=10)
            result['objects'] = objects
            result['stats']['num_objects'] = len(objects)
        
        result['processed_pc'] = pc_filtered
        
        return result


# Test del módulo
if __name__ == "__main__":
    import time
    
    print("=" * 60)
    print("POINT CLOUD PROCESSOR - TEST")
    print("=" * 60)
    
    processor = PointCloudProcessor()
    
    # Crear nube de puntos de prueba
    # Simular un plano (mesa) con algunos objetos encima
    n_plane = 5000
    n_objects = 500
    
    # Puntos del plano (z ≈ 1.5m, y = 0)
    plane_points = np.random.randn(n_plane, 3).astype(np.float32) * 0.5
    plane_points[:, 2] = 1.5 + np.random.randn(n_plane) * 0.01  # Z constante
    
    # Puntos de objetos (encima del plano)
    obj_points = np.random.randn(n_objects, 3).astype(np.float32) * 0.1
    obj_points[:, 2] = 1.3  # Más cerca de la cámara
    obj_points[:, 0] += 0.3  # Desplazado a un lado
    
    all_points = np.vstack([plane_points, obj_points])
    
    pc = PointCloud(
        points=all_points,
        num_points=len(all_points)
    )
    
    print(f"\nNube de prueba: {pc.num_points} puntos")
    
    # Test voxel downsampling
    start = time.time()
    pc_voxel = processor.voxel_downsample(pc, voxel_size=0.02)
    print(f"\nVoxel downsample: {pc_voxel.num_points} puntos ({(time.time()-start)*1000:.1f}ms)")
    
    # Test RANSAC
    start = time.time()
    plane, remaining = processor.segment_plane_ransac(pc, distance_threshold=0.02)
    elapsed = time.time() - start
    
    if plane:
        print(f"\nRANSAC ({elapsed*1000:.1f}ms):")
        print(f"  Inliers: {plane.num_inliers}")
        print(f"  Normal: {plane.normal}")
        print(f"  Restantes: {remaining.num_points}")
    
    # Test DBSCAN
    try:
        start = time.time()
        clusters = processor.cluster_objects_dbscan(remaining, eps=0.05, min_samples=10)
        print(f"\nDBSCAN ({(time.time()-start)*1000:.1f}ms):")
        print(f"  Clusters: {len(clusters)}")
        for i, c in enumerate(clusters):
            print(f"    Cluster {i}: {len(c.points)} puntos")
    except Exception as e:
        print(f"\nDBSCAN error: {e}")
    
    print("\n✅ Test completado")
