"""
Hand Tracking Module - MediaPipe Integration
=============================================
Sistema de tracking de manos usando MediaPipe con reconocimiento de gestos básicos
"""

import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import time


class HandGesture(Enum):
    """Enumeración de gestos reconocibles"""
    UNKNOWN = "unknown"
    OPEN_PALM = "open_palm"
    CLOSED_FIST = "closed_fist"
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    PEACE_SIGN = "peace_sign"
    OK_SIGN = "ok_sign"
    POINTING = "pointing"
    PINCH = "pinch"


@dataclass
class HandLandmark:
    """Datos de un landmark de la mano"""
    x: float
    y: float
    z: float
    visibility: float = 1.0


@dataclass
class HandData:
    """Datos completos de una mano detectada"""
    landmarks: List[HandLandmark]
    handedness: str  # "Left" o "Right"
    gesture: HandGesture
    confidence: float
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    center: Tuple[float, float]


class HandTracker:
    """
    Clase principal para tracking de manos y reconocimiento de gestos
    """
    
    def __init__(
        self,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5,
        model_complexity: int = 1
    ):
        """
        Inicializar el tracker de manos
        
        Args:
            max_num_hands: Número máximo de manos a detectar
            min_detection_confidence: Confianza mínima para detección
            min_tracking_confidence: Confianza mínima para tracking
            model_complexity: Complejidad del modelo (0=lite, 1=full)
        """
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        self.hands = self.mp_hands.Hands(
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            model_complexity=model_complexity
        )
        
        # Historial para suavizado temporal
        self.gesture_history: List[HandGesture] = []
        self.history_size = 5
        
        # Métricas
        self.fps = 0
        self.last_time = time.time()
        self.frame_count = 0
    
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, List[HandData]]:
        """
        Procesar un frame y detectar manos
        
        Args:
            frame: Frame BGR de OpenCV
            
        Returns:
            Tuple de (frame anotado, lista de HandData)
        """
        # Convertir BGR a RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        
        # Procesar con MediaPipe
        results = self.mp_hands.process(rgb_frame)
        
        # Hacer frame escribible para anotaciones
        rgb_frame.flags.writeable = True
        annotated_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
        
        hands_data = []
        
        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_landmarks, handedness in zip(
                results.multi_hand_landmarks,
                results.multi_handedness
            ):
                # Extraer datos de la mano
                hand_data = self._extract_hand_data(
                    hand_landmarks,
                    handedness,
                    frame.shape
                )
                hands_data.append(hand_data)
                
                # Dibujar landmarks en el frame
                self._draw_hand_annotations(
                    annotated_frame,
                    hand_landmarks,
                    hand_data
                )
        
        # Calcular FPS
        self._update_fps()
        
        # Dibujar FPS en el frame
        cv2.putText(
            annotated_frame,
            f"FPS: {self.fps:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )
        
        return annotated_frame, hands_data
    
    def _extract_hand_data(
        self,
        hand_landmarks,
        handedness,
        frame_shape: Tuple[int, int, int]
    ) -> HandData:
        """Extraer datos estructurados de una mano"""
        h, w, _ = frame_shape
        
        # Convertir landmarks a lista de HandLandmark
        landmarks = []
        xs, ys = [], []
        
        for landmark in hand_landmarks.landmark:
            x = landmark.x * w
            y = landmark.y * h
            xs.append(x)
            ys.append(y)
            
            landmarks.append(HandLandmark(
                x=landmark.x,
                y=landmark.y,
                z=landmark.z,
                visibility=landmark.visibility if hasattr(landmark, 'visibility') else 1.0
            ))
        
        # Calcular bounding box
        x_min, x_max = int(min(xs)), int(max(xs))
        y_min, y_max = int(min(ys)), int(max(ys))
        bbox = (x_min, y_min, x_max - x_min, y_max - y_min)
        
        # Calcular centro
        center = (sum(xs) / len(xs), sum(ys) / len(ys))
        
        # Reconocer gesto
        gesture = self._recognize_gesture(landmarks)
        
        # Suavizado temporal del gesto
        gesture = self._smooth_gesture(gesture)
        
        return HandData(
            landmarks=landmarks,
            handedness=handedness.classification[0].label,
            gesture=gesture,
            confidence=handedness.classification[0].score,
            bbox=bbox,
            center=center
        )
    
    def _recognize_gesture(self, landmarks: List[HandLandmark]) -> HandGesture:
        """
        Reconocer gesto basado en landmarks
        
        Indices de landmarks (MediaPipe):
        0: Muñeca
        4: Pulgar punta
        8: Índice punta
        12: Medio punta
        16: Anular punta
        20: Meñique punta
        """
        # Verificar que tenemos suficientes landmarks
        if len(landmarks) < 21:
            return HandGesture.UNKNOWN
        
        # Obtener posiciones de dedos
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        ring_tip = landmarks[16]
        pinky_tip = landmarks[20]
        
        # Posiciones de articulaciones medias
        thumb_ip = landmarks[3]
        index_pip = landmarks[6]
        middle_pip = landmarks[10]
        ring_pip = landmarks[14]
        pinky_pip = landmarks[18]
        
        # Muñeca
        wrist = landmarks[0]
        
        # Detectar dedos extendidos
        fingers_extended = []
        
        # Pulgar (comparación en eje X)
        fingers_extended.append(
            abs(thumb_tip.x - thumb_ip.x) > 0.04
        )
        
        # Otros dedos (comparación en eje Y)
        for tip, pip in [
            (index_tip, index_pip),
            (middle_tip, middle_pip),
            (ring_tip, ring_pip),
            (pinky_tip, pinky_pip)
        ]:
            fingers_extended.append(tip.y < pip.y)
        
        extended_count = sum(fingers_extended)
        
        # Reconocer gestos
        
        # Mano abierta (todos los dedos extendidos)
        if extended_count >= 4:
            return HandGesture.OPEN_PALM
        
        # Puño cerrado (ningún dedo extendido)
        if extended_count == 0:
            return HandGesture.CLOSED_FIST
        
        # Thumbs up (solo pulgar extendido)
        if fingers_extended[0] and extended_count == 1:
            if thumb_tip.y < wrist.y:
                return HandGesture.THUMBS_UP
            else:
                return HandGesture.THUMBS_DOWN
        
        # Peace sign (índice y medio extendidos)
        if (fingers_extended[1] and fingers_extended[2] and 
            not fingers_extended[3] and not fingers_extended[4]):
            return HandGesture.PEACE_SIGN
        
        # Pointing (solo índice extendido)
        if fingers_extended[1] and extended_count == 1:
            return HandGesture.POINTING
        
        # OK sign (pulgar e índice haciendo círculo)
        thumb_index_dist = np.sqrt(
            (thumb_tip.x - index_tip.x)**2 + 
            (thumb_tip.y - index_tip.y)**2
        )
        if thumb_index_dist < 0.05 and extended_count >= 3:
            return HandGesture.OK_SIGN
        
        # Pinch (pulgar e índice cercanos)
        if thumb_index_dist < 0.03:
            return HandGesture.PINCH
        
        return HandGesture.UNKNOWN
    
    def _smooth_gesture(self, gesture: HandGesture) -> HandGesture:
        """Suavizar reconocimiento de gestos usando historial"""
        self.gesture_history.append(gesture)
        
        # Mantener solo los últimos N gestos
        if len(self.gesture_history) > self.history_size:
            self.gesture_history.pop(0)
        
        # Si hay suficiente historia, usar votación mayoritaria
        if len(self.gesture_history) >= 3:
            from collections import Counter
            most_common = Counter(self.gesture_history).most_common(1)[0][0]
            return most_common
        
        return gesture
    
    def _draw_hand_annotations(
        self,
        frame: np.ndarray,
        hand_landmarks,
        hand_data: HandData
    ):
        """Dibujar anotaciones en el frame"""
        # Dibujar landmarks y conexiones
        self.mp_drawing.draw_landmarks(
            frame,
            hand_landmarks,
            self.mp_hands.HAND_CONNECTIONS,
            self.mp_drawing_styles.get_default_hand_landmarks_style(),
            self.mp_drawing_styles.get_default_hand_connections_style()
        )
        
        # Dibujar bounding box
        x, y, w, h = hand_data.bbox
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # Dibujar información de la mano
        text = f"{hand_data.handedness} - {hand_data.gesture.value}"
        cv2.putText(
            frame,
            text,
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )
        
        # Dibujar centro
        cx, cy = int(hand_data.center[0]), int(hand_data.center[1])
        cv2.circle(frame, (cx, cy), 5, (255, 0, 255), -1)
    
    def _update_fps(self):
        """Actualizar cálculo de FPS"""
        self.frame_count += 1
        current_time = time.time()
        
        if current_time - self.last_time >= 1.0:
            self.fps = self.frame_count / (current_time - self.last_time)
            self.frame_count = 0
            self.last_time = current_time
    
    def get_gesture_name(self, gesture: HandGesture) -> str:
        """Obtener nombre legible del gesto"""
        gesture_names = {
            HandGesture.UNKNOWN: "Desconocido",
            HandGesture.OPEN_PALM: "Mano Abierta",
            HandGesture.CLOSED_FIST: "Puño Cerrado",
            HandGesture.THUMBS_UP: "Pulgar Arriba",
            HandGesture.THUMBS_DOWN: "Pulgar Abajo",
            HandGesture.PEACE_SIGN: "Señal de Paz",
            HandGesture.OK_SIGN: "Señal OK",
            HandGesture.POINTING: "Señalando",
            HandGesture.PINCH: "Pellizco"
        }
        return gesture_names.get(gesture, "Desconocido")
    
    def release(self):
        """Liberar recursos"""
        self.hands.close()


if __name__ == "__main__":
    # Demo standalone
    print("Iniciando Hand Tracker...")
    print("Presiona 'q' para salir")
    
    tracker = HandTracker(max_num_hands=2)
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: No se pudo abrir la cámara")
        exit()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: No se pudo leer el frame")
                break
            
            # Procesar frame
            annotated_frame, hands_data = tracker.process_frame(frame)
            
            # Mostrar información de gestos detectados
            for i, hand in enumerate(hands_data):
                gesture_name = tracker.get_gesture_name(hand.gesture)
                print(f"Mano {i+1} ({hand.handedness}): {gesture_name}")
            
            # Mostrar frame
            cv2.imshow('Hand Tracking - MediaPipe', annotated_frame)
            
            # Salir con 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        tracker.release()
        cap.release()
        cv2.destroyAllWindows()
        print("Hand Tracker cerrado")
