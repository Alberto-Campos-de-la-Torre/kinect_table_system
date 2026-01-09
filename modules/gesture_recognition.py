"""
Módulo de Reconocimiento de Gestos con MediaPipe
=================================================
Detecta y reconoce gestos básicos de la mano en tiempo real

Gestos Soportados:
- Mano Abierta (Open Palm)
- Puño Cerrado (Closed Fist)
- Pulgar Arriba (Thumbs Up)
- Pulgar Abajo (Thumbs Down)
- Pellizco (Pinch)
- Victoria/Paz (Peace/Victory)
- OK Sign
- Puntero (Pointing)
"""

import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class GestureType(Enum):
    """Tipos de gestos reconocidos"""
    UNKNOWN = "unknown"
    OPEN_PALM = "open_palm"
    CLOSED_FIST = "closed_fist"
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    PINCH = "pinch"
    VICTORY = "victory"
    OK_SIGN = "ok_sign"
    POINTING = "pointing"


@dataclass
class HandLandmarks:
    """Información de landmarks de la mano"""
    wrist: Tuple[float, float]
    thumb_tip: Tuple[float, float]
    index_tip: Tuple[float, float]
    middle_tip: Tuple[float, float]
    ring_tip: Tuple[float, float]
    pinky_tip: Tuple[float, float]
    thumb_ip: Tuple[float, float]
    index_pip: Tuple[float, float]
    middle_pip: Tuple[float, float]
    ring_pip: Tuple[float, float]
    pinky_pip: Tuple[float, float]


@dataclass
class GestureResult:
    """Resultado del reconocimiento de gesto"""
    gesture: GestureType
    confidence: float
    hand_landmarks: HandLandmarks
    bounding_box: Tuple[int, int, int, int]  # x, y, w, h
    handedness: str  # "Left" or "Right"


class GestureRecognizer:
    """Reconocedor de gestos usando MediaPipe Hands"""
    
    def __init__(
        self,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5
    ):
        """
        Inicializar reconocedor de gestos
        
        Args:
            max_num_hands: Número máximo de manos a detectar
            min_detection_confidence: Confianza mínima para detección
            min_tracking_confidence: Confianza mínima para tracking
        """
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
        # Colores para visualización
        self.colors = {
            GestureType.OPEN_PALM: (0, 255, 0),
            GestureType.CLOSED_FIST: (0, 0, 255),
            GestureType.THUMBS_UP: (255, 255, 0),
            GestureType.THUMBS_DOWN: (255, 0, 255),
            GestureType.PINCH: (255, 165, 0),
            GestureType.VICTORY: (128, 0, 128),
            GestureType.OK_SIGN: (0, 255, 255),
            GestureType.POINTING: (255, 192, 203),
            GestureType.UNKNOWN: (128, 128, 128)
        }
    
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, List[GestureResult]]:
        """
        Procesar un frame y detectar gestos
        
        Args:
            frame: Frame de video en formato BGR
        
        Returns:
            Tupla de (frame_anotado, lista_de_gestos)
        """
        # Convertir BGR a RGB
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False
        
        # Procesar con MediaPipe
        results = self.hands.process(image_rgb)
        
        # Convertir de vuelta a BGR para visualización
        image_rgb.flags.writeable = True
        annotated_frame = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        
        gesture_results = []
        
        if results.multi_hand_landmarks:
            for idx, (hand_landmarks, handedness) in enumerate(
                zip(results.multi_hand_landmarks, results.multi_handedness)
            ):
                # Extraer información de landmarks
                landmarks = self._extract_landmarks(hand_landmarks, frame.shape)
                
                # Reconocer gesto
                gesture, confidence = self._recognize_gesture(landmarks)
                
                # Calcular bounding box
                bbox = self._calculate_bounding_box(hand_landmarks, frame.shape)
                
                # Crear resultado
                gesture_result = GestureResult(
                    gesture=gesture,
                    confidence=confidence,
                    hand_landmarks=landmarks,
                    bounding_box=bbox,
                    handedness=handedness.classification[0].label
                )
                gesture_results.append(gesture_result)
                
                # Dibujar landmarks
                self.mp_drawing.draw_landmarks(
                    annotated_frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    self.mp_drawing_styles.get_default_hand_connections_style()
                )
                
                # Dibujar información del gesto
                self._draw_gesture_info(annotated_frame, gesture_result)
        
        return annotated_frame, gesture_results
    
    def _extract_landmarks(self, hand_landmarks, shape) -> HandLandmarks:
        """Extraer coordenadas de landmarks importantes"""
        h, w = shape[:2]
        
        def get_coords(idx):
            lm = hand_landmarks.landmark[idx]
            return (lm.x * w, lm.y * h)
        
        return HandLandmarks(
            wrist=get_coords(0),
            thumb_tip=get_coords(4),
            index_tip=get_coords(8),
            middle_tip=get_coords(12),
            ring_tip=get_coords(16),
            pinky_tip=get_coords(20),
            thumb_ip=get_coords(3),
            index_pip=get_coords(6),
            middle_pip=get_coords(10),
            ring_pip=get_coords(14),
            pinky_pip=get_coords(18)
        )
    
    def _recognize_gesture(self, landmarks: HandLandmarks) -> Tuple[GestureType, float]:
        """
        Reconocer gesto basado en landmarks
        
        Returns:
            Tupla de (tipo_gesto, confianza)
        """
        # Calcular estados de dedos (extendidos o no)
        fingers_up = self._count_fingers_up(landmarks)
        
        # Reconocer gestos basados en patrones
        
        # Mano abierta: todos los dedos arriba
        if sum(fingers_up) == 5:
            return GestureType.OPEN_PALM, 0.95
        
        # Puño cerrado: ningún dedo arriba
        if sum(fingers_up) == 0:
            return GestureType.CLOSED_FIST, 0.95
        
        # Pulgar arriba: solo pulgar arriba
        if fingers_up == [1, 0, 0, 0, 0]:
            return GestureType.THUMBS_UP, 0.90
        
        # Pulgar abajo (aproximación basada en posición)
        if fingers_up == [0, 0, 0, 0, 0]:
            # Verificar si pulgar está por debajo de la muñeca
            if landmarks.thumb_tip[1] > landmarks.wrist[1]:
                return GestureType.THUMBS_DOWN, 0.85
        
        # Victoria: índice y medio arriba
        if fingers_up == [0, 1, 1, 0, 0]:
            return GestureType.VICTORY, 0.90
        
        # Puntero: solo índice arriba
        if fingers_up == [0, 1, 0, 0, 0]:
            return GestureType.POINTING, 0.90
        
        # OK Sign: pulgar e índice formando círculo
        if self._is_pinch(landmarks):
            if fingers_up[2:] == [1, 1, 1]:  # otros dedos arriba
                return GestureType.OK_SIGN, 0.85
            else:
                return GestureType.PINCH, 0.85
        
        return GestureType.UNKNOWN, 0.5
    
    def _count_fingers_up(self, landmarks: HandLandmarks) -> List[int]:
        """
        Contar qué dedos están levantados
        
        Returns:
            Lista de 5 elementos [pulgar, índice, medio, anular, meñique]
            1 = levantado, 0 = doblado
        """
        fingers = []
        
        # Pulgar (comparar con IP en x)
        if landmarks.thumb_tip[0] < landmarks.thumb_ip[0]:
            fingers.append(1)
        else:
            fingers.append(0)
        
        # Otros dedos (comparar TIP con PIP en y)
        tips = [
            landmarks.index_tip,
            landmarks.middle_tip,
            landmarks.ring_tip,
            landmarks.pinky_tip
        ]
        pips = [
            landmarks.index_pip,
            landmarks.middle_pip,
            landmarks.ring_pip,
            landmarks.pinky_pip
        ]
        
        for tip, pip in zip(tips, pips):
            if tip[1] < pip[1]:  # tip más arriba que pip
                fingers.append(1)
            else:
                fingers.append(0)
        
        return fingers
    
    def _is_pinch(self, landmarks: HandLandmarks, threshold: float = 40.0) -> bool:
        """Detectar si pulgar e índice están haciendo pinch"""
        thumb_tip = np.array(landmarks.thumb_tip)
        index_tip = np.array(landmarks.index_tip)
        distance = np.linalg.norm(thumb_tip - index_tip)
        return distance < threshold
    
    def _calculate_bounding_box(self, hand_landmarks, shape) -> Tuple[int, int, int, int]:
        """Calcular bounding box de la mano"""
        h, w = shape[:2]
        
        x_coords = [lm.x * w for lm in hand_landmarks.landmark]
        y_coords = [lm.y * h for lm in hand_landmarks.landmark]
        
        x_min, x_max = int(min(x_coords)), int(max(x_coords))
        y_min, y_max = int(min(y_coords)), int(max(y_coords))
        
        # Agregar margen
        margin = 20
        x_min = max(0, x_min - margin)
        y_min = max(0, y_min - margin)
        x_max = min(w, x_max + margin)
        y_max = min(h, y_max + margin)
        
        return (x_min, y_min, x_max - x_min, y_max - y_min)
    
    def _draw_gesture_info(self, frame: np.ndarray, gesture_result: GestureResult):
        """Dibujar información del gesto en el frame"""
        x, y, w, h = gesture_result.bounding_box
        
        # Dibujar bounding box
        color = self.colors[gesture_result.gesture]
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        
        # Preparar texto
        gesture_name = gesture_result.gesture.value.replace('_', ' ').title()
        confidence = gesture_result.confidence * 100
        text = f"{gesture_result.handedness}: {gesture_name} ({confidence:.0f}%)"
        
        # Calcular tamaño del texto
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
        
        # Dibujar fondo del texto
        cv2.rectangle(
            frame,
            (x, y - text_height - 10),
            (x + text_width + 10, y),
            color,
            -1
        )
        
        # Dibujar texto
        cv2.putText(
            frame,
            text,
            (x + 5, y - 5),
            font,
            font_scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA
        )
    
    def close(self):
        """Liberar recursos"""
        self.hands.close()


def main():
    """Función principal para demo standalone"""
    print("=" * 60)
    print("RECONOCIMIENTO DE GESTOS CON MEDIAPIPE")
    print("=" * 60)
    print("\nGestos soportados:")
    print("  - Mano Abierta (todos los dedos arriba)")
    print("  - Puño Cerrado (ningún dedo arriba)")
    print("  - Pulgar Arriba (solo pulgar)")
    print("  - Victoria (índice y medio)")
    print("  - Puntero (solo índice)")
    print("  - OK Sign (pulgar e índice + otros arriba)")
    print("  - Pellizco (pulgar e índice juntos)")
    print("\nPresiona 'q' para salir")
    print("=" * 60)
    print()
    
    # Inicializar reconocedor
    recognizer = GestureRecognizer(
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5
    )
    
    # Abrir cámara
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: No se pudo abrir la cámara")
        return
    
    # Configurar resolución
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # Variables para FPS
    import time
    prev_time = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: No se pudo leer el frame")
                break
            
            # Voltear horizontalmente para efecto espejo
            frame = cv2.flip(frame, 1)
            
            # Procesar frame
            annotated_frame, gestures = recognizer.process_frame(frame)
            
            # Calcular FPS
            curr_time = time.time()
            fps = 1 / (curr_time - prev_time)
            prev_time = curr_time
            
            # Mostrar FPS
            cv2.putText(
                annotated_frame,
                f"FPS: {fps:.1f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
                cv2.LINE_AA
            )
            
            # Mostrar información de gestos detectados
            if gestures:
                y_offset = 70
                for gesture in gestures:
                    info = f"{gesture.handedness} - {gesture.gesture.value}"
                    cv2.putText(
                        annotated_frame,
                        info,
                        (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 255, 255),
                        2,
                        cv2.LINE_AA
                    )
                    y_offset += 40
            
            # Mostrar frame
            cv2.imshow('Reconocimiento de Gestos - MediaPipe', annotated_frame)
            
            # Salir con 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        # Limpiar
        cap.release()
        cv2.destroyAllWindows()
        recognizer.close()
        print("\nSistema cerrado correctamente")


if __name__ == "__main__":
    main()
