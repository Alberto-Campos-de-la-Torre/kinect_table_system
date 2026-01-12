"""
Script para descargar el modelo hand_landmarker.task de MediaPipe
"""

import urllib.request
from pathlib import Path

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
MODEL_NAME = "hand_landmarker.task"

def download_model(destination: Path = None):
    """Descargar el modelo hand_landmarker.task"""
    if destination is None:
        destination = Path(__file__).parent / MODEL_NAME
    
    destination = Path(destination)
    
    if destination.exists():
        print(f"✅ El modelo ya existe en: {destination}")
        return destination
    
    print(f"Descargando modelo desde: {MODEL_URL}")
    print(f"Destino: {destination}")
    
    try:
        urllib.request.urlretrieve(MODEL_URL, destination)
        print(f"✅ Modelo descargado exitosamente en: {destination}")
        return destination
    except Exception as e:
        print(f"❌ Error al descargar el modelo: {e}")
        print(f"\nPor favor descarga manualmente desde:")
        print(f"{MODEL_URL}")
        print(f"Y colócalo en: {destination}")
        raise

if __name__ == "__main__":
    download_model()
