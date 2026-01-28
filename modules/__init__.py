"""
Kinect Table System - Módulos
=============================
Colección de módulos para el sistema de mesa interactiva con Kinect.
"""

# Captura Kinect
from .kinect_capture import KinectCapture, depth_to_color

# Detección de objetos
from .object_detection import ObjectDetector, Detection, get_mesa_class_ids

# Tracking de manos
from .hand_tracking import HandTracker, HandGesture, HandData

# Reconocimiento de gestos (alternativo)
from .gesture_recognition import GestureRecognizer, GestureType, GestureResult

# Sistema de acciones basado en gestos
from .gesture_actions import (
    GestureActionMapper,
    GestureActionMapping,
    ActionType,
    ActionState,
    ActionEvent,
    create_default_mapper,
    create_minimal_mapper,
    create_stable_mapper
)

# Motor de interacción
from .interaction_engine import (
    InteractionEngine,
    InteractionState,
    InteractiveObject,
    HandState,
    InteractionEvent
)

# Submódulos
from . import calibration
from . import point_cloud

__all__ = [
    # Kinect
    'KinectCapture',
    'depth_to_color',
    
    # Object Detection
    'ObjectDetector',
    'Detection',
    'get_mesa_class_ids',
    
    # Hand Tracking
    'HandTracker',
    'HandGesture',
    'HandData',
    
    # Gesture Recognition
    'GestureRecognizer',
    'GestureType',
    'GestureResult',
    
    # Gesture Actions
    'GestureActionMapper',
    'GestureActionMapping',
    'ActionType',
    'ActionState',
    'ActionEvent',
    'create_default_mapper',
    'create_minimal_mapper',
    
    # Interaction Engine
    'InteractionEngine',
    'InteractionState',
    'InteractiveObject',
    'HandState',
    'InteractionEvent',
    
    # Submódulos
    'calibration',
    'point_cloud',
]
