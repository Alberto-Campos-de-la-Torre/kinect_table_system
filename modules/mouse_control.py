"""
Mouse Control Module - Control del mouse con gestos
====================================================
Controla el cursor siguiendo la punta del dedo índice.
Detecta clics usando el gesto de PINCH (pulgar + índice juntos).

- El cursor sigue la punta del dedo índice
- Gesto PINCH = clic izquierdo
- Mantener PINCH = arrastrar
"""

import logging
import time
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import threading
import numpy as np

logger = logging.getLogger(__name__)

# Importar pyautogui
try:
    import pyautogui
    pyautogui.FAILSAFE = False  # Desactivar failsafe para múltiples monitores
    pyautogui.PAUSE = 0.001
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    logger.warning("pyautogui no disponible")


class MouseAction(Enum):
    """Acciones del mouse"""
    NONE = "none"
    MOVE = "move"
    HOVER = "hover"
    TOUCH_DOWN = "touch_down"
    TOUCH_UP = "touch_up"
    LEFT_CLICK = "left_click"
    RIGHT_CLICK = "right_click"
    DOUBLE_CLICK = "double_click"
    DRAG_START = "drag_start"
    DRAG_MOVE = "drag_move"
    DRAG_END = "drag_end"


class TouchState(Enum):
    """Estado del toque"""
    HOVERING = "hovering"
    TOUCHING = "touching"
    DRAGGING = "dragging"


@dataclass
class TouchConfig:
    """Configuración del control táctil"""

    # === ÁREA DE PANTALLA ===
    # Monitor 3 (DP-5): posición (5280, 0), resolución 1920x1080
    screen_offset_x: int = 5280   # Offset X del monitor 3
    screen_offset_y: int = 0      # Offset Y del área activa
    screen_width: int = 1920      # Ancho del área activa
    screen_height: int = 1080     # Alto del área activa

    # === FLIP/ESPEJO ===
    # Debe coincidir con la calibración del video
    flip_x: bool = False  # Si True, invierte eje X (espejo horizontal)
    flip_y: bool = False  # Si True, invierte eje Y (espejo vertical)

    # === TIEMPOS ===
    min_touch_time: float = 0.04      # Tiempo mínimo de toque
    drag_threshold_time: float = 0.25  # Tiempo para iniciar arrastre
    click_cooldown: float = 0.2        # Cooldown entre clics
    double_click_window: float = 0.35  # Ventana para doble clic

    # === SUAVIZADO ===
    smoothing: float = 0.5             # Suavizado de posición (0-0.9)
    depth_smoothing: float = 0.4       # Suavizado de profundidad

    # === ENTRADA ===
    input_width: int = 640
    input_height: int = 480
    margin: int = 40                   # Margen de la zona activa del frame

    # === MANO ===
    active_hand: str = "Right"


class TouchMouseController:
    """
    Controlador de mouse con gestos.

    - El cursor sigue la punta del dedo índice
    - Gesto PINCH (pulgar + índice) = clic izquierdo
    - Mantener PINCH = arrastrar
    """

    INDEX_FINGER_TIP = 8
    WRIST = 0

    def __init__(self, config: Optional[TouchConfig] = None):
        self.config = config or TouchConfig()
        self.enabled = False
        self._lock = threading.Lock()

        # Estado
        self._touch_state = TouchState.HOVERING
        self._touch_start_time: float = 0
        self._last_click_time: float = 0
        self._last_touch_up_time: float = 0

        # Estado del pinch
        self._was_pinching: bool = False
        self._pinch_start_time: float = 0

        # Posición
        self._smoothed_x: float = 0
        self._smoothed_y: float = 0
        self._smoothed_depth: float = 0
        self._position_history: List[Tuple[float, float]] = []
        self._history_size: int = 4

        # Calibración (ya no necesaria pero mantenida para compatibilidad)
        self._depth_baseline: float = 0
        self._is_calibrated: bool = True  # Ya no necesita calibración
        self._calibration_samples: List[float] = []

        # Detectar pantalla principal si pyautogui disponible
        if PYAUTOGUI_AVAILABLE:
            try:
                # Obtener tamaño total (todos los monitores)
                total_w, total_h = pyautogui.size()
                logger.info(f"Área total de monitores: {total_w}x{total_h}")

                # Configurado para Monitor 3 (DP-5) en posición (5280, 0)
                if total_w > 1920:
                    logger.info(f"Múltiples monitores detectados. Usando Monitor 3 (offset: {self.config.screen_offset_x})")
            except Exception as e:
                logger.warning(f"Error detectando pantalla: {e}")

        logger.info("TouchMouseController inicializado")
        logger.info(f"Área activa: ({self.config.screen_offset_x}, {self.config.screen_offset_y}) "
                   f"{self.config.screen_width}x{self.config.screen_height}")

    def set_screen_area(self, x: int, y: int, width: int, height: int):
        """
        Configurar área de pantalla activa.

        Args:
            x: Offset X (0 para primer monitor)
            y: Offset Y (0 para primer monitor)
            width: Ancho del área
            height: Alto del área
        """
        self.config.screen_offset_x = x
        self.config.screen_offset_y = y
        self.config.screen_width = width
        self.config.screen_height = height
        logger.info(f"Área de pantalla: ({x}, {y}) {width}x{height}")

    def enable(self) -> bool:
        """Habilitar control"""
        if not PYAUTOGUI_AVAILABLE:
            return False

        with self._lock:
            self.enabled = True
            self._reset_state()
            self._is_calibrated = True  # No requiere calibración con pinch
            self._was_pinching = False

        logger.info("Control con gestos HABILITADO - Usa PINCH para clic")
        return True

    def disable(self):
        """Deshabilitar control"""
        with self._lock:
            if self._touch_state == TouchState.DRAGGING:
                self._end_drag()
            self.enabled = False
            self._reset_state()
        logger.info("Control táctil DESHABILITADO")

    def toggle(self) -> bool:
        if self.enabled:
            self.disable()
            return False
        return self.enable()

    def _reset_state(self):
        self._touch_state = TouchState.HOVERING
        self._touch_start_time = 0
        self._position_history.clear()
        self._was_pinching = False
        self._pinch_start_time = 0

    def _smooth_position(self, x: float, y: float) -> Tuple[float, float]:
        """Suavizar posición"""
        self._position_history.append((x, y))
        if len(self._position_history) > self._history_size:
            self._position_history.pop(0)

        if len(self._position_history) < 2:
            self._smoothed_x = x
            self._smoothed_y = y
            return x, y

        # Promedio ponderado
        total_w = 0
        wx, wy = 0.0, 0.0
        for i, (px, py) in enumerate(self._position_history):
            w = (i + 1) ** 2
            wx += px * w
            wy += py * w
            total_w += w

        avg_x = wx / total_w
        avg_y = wy / total_w

        s = self.config.smoothing
        self._smoothed_x = self._smoothed_x * s + avg_x * (1 - s)
        self._smoothed_y = self._smoothed_y * s + avg_y * (1 - s)

        return self._smoothed_x, self._smoothed_y

    def _smooth_depth(self, depth: float) -> float:
        """Suavizar profundidad"""
        if depth <= 0:
            return self._smoothed_depth

        s = self.config.depth_smoothing
        self._smoothed_depth = self._smoothed_depth * s + depth * (1 - s)
        return self._smoothed_depth

    def _map_to_screen(self, finger_x: float, finger_y: float) -> Tuple[int, int]:
        """Mapear posición del dedo a coordenadas de pantalla (limitado al área activa)"""
        margin = self.config.margin

        # Normalizar a 0-1
        norm_x = (finger_x - margin) / (self.config.input_width - 2 * margin)
        norm_y = (finger_y - margin) / (self.config.input_height - 2 * margin)

        # Clamp a 0-1
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        # Aplicar flip según configuración (debe coincidir con calibración del video)
        if self.config.flip_x:
            norm_x = 1.0 - norm_x
        if self.config.flip_y:
            norm_y = 1.0 - norm_y

        # Mapear al área de pantalla configurada
        screen_x = self.config.screen_offset_x + int(norm_x * self.config.screen_width)
        screen_y = self.config.screen_offset_y + int(norm_y * self.config.screen_height)

        # Clamp a límites del área activa
        screen_x = max(self.config.screen_offset_x,
                      min(self.config.screen_offset_x + self.config.screen_width - 1, screen_x))
        screen_y = max(self.config.screen_offset_y,
                      min(self.config.screen_offset_y + self.config.screen_height - 1, screen_y))

        return screen_x, screen_y

    def _move_cursor(self, x: int, y: int):
        """Mover cursor"""
        if not PYAUTOGUI_AVAILABLE:
            return
        try:
            pyautogui.moveTo(x, y, _pause=False)
        except Exception as e:
            logger.error(f"Error moviendo cursor: {e}")

    def _click(self, button: str = 'left'):
        """Realizar clic"""
        if not PYAUTOGUI_AVAILABLE:
            return

        current = time.time()
        if current - self._last_click_time < self.config.click_cooldown:
            return

        self._last_click_time = current

        try:
            pyautogui.click(button=button, _pause=False)
            logger.info(f"🖱️ Clic {button}")
        except Exception as e:
            logger.error(f"Error en clic: {e}")

    def _double_click(self):
        """Doble clic"""
        if not PYAUTOGUI_AVAILABLE:
            return
        try:
            pyautogui.doubleClick(_pause=False)
            logger.info("🖱️ Doble clic")
        except Exception as e:
            logger.error(f"Error doble clic: {e}")

    def _start_drag(self):
        """Iniciar arrastre"""
        if not PYAUTOGUI_AVAILABLE:
            return
        try:
            pyautogui.mouseDown(_pause=False)
            self._touch_state = TouchState.DRAGGING
            logger.info("🖱️ Inicio arrastre")
        except Exception as e:
            logger.error(f"Error arrastre: {e}")

    def _end_drag(self):
        """Finalizar arrastre"""
        if not PYAUTOGUI_AVAILABLE:
            return
        try:
            pyautogui.mouseUp(_pause=False)
            logger.info("🖱️ Fin arrastre")
        except Exception as e:
            logger.error(f"Error fin arrastre: {e}")

    def process_hand(
        self,
        landmarks: List[Dict[str, float]],
        handedness: str = "Right",
        hand_depth: float = 0,
        confidence: float = 0.8,
        gesture: str = ""
    ) -> Dict[str, Any]:
        """
        Procesar mano y controlar mouse.

        Args:
            landmarks: 21 landmarks de MediaPipe
            handedness: "Left" o "Right"
            hand_depth: Profundidad desde Kinect (mm)
            confidence: Confianza de detección
            gesture: Gesto detectado ("pinch", "open_hand", etc.)
        """
        result = {
            'action': MouseAction.NONE.value,
            'finger_position': (0, 0),
            'screen_position': (0, 0),
            'depth': 0,
            'gesture': gesture,
            'touch_state': self._touch_state.value,
            'is_calibrated': True,
            'calibration_progress': 1.0,
            'enabled': self.enabled
        }

        if not self.enabled or not PYAUTOGUI_AVAILABLE:
            return result

        if handedness != self.config.active_hand:
            return result

        if not landmarks or len(landmarks) < 21:
            return result

        with self._lock:
            current_time = time.time()

            # Obtener punta del dedo índice
            index_tip = landmarks[self.INDEX_FINGER_TIP]

            # Posición en píxeles
            finger_x = index_tip['x'] * self.config.input_width
            finger_y = index_tip['y'] * self.config.input_height

            result['finger_position'] = (finger_x, finger_y)

            # Suavizar posición
            smooth_x, smooth_y = self._smooth_position(finger_x, finger_y)

            # Mapear a pantalla
            screen_x, screen_y = self._map_to_screen(smooth_x, smooth_y)
            result['screen_position'] = (screen_x, screen_y)

            # Mover cursor siempre
            self._move_cursor(screen_x, screen_y)

            # Detectar PINCH para clic
            is_pinching = gesture.lower() == 'pinch'

            # Máquina de estados basada en PINCH
            if self._touch_state == TouchState.HOVERING:
                result['action'] = MouseAction.HOVER.value

                if is_pinching and not self._was_pinching:
                    # Inicio de pinch
                    self._touch_state = TouchState.TOUCHING
                    self._pinch_start_time = current_time
                    result['action'] = MouseAction.TOUCH_DOWN.value
                    logger.debug(f"PINCH detectado - inicio touch")

            elif self._touch_state == TouchState.TOUCHING:
                pinch_duration = current_time - self._pinch_start_time

                if not is_pinching:
                    # Soltó el pinch
                    self._touch_state = TouchState.HOVERING
                    result['action'] = MouseAction.TOUCH_UP.value

                    if pinch_duration >= self.config.min_touch_time:
                        # Verificar doble clic
                        if current_time - self._last_touch_up_time < self.config.double_click_window:
                            self._double_click()
                            result['action'] = MouseAction.DOUBLE_CLICK.value
                        else:
                            self._click('left')
                            result['action'] = MouseAction.LEFT_CLICK.value
                            logger.info(f"🖱️ PINCH -> Clic izquierdo")

                    self._last_touch_up_time = current_time

                elif pinch_duration >= self.config.drag_threshold_time:
                    # Mantiene pinch - arrastrar
                    self._start_drag()
                    result['action'] = MouseAction.DRAG_START.value

            elif self._touch_state == TouchState.DRAGGING:
                result['action'] = MouseAction.DRAG_MOVE.value

                if not is_pinching:
                    self._end_drag()
                    self._touch_state = TouchState.HOVERING
                    result['action'] = MouseAction.DRAG_END.value

            # Guardar estado de pinch
            self._was_pinching = is_pinching
            result['touch_state'] = self._touch_state.value

        return result

    def recalibrate(self):
        """Resetear estado (no requiere calibración con pinch)"""
        with self._lock:
            self._reset_state()
        logger.info("Estado reseteado - usa PINCH para clic")

    def get_state(self) -> Dict[str, Any]:
        """Obtener estado"""
        return {
            'enabled': self.enabled,
            'is_calibrated': self._is_calibrated,
            'touch_state': self._touch_state.value,
            'screen_area': {
                'x': self.config.screen_offset_x,
                'y': self.config.screen_offset_y,
                'width': self.config.screen_width,
                'height': self.config.screen_height
            },
            'flip': {
                'x': self.config.flip_x,
                'y': self.config.flip_y
            },
            'pyautogui_available': PYAUTOGUI_AVAILABLE,
            'config': {
                'smoothing': self.config.smoothing,
                'active_hand': self.config.active_hand
            }
        }

    def set_flip(self, flip_x: bool = None, flip_y: bool = None):
        """Configurar flip de ejes (debe coincidir con calibración del video)"""
        if flip_x is not None:
            self.config.flip_x = flip_x
        if flip_y is not None:
            self.config.flip_y = flip_y
        logger.info(f"Flip configurado: X={self.config.flip_x}, Y={self.config.flip_y}")

    def set_smoothing(self, smoothing: float):
        """Ajustar suavizado (0.0 - 0.9)"""
        self.config.smoothing = max(0.0, min(0.9, smoothing))

    def set_active_hand(self, hand: str):
        """Cambiar mano activa"""
        if hand in ["Left", "Right"]:
            self.config.active_hand = hand

    def set_input_resolution(self, width: int, height: int):
        """Configurar resolución de entrada"""
        self.config.input_width = width
        self.config.input_height = height


# Alias
MouseController = TouchMouseController
MouseControlConfig = TouchConfig

_mouse_controller: Optional[TouchMouseController] = None


def get_mouse_controller() -> TouchMouseController:
    global _mouse_controller
    if _mouse_controller is None:
        _mouse_controller = TouchMouseController()
    return _mouse_controller


def is_available() -> bool:
    return PYAUTOGUI_AVAILABLE
