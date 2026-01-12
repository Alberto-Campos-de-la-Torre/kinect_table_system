"""
Hand Tracking Module - MediaPipe Integration
=============================================
Sistema de tracking de manos usando MediaPipe con reconocimiento de gestos básicos
"""

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import time
from pathlib import Path


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
    # Nuevos gestos
    ROCK = "rock"              # Cuernos del rock 🤘
    CALL_ME = "call_me"        # Teléfono 🤙
    THREE = "three"            # Número 3
    FOUR = "four"              # Número 4
    SPIDERMAN = "spiderman"    # Gesto de Spiderman 🕷️
    LOVE = "love"              # Te quiero (lengua de señas) 🤟
    GUN = "gun"                # Pistola 👉
    MIDDLE_FINGER = "middle_finger"  # Dedo medio (censurado)
    GRAB = "grab"              # Agarrar


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
        model_complexity: int = 1,
        model_path: Optional[str] = None
    ):
        """
        Inicializar el tracker de manos
        
        Args:
            max_num_hands: Número máximo de manos a detectar
            min_detection_confidence: Confianza mínima para detección
            min_tracking_confidence: Confianza mínima para tracking
            model_complexity: Complejidad del modelo (0=lite, 1=full) - No usado en nueva API
            model_path: Ruta al archivo del modelo hand_landmarker.task
        """
        # Buscar el modelo en el directorio raíz del proyecto
        if model_path is None:
            project_root = Path(__file__).parent.parent
            model_path = project_root / "hand_landmarker.task"
            if not model_path.exists():
                # Intentar en el directorio actual
                model_path = Path("hand_landmarker.task")
        
        if not Path(model_path).exists():
            raise FileNotFoundError(
                f"No se encontró el modelo hand_landmarker.task en {model_path}.\n"
                "Por favor descárgalo desde: https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
            )
        
        # Configurar opciones del HandLandmarker
        base_options = python.BaseOptions(model_asset_path=str(model_path))
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=max_num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
        # Crear el HandLandmarker
        self.landmarker = vision.HandLandmarker.create_from_options(options)
        
        # Para dibujar landmarks (usando OpenCV ya que la nueva API no tiene drawing_utils)
        self.use_opencv_drawing = True
        
        # Historial para suavizado temporal
        self.gesture_history: List[HandGesture] = []
        self.history_size = 5
        
        # Métricas
        self.fps = 0
        self.last_time = time.time()
        self.frame_count = 0
        self.timestamp_ms = 0
    
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
        
        # Crear imagen de MediaPipe
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Procesar con MediaPipe (usando timestamp en milisegundos)
        self.timestamp_ms = int(time.time() * 1000)
        results = self.landmarker.detect_for_video(mp_image, self.timestamp_ms)
        
        # Copiar frame para anotaciones
        annotated_frame = frame.copy()
        
        hands_data = []
        
        if results.hand_landmarks:
            for idx, hand_landmarks in enumerate(results.hand_landmarks):
                # Obtener handedness (Left o Right)
                handedness = "Left"
                confidence = 0.5
                if results.handedness and idx < len(results.handedness):
                    handedness_info = results.handedness[idx]
                    if handedness_info and len(handedness_info) > 0:
                        handedness = handedness_info[0].category_name
                        confidence = handedness_info[0].score
                
                # Extraer datos de la mano
                hand_data = self._extract_hand_data(
                    hand_landmarks,
                    handedness,
                    frame.shape,
                    confidence
                )
                hands_data.append(hand_data)
                
                # Dibujar landmarks en el frame
                self._draw_hand_annotations(
                    annotated_frame,
                    hand_landmarks,
                    hand_data
                )
        
        # Calcular FPS (interno, no dibujar)
        self._update_fps()
        
        return annotated_frame, hands_data
    
    def _extract_hand_data(
        self,
        hand_landmarks,
        handedness: str,
        frame_shape: Tuple[int, int, int],
        confidence: float = 0.5
    ) -> HandData:
        """Extraer datos estructurados de una mano"""
        h, w, _ = frame_shape
        
        # Convertir landmarks a lista de HandLandmark
        landmarks = []
        xs, ys = [], []
        
        for landmark in hand_landmarks:
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
            handedness=handedness,
            gesture=gesture,
            confidence=confidence,
            bbox=bbox,
            center=center
        )
    
    def _recognize_gesture(self, landmarks: List[HandLandmark]) -> HandGesture:
        """
        Reconocer gesto basado en landmarks
        
        Indices de landmarks (MediaPipe):
        0: Muñeca
        1-4: Pulgar (CMC, MCP, IP, TIP)
        5-8: Índice (MCP, PIP, DIP, TIP)
        9-12: Medio (MCP, PIP, DIP, TIP)
        13-16: Anular (MCP, PIP, DIP, TIP)
        17-20: Meñique (MCP, PIP, DIP, TIP)
        """
        if len(landmarks) < 21:
            return HandGesture.UNKNOWN
        
        # Obtener posiciones de dedos (puntas)
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        ring_tip = landmarks[16]
        pinky_tip = landmarks[20]
        
        # Articulaciones medias (PIP)
        thumb_ip = landmarks[3]
        index_pip = landmarks[6]
        middle_pip = landmarks[10]
        ring_pip = landmarks[14]
        pinky_pip = landmarks[18]
        
        # Articulaciones base (MCP)
        thumb_mcp = landmarks[2]
        index_mcp = landmarks[5]
        middle_mcp = landmarks[9]
        ring_mcp = landmarks[13]
        pinky_mcp = landmarks[17]
        
        # Muñeca
        wrist = landmarks[0]
        
        # Detectar dedos extendidos
        # Pulgar: comparar distancia horizontal
        thumb_extended = abs(thumb_tip.x - thumb_mcp.x) > 0.05
        
        # Otros dedos: punta por encima del PIP (en coordenadas de imagen, Y menor = arriba)
        index_extended = index_tip.y < index_pip.y
        middle_extended = middle_tip.y < middle_pip.y
        ring_extended = ring_tip.y < ring_pip.y
        pinky_extended = pinky_tip.y < pinky_pip.y
        
        fingers = [thumb_extended, index_extended, middle_extended, ring_extended, pinky_extended]
        extended_count = sum(fingers)
        
        # Distancias útiles
        thumb_index_dist = np.sqrt((thumb_tip.x - index_tip.x)**2 + (thumb_tip.y - index_tip.y)**2)
        thumb_middle_dist = np.sqrt((thumb_tip.x - middle_tip.x)**2 + (thumb_tip.y - middle_tip.y)**2)
        thumb_pinky_dist = np.sqrt((thumb_tip.x - pinky_tip.x)**2 + (thumb_tip.y - pinky_tip.y)**2)
        
        # ========== RECONOCIMIENTO DE GESTOS ==========
        
        # PINCH - Pellizco (pulgar e índice muy cercanos)
        if thumb_index_dist < 0.04 and not middle_extended and not ring_extended:
            return HandGesture.PINCH
        
        # GRAB - Agarrar (todos los dedos semi-cerrados, como agarrando algo)
        if thumb_index_dist < 0.06 and thumb_middle_dist < 0.08 and extended_count <= 2:
            return HandGesture.GRAB
        
        # OK SIGN - Pulgar e índice en círculo, otros extendidos
        if thumb_index_dist < 0.05 and middle_extended and ring_extended and pinky_extended:
            return HandGesture.OK_SIGN
        
        # CLOSED FIST - Puño cerrado
        if extended_count == 0:
            return HandGesture.CLOSED_FIST
        
        # OPEN PALM - Mano abierta (5 dedos)
        if extended_count >= 5:
            return HandGesture.OPEN_PALM
        
        # FOUR - Cuatro dedos (sin pulgar)
        if not thumb_extended and index_extended and middle_extended and ring_extended and pinky_extended:
            return HandGesture.FOUR
        
        # THREE - Tres dedos (índice, medio, anular)
        if index_extended and middle_extended and ring_extended and not pinky_extended and not thumb_extended:
            return HandGesture.THREE
        
        # PEACE SIGN - Señal de paz (índice y medio)
        if index_extended and middle_extended and not ring_extended and not pinky_extended:
            if not thumb_extended:
                return HandGesture.PEACE_SIGN
        
        # ROCK - Cuernos del rock (índice y meñique)
        if index_extended and pinky_extended and not middle_extended and not ring_extended:
            return HandGesture.ROCK
        
        # LOVE - Te quiero en lengua de señas (pulgar, índice y meñique)
        if thumb_extended and index_extended and pinky_extended and not middle_extended and not ring_extended:
            return HandGesture.LOVE
        
        # SPIDERMAN - Gesto Spiderman (pulgar, índice y meñique, pero pulgar sobre palma)
        if index_extended and pinky_extended and not middle_extended and not ring_extended:
            if thumb_middle_dist < 0.06:  # Pulgar tocando palma
                return HandGesture.SPIDERMAN
        
        # CALL ME - Teléfono (pulgar y meñique)
        if thumb_extended and pinky_extended and not index_extended and not middle_extended and not ring_extended:
            return HandGesture.CALL_ME
        
        # THUMBS UP/DOWN - Solo pulgar
        if thumb_extended and extended_count == 1:
            if thumb_tip.y < wrist.y:
                return HandGesture.THUMBS_UP
            else:
                return HandGesture.THUMBS_DOWN
        
        # POINTING - Solo índice
        if index_extended and extended_count == 1:
            return HandGesture.POINTING
        
        # GUN - Pistola (pulgar e índice extendidos, como una L)
        if thumb_extended and index_extended and not middle_extended and not ring_extended and not pinky_extended:
            return HandGesture.GUN
        
        # MIDDLE FINGER - Solo dedo medio
        if middle_extended and not index_extended and not ring_extended and not pinky_extended and not thumb_extended:
            return HandGesture.MIDDLE_FINGER
        
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
        """Dibujar anotaciones en el frame usando OpenCV"""
        # Conexiones de la mano (MediaPipe Hand Landmarks)
        HAND_CONNECTIONS = [
            (0, 1), (1, 2), (2, 3), (3, 4),  # Pulgar
            (0, 5), (5, 6), (6, 7), (7, 8),  # Índice
            (0, 9), (9, 10), (10, 11), (11, 12),  # Medio
            (0, 13), (13, 14), (14, 15), (15, 16),  # Anular
            (0, 17), (17, 18), (18, 19), (19, 20),  # Meñique
            (5, 9), (9, 13), (13, 17), (17, 5)  # Base de los dedos
        ]
        
        h, w, _ = frame.shape
        
        # Dibujar conexiones
        for connection in HAND_CONNECTIONS:
            start_idx, end_idx = connection
            if start_idx < len(hand_landmarks) and end_idx < len(hand_landmarks):
                start = hand_landmarks[start_idx]
                end = hand_landmarks[end_idx]
                pt1 = (int(start.x * w), int(start.y * h))
                pt2 = (int(end.x * w), int(end.y * h))
                cv2.line(frame, pt1, pt2, (0, 255, 0), 2)
        
        # Dibujar landmarks
        for landmark in hand_landmarks:
            x, y = int(landmark.x * w), int(landmark.y * h)
            cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)
        
        # Dibujar bounding box
        x, y, w_box, h_box = hand_data.bbox
        cv2.rectangle(frame, (x, y), (x + w_box, y + h_box), (0, 255, 0), 2)
        
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
            HandGesture.OPEN_PALM: "Mano Abierta 🖐️",
            HandGesture.CLOSED_FIST: "Puño Cerrado ✊",
            HandGesture.THUMBS_UP: "Pulgar Arriba 👍",
            HandGesture.THUMBS_DOWN: "Pulgar Abajo 👎",
            HandGesture.PEACE_SIGN: "Paz ✌️",
            HandGesture.OK_SIGN: "OK 👌",
            HandGesture.POINTING: "Señalando 👉",
            HandGesture.PINCH: "Pellizco 🤏",
            HandGesture.ROCK: "Rock 🤘",
            HandGesture.CALL_ME: "Llámame 🤙",
            HandGesture.THREE: "Tres 3️⃣",
            HandGesture.FOUR: "Cuatro 4️⃣",
            HandGesture.SPIDERMAN: "Spiderman 🕷️",
            HandGesture.LOVE: "Te Quiero 🤟",
            HandGesture.GUN: "Pistola 🔫",
            HandGesture.MIDDLE_FINGER: "🖕",
            HandGesture.GRAB: "Agarrar 🫳"
        }
        return gesture_names.get(gesture, "Desconocido")
    
    def release(self):
        """Liberar recursos"""
        if hasattr(self, 'landmarker'):
            self.landmarker.close()


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
