# Modelos Pre-entrenados

Este directorio contiene los modelos de Machine Learning utilizados por el sistema.

## Modelos Incluidos

### YOLOv8 Nano (yolov8n.pt)
- **Uso**: Detección de objetos en tiempo real
- **Dataset**: COCO (80 clases)
- **Tamaño**: ~6 MB
- **Velocidad**: ~45 FPS en GPU, ~10 FPS en CPU
- **Precisión**: mAP 37.3%

### YOLOv8 Small (yolov8s.pt) - Opcional
- **Uso**: Detección con mayor precisión
- **Dataset**: COCO (80 clases)
- **Tamaño**: ~22 MB
- **Velocidad**: ~30 FPS en GPU, ~5 FPS en CPU
- **Precisión**: mAP 44.9%

## Descargar Modelos

Ejecuta el script de descarga:

```bash
python scripts/download_models.py
```

O descarga manualmente:
- YOLOv8n: https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
- YOLOv8s: https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt

## Entrenar Modelos Personalizados

Para entrenar un modelo con tus propios datos:

1. Prepara tu dataset en formato YOLO
2. Ejecuta:
```python
from ultralytics import YOLO

model = YOLO('yolov8n.pt')
model.train(data='tu_dataset.yaml', epochs=100)
```

3. Guarda el modelo entrenado en este directorio

## Estructura de Archivos

```
models/
├── README.md                    # Este archivo
├── yolov8n.pt                   # Modelo principal (descargado)
├── yolov8s.pt                   # Modelo alternativo (opcional)
├── custom_classifier.pkl        # Clasificador personalizado (generado)
└── gesture_model.h5             # Modelo de gestos (generado)
```

## Clases Detectables (COCO Dataset)

0: person, 1: bicycle, 2: car, 3: motorcycle, 4: airplane, 5: bus, 6: train, 7: truck, 
8: boat, 9: traffic light, 10: fire hydrant, 11: stop sign, 12: parking meter, 13: bench, 
14: bird, 15: cat, 16: dog, 17: horse, 18: sheep, 19: cow, 20: elephant, 21: bear, 
22: zebra, 23: giraffe, 24: backpack, 25: umbrella, 26: handbag, 27: tie, 28: suitcase, 
29: frisbee, 30: skis, 31: snowboard, 32: sports ball, 33: kite, 34: baseball bat, 
35: baseball glove, 36: skateboard, 37: surfboard, 38: tennis racket, 39: bottle, 
40: wine glass, 41: cup, 42: fork, 43: knife, 44: spoon, 45: bowl, 46: banana, 47: apple, 
48: sandwich, 49: orange, 50: broccoli, 51: carrot, 52: hot dog, 53: pizza, 54: donut, 
55: cake, 56: chair, 57: couch, 58: potted plant, 59: bed, 60: dining table, 61: toilet, 
62: tv, 63: laptop, 64: mouse, 65: remote, 66: keyboard, 67: cell phone, 68: microwave, 
69: oven, 70: toaster, 71: sink, 72: refrigerator, 73: book, 74: clock, 75: vase, 
76: scissors, 77: teddy bear, 78: hair drier, 79: toothbrush

## Notas

- Los modelos `.pt` son modelos PyTorch
- Los archivos `.pkl` son modelos de scikit-learn
- Los archivos `.h5` son modelos de Keras/TensorFlow
- No subir modelos grandes a Git (usar Git LFS si es necesario)
