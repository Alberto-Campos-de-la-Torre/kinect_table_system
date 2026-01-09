#!/usr/bin/env python3
"""
Script para descargar modelos pre-entrenados
==============================================
Este script descarga los modelos necesarios para el sistema
"""

import sys
from pathlib import Path
import urllib.request
from tqdm import tqdm


class DownloadProgressBar(tqdm):
    """Barra de progreso para descargas"""
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def download_file(url: str, output_path: Path):
    """
    Descargar archivo con barra de progreso
    
    Args:
        url: URL del archivo a descargar
        output_path: Ruta donde guardar el archivo
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc=output_path.name) as t:
        urllib.request.urlretrieve(url, filename=output_path, reporthook=t.update_to)


def main():
    """Función principal"""
    print("=" * 60)
    print("DESCARGA DE MODELOS - KINECT TABLE SYSTEM")
    print("=" * 60)
    print()
    
    # Directorio de modelos
    models_dir = Path(__file__).parent.parent / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Modelos a descargar
    models = {
        "YOLOv8 Nano": {
            "url": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt",
            "filename": "yolov8n.pt",
            "size": "~6 MB"
        },
        # Descomentar para descargar modelos adicionales
        # "YOLOv8 Small": {
        #     "url": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt",
        #     "filename": "yolov8s.pt",
        #     "size": "~22 MB"
        # },
    }
    
    print(f"Modelos a descargar: {len(models)}")
    print(f"Destino: {models_dir}")
    print()
    
    # Descargar cada modelo
    for model_name, model_info in models.items():
        output_path = models_dir / model_info["filename"]
        
        # Verificar si ya existe
        if output_path.exists():
            print(f"✓ {model_name} ya existe - Omitiendo")
            continue
        
        print(f"Descargando {model_name} ({model_info['size']})...")
        try:
            download_file(model_info["url"], output_path)
            print(f"✓ {model_name} descargado exitosamente")
        except Exception as e:
            print(f"✗ Error descargando {model_name}: {e}")
            return 1
        
        print()
    
    print("=" * 60)
    print("DESCARGA COMPLETADA")
    print("=" * 60)
    print()
    print("Los modelos están listos para usar en:")
    print(f"  {models_dir}")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
