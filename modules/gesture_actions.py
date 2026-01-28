"""
Sistema de Acciones Basado en Gestos
====================================
Mapea gestos reconocidos a acciones del sistema.

Funcionalidades:
- Mapeo gesto → acción configurable
- Acciones sobre objetos (seleccionar, mover, rotar)
- Acciones de sistema (zoom, pan, menú)
- Sistema de eventos (onStart, onMove, onEnd)
- Historial de acciones para undo/redo
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Tuple, Any
import time
import logging
from collections import deque

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Tipos de acciones disponibles"""
    # Acciones sobre objetos
    SELECT = "select"              # Seleccionar objeto
    DESELECT = "deselect"          # Deseleccionar objeto
    MOVE = "move"                  # Mover objeto
    ROTATE = "rotate"              # Rotar objeto
    SCALE = "scale"                # Escalar objeto
    DELETE = "delete"              # Eliminar objeto
    
    # Acciones de navegación
    ZOOM_IN = "zoom_in"            # Acercar vista
    ZOOM_OUT = "zoom_out"          # Alejar vista
    PAN = "pan"                    # Mover vista
    RESET_VIEW = "reset_view"      # Resetear vista
    
    # Acciones de sistema
    MENU_OPEN = "menu_open"        # Abrir menú
    MENU_CLOSE = "menu_close"      # Cerrar menú
    MENU_SELECT = "menu_select"    # Seleccionar en menú
    CONFIRM = "confirm"            # Confirmar acción
    CANCEL = "cancel"              # Cancelar acción
    
    # Acciones especiales
    GRAB = "grab"                  # Agarrar objeto
    RELEASE = "release"            # Soltar objeto
    DRAG = "drag"                  # Arrastrar
    DROP = "drop"                  # Soltar al arrastrar
    CLICK = "click"                # Click simple
    DOUBLE_CLICK = "double_click"  # Doble click
    
    # Sin acción
    NONE = "none"


class ActionState(Enum):
    """Estados de una acción"""
    STARTED = "started"            # Acción iniciada
    IN_PROGRESS = "in_progress"    # Acción en curso
    COMPLETED = "completed"        # Acción completada
    CANCELLED = "cancelled"        # Acción cancelada


@dataclass
class ActionEvent:
    """Evento de acción generado por un gesto"""
    action_type: ActionType
    state: ActionState
    timestamp: float
    
    # Datos del gesto origen
    gesture: str                          # Tipo de gesto
    hand: str                             # "Left" o "Right"
    hand_position: Tuple[float, float]    # Posición (x, y) normalizada
    hand_position_3d: Optional[Tuple[float, float, float]] = None
    
    # Datos de la acción
    target_object_id: Optional[int] = None      # ID del objeto afectado
    target_position: Optional[Tuple[float, float]] = None
    delta: Optional[Tuple[float, float]] = None  # Cambio desde última posición
    value: Optional[float] = None                # Valor numérico (ej: ángulo de rotación)
    
    # Metadatos
    confidence: float = 1.0
    duration: float = 0.0                        # Duración de la acción
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convertir a diccionario para serialización"""
        return {
            'action': self.action_type.value,
            'state': self.state.value,
            'timestamp': self.timestamp,
            'gesture': self.gesture,
            'hand': self.hand,
            'hand_position': self.hand_position,
            'hand_position_3d': self.hand_position_3d,
            'target_object_id': self.target_object_id,
            'target_position': self.target_position,
            'delta': self.delta,
            'value': self.value,
            'confidence': self.confidence,
            'duration': self.duration,
            'metadata': self.metadata
        }


@dataclass
class GestureActionMapping:
    """Mapeo de un gesto a una acción"""
    gesture: str                           # Nombre del gesto
    action: ActionType                     # Acción resultante
    requires_object: bool = False          # Requiere estar sobre un objeto
    continuous: bool = False               # Es una acción continua (drag, rotate)
    hold_time: float = 0.0                 # Tiempo mínimo de mantener gesto (segundos)
    cooldown: float = 0.3                  # Tiempo entre activaciones
    priority: int = 0                      # Prioridad (mayor = preferencia)
    
    # Condiciones adicionales
    min_confidence: float = 0.7
    allowed_hands: List[str] = field(default_factory=lambda: ["Left", "Right"])


class GestureActionMapper:
    """
    Mapea gestos reconocidos a acciones del sistema.
    
    Características:
    - Mapeo configurable de gestos a acciones
    - Soporte para acciones continuas (drag, rotate)
    - Cooldown para evitar activaciones repetidas
    - Priorización de gestos cuando hay conflicto
    - Sistema de callbacks para reaccionar a eventos
    """
    
    # Mapeo por defecto de gestos a acciones
    DEFAULT_MAPPINGS = [
        # Selección y manipulación
        GestureActionMapping(
            gesture="open_palm",
            action=ActionType.SELECT,
            requires_object=True,
            hold_time=0.3,
            priority=10
        ),
        GestureActionMapping(
            gesture="closed_fist",
            action=ActionType.GRAB,
            requires_object=True,
            continuous=True,
            priority=20
        ),
        GestureActionMapping(
            gesture="grab",
            action=ActionType.DRAG,
            requires_object=True,
            continuous=True,
            priority=25
        ),
        GestureActionMapping(
            gesture="pinch",
            action=ActionType.ROTATE,
            requires_object=True,
            continuous=True,
            priority=15
        ),
        
        # Navegación
        GestureActionMapping(
            gesture="pointing",
            action=ActionType.CLICK,
            requires_object=False,
            hold_time=0.0,
            priority=5
        ),
        GestureActionMapping(
            gesture="peace_sign",
            action=ActionType.ZOOM_IN,
            continuous=True,
            priority=10
        ),
        
        # Sistema
        GestureActionMapping(
            gesture="thumbs_up",
            action=ActionType.CONFIRM,
            hold_time=0.5,
            priority=30
        ),
        GestureActionMapping(
            gesture="thumbs_down",
            action=ActionType.CANCEL,
            hold_time=0.5,
            priority=30
        ),
        GestureActionMapping(
            gesture="call_me",
            action=ActionType.MENU_OPEN,
            hold_time=0.3,
            priority=15
        ),
        GestureActionMapping(
            gesture="rock",
            action=ActionType.DELETE,
            requires_object=True,
            hold_time=1.0,  # Requiere mantener para evitar accidentes
            priority=5
        ),
        
        # Acciones especiales
        GestureActionMapping(
            gesture="ok_sign",
            action=ActionType.SCALE,
            requires_object=True,
            continuous=True,
            priority=12
        ),
        GestureActionMapping(
            gesture="love",
            action=ActionType.RESET_VIEW,
            hold_time=0.5,
            priority=8
        ),
    ]
    
    def __init__(self, custom_mappings: Optional[List[GestureActionMapping]] = None):
        """
        Inicializar el mapper
        
        Args:
            custom_mappings: Mapeos personalizados (reemplazan los default)
        """
        # Usar mapeos custom o default
        self.mappings: Dict[str, GestureActionMapping] = {}
        mappings_to_use = custom_mappings if custom_mappings else self.DEFAULT_MAPPINGS
        
        for mapping in mappings_to_use:
            self.mappings[mapping.gesture] = mapping
        
        # Estado de gestos activos por mano
        self.active_gestures: Dict[str, Dict] = {
            "Left": {"gesture": None, "start_time": 0, "last_action_time": 0, "position": (0, 0)},
            "Right": {"gesture": None, "start_time": 0, "last_action_time": 0, "position": (0, 0)}
        }
        
        # Callbacks registrados
        self.callbacks: Dict[ActionType, List[Callable]] = {}
        
        # Historial de acciones
        self.action_history: deque = deque(maxlen=100)
        
        # Estado actual
        self.current_actions: Dict[str, ActionEvent] = {}  # Por mano
        
        logger.info(f"GestureActionMapper inicializado con {len(self.mappings)} mapeos")
    
    def process_gesture(
        self,
        gesture: str,
        hand: str,
        position: Tuple[float, float],
        position_3d: Optional[Tuple[float, float, float]] = None,
        confidence: float = 1.0,
        target_object_id: Optional[int] = None,
        is_over_object: bool = False
    ) -> Optional[ActionEvent]:
        """
        Procesar un gesto detectado y generar evento de acción si corresponde
        
        Args:
            gesture: Nombre del gesto detectado
            hand: "Left" o "Right"
            position: Posición (x, y) normalizada de la mano
            position_3d: Posición 3D opcional
            confidence: Confianza del gesto (0-1)
            target_object_id: ID del objeto bajo la mano (si hay)
            is_over_object: Si la mano está sobre un objeto
            
        Returns:
            ActionEvent si se generó una acción, None si no
        """
        current_time = time.time()
        
        # Obtener estado de esta mano
        hand_state = self.active_gestures.get(hand, {
            "gesture": None, "start_time": 0, "last_action_time": 0, "position": (0, 0)
        })
        
        # Obtener mapeo para este gesto
        mapping = self.mappings.get(gesture)
        
        # Si el gesto cambió, actualizar estado
        if hand_state["gesture"] != gesture:
            # Finalizar acción anterior si era continua
            if hand_state["gesture"]:
                prev_mapping = self.mappings.get(hand_state["gesture"])
                if prev_mapping and prev_mapping.continuous:
                    # Generar evento de finalización
                    end_event = self._create_action_event(
                        prev_mapping.action,
                        ActionState.COMPLETED,
                        hand_state["gesture"],
                        hand,
                        hand_state["position"],
                        position_3d,
                        confidence,
                        target_object_id,
                        current_time - hand_state["start_time"]
                    )
                    self._dispatch_event(end_event)
            
            # Iniciar nuevo gesto
            hand_state["gesture"] = gesture
            hand_state["start_time"] = current_time
            hand_state["position"] = position
        
        # Actualizar posición
        old_position = hand_state["position"]
        hand_state["position"] = position
        
        # Guardar estado actualizado
        self.active_gestures[hand] = hand_state
        
        # Si no hay mapeo para este gesto, retornar None
        if not mapping:
            return None
        
        # Verificar condiciones
        if not self._check_mapping_conditions(mapping, hand, confidence, is_over_object):
            return None
        
        # Calcular delta de posición
        delta = (position[0] - old_position[0], position[1] - old_position[1])
        
        # Calcular tiempo manteniendo el gesto
        hold_duration = current_time - hand_state["start_time"]
        
        # Determinar estado de la acción
        action_state = None
        
        if mapping.continuous:
            # Acciones continuas
            if hold_duration < 0.1:  # Recién iniciado
                action_state = ActionState.STARTED
            else:
                action_state = ActionState.IN_PROGRESS
        else:
            # Acciones discretas - verificar hold_time y cooldown
            time_since_last = current_time - hand_state["last_action_time"]
            
            if hold_duration >= mapping.hold_time and time_since_last >= mapping.cooldown:
                action_state = ActionState.COMPLETED
                hand_state["last_action_time"] = current_time
                self.active_gestures[hand] = hand_state
        
        # Si no hay estado válido, no generar evento
        if action_state is None:
            return None
        
        # Crear evento de acción
        event = self._create_action_event(
            mapping.action,
            action_state,
            gesture,
            hand,
            position,
            position_3d,
            confidence,
            target_object_id,
            hold_duration,
            delta
        )
        
        # Despachar evento
        self._dispatch_event(event)
        
        # Guardar en historial
        self.action_history.append(event)
        
        # Guardar acción actual
        self.current_actions[hand] = event
        
        return event
    
    def _check_mapping_conditions(
        self,
        mapping: GestureActionMapping,
        hand: str,
        confidence: float,
        is_over_object: bool
    ) -> bool:
        """Verificar si se cumplen las condiciones del mapeo"""
        # Verificar confianza mínima
        if confidence < mapping.min_confidence:
            return False
        
        # Verificar mano permitida
        if hand not in mapping.allowed_hands:
            return False
        
        # Verificar si requiere objeto
        if mapping.requires_object and not is_over_object:
            return False
        
        return True
    
    def _create_action_event(
        self,
        action_type: ActionType,
        state: ActionState,
        gesture: str,
        hand: str,
        position: Tuple[float, float],
        position_3d: Optional[Tuple[float, float, float]],
        confidence: float,
        target_object_id: Optional[int],
        duration: float,
        delta: Optional[Tuple[float, float]] = None
    ) -> ActionEvent:
        """Crear un evento de acción"""
        return ActionEvent(
            action_type=action_type,
            state=state,
            timestamp=time.time(),
            gesture=gesture,
            hand=hand,
            hand_position=position,
            hand_position_3d=position_3d,
            target_object_id=target_object_id,
            target_position=position,
            delta=delta,
            confidence=confidence,
            duration=duration
        )
    
    def _dispatch_event(self, event: ActionEvent):
        """Despachar evento a callbacks registrados"""
        callbacks = self.callbacks.get(event.action_type, [])
        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error en callback para {event.action_type}: {e}")
    
    def register_callback(self, action_type: ActionType, callback: Callable[[ActionEvent], None]):
        """
        Registrar callback para un tipo de acción
        
        Args:
            action_type: Tipo de acción a escuchar
            callback: Función a llamar cuando ocurra la acción
        """
        if action_type not in self.callbacks:
            self.callbacks[action_type] = []
        self.callbacks[action_type].append(callback)
        logger.debug(f"Callback registrado para {action_type.value}")
    
    def unregister_callback(self, action_type: ActionType, callback: Callable):
        """Desregistrar callback"""
        if action_type in self.callbacks and callback in self.callbacks[action_type]:
            self.callbacks[action_type].remove(callback)
    
    def add_mapping(self, mapping: GestureActionMapping):
        """Agregar o actualizar un mapeo de gesto"""
        self.mappings[mapping.gesture] = mapping
        logger.info(f"Mapeo agregado: {mapping.gesture} → {mapping.action.value}")
    
    def remove_mapping(self, gesture: str):
        """Eliminar un mapeo de gesto"""
        if gesture in self.mappings:
            del self.mappings[gesture]
            logger.info(f"Mapeo eliminado: {gesture}")
    
    def get_mapping(self, gesture: str) -> Optional[GestureActionMapping]:
        """Obtener mapeo para un gesto"""
        return self.mappings.get(gesture)
    
    def get_all_mappings(self) -> Dict[str, GestureActionMapping]:
        """Obtener todos los mapeos"""
        return self.mappings.copy()
    
    def get_current_action(self, hand: str) -> Optional[ActionEvent]:
        """Obtener acción actual de una mano"""
        return self.current_actions.get(hand)
    
    def get_action_history(self, limit: int = 10) -> List[ActionEvent]:
        """Obtener historial de acciones recientes"""
        return list(self.action_history)[-limit:]
    
    def clear_hand_state(self, hand: str):
        """Limpiar estado de una mano (cuando se pierde tracking)"""
        if hand in self.active_gestures:
            # Si había una acción continua, finalizarla
            state = self.active_gestures[hand]
            if state["gesture"]:
                mapping = self.mappings.get(state["gesture"])
                if mapping and mapping.continuous:
                    end_event = self._create_action_event(
                        mapping.action,
                        ActionState.CANCELLED,
                        state["gesture"],
                        hand,
                        state["position"],
                        None,
                        0.5,
                        None,
                        time.time() - state["start_time"]
                    )
                    self._dispatch_event(end_event)
            
            # Resetear estado
            self.active_gestures[hand] = {
                "gesture": None,
                "start_time": 0,
                "last_action_time": 0,
                "position": (0, 0)
            }
        
        if hand in self.current_actions:
            del self.current_actions[hand]
    
    def to_dict(self) -> Dict:
        """Serializar estado para enviar por WebSocket"""
        return {
            "mappings": {
                gesture: {
                    "action": m.action.value,
                    "requires_object": m.requires_object,
                    "continuous": m.continuous,
                    "hold_time": m.hold_time
                }
                for gesture, m in self.mappings.items()
            },
            "current_actions": {
                hand: event.to_dict() if event else None
                for hand, event in self.current_actions.items()
            },
            "active_gestures": {
                hand: {
                    "gesture": state["gesture"],
                    "duration": time.time() - state["start_time"] if state["gesture"] else 0
                }
                for hand, state in self.active_gestures.items()
            }
        }


# Funciones de utilidad
def create_default_mapper() -> GestureActionMapper:
    """Crear mapper con configuración por defecto"""
    return GestureActionMapper()


def create_minimal_mapper() -> GestureActionMapper:
    """Crear mapper con mapeos mínimos (solo select/drag)"""
    minimal_mappings = [
        GestureActionMapping(
            gesture="open_palm",
            action=ActionType.SELECT,
            requires_object=True,
            hold_time=0.2,
            priority=10
        ),
        GestureActionMapping(
            gesture="closed_fist",
            action=ActionType.DRAG,
            requires_object=True,
            continuous=True,
            priority=20
        ),
        GestureActionMapping(
            gesture="pointing",
            action=ActionType.CLICK,
            requires_object=False,
            priority=5
        ),
    ]
    return GestureActionMapper(minimal_mappings)


def create_stable_mapper() -> GestureActionMapper:
    """
    Crear mapper optimizado para estabilidad.
    
    Solo usa los gestos más confiables:
    - open_palm (🖐️): Seleccionar/deseleccionar objeto
    - closed_fist (✊): Arrastrar objeto seleccionado
    
    Las acciones dependen de la posición de la mano, no de gestos complejos.
    """
    stable_mappings = [
        # Palma abierta = Seleccionar (sobre objeto) o Soltar (objeto ya seleccionado)
        GestureActionMapping(
            gesture="open_palm",
            action=ActionType.SELECT,
            requires_object=False,  # Permite hover sin objeto
            continuous=False,
            hold_time=0.0,  # Instantáneo
            cooldown=0.2,
            priority=10,
            min_confidence=0.5
        ),
        
        # Puño cerrado = Arrastrar (si hay objeto seleccionado)
        GestureActionMapping(
            gesture="closed_fist",
            action=ActionType.GRAB,
            requires_object=False,  # Permite arrastrar objeto ya seleccionado
            continuous=True,
            hold_time=0.0,
            cooldown=0.0,
            priority=20,
            min_confidence=0.5
        ),
    ]
    return GestureActionMapper(stable_mappings)


if __name__ == "__main__":
    # Demo del módulo
    print("=" * 60)
    print("GESTURE ACTION MAPPER - DEMO")
    print("=" * 60)
    
    # Crear mapper
    mapper = create_default_mapper()
    
    # Mostrar mapeos
    print("\nMapeos configurados:")
    for gesture, mapping in mapper.get_all_mappings().items():
        print(f"  {gesture:15} → {mapping.action.value:15} "
              f"(objeto: {mapping.requires_object}, continuo: {mapping.continuous})")
    
    # Registrar callback de ejemplo
    def on_select(event: ActionEvent):
        print(f"\n🎯 SELECT detectado: objeto={event.target_object_id}, mano={event.hand}")
    
    def on_drag(event: ActionEvent):
        print(f"\n🖐️ DRAG: pos={event.hand_position}, delta={event.delta}, state={event.state.value}")
    
    mapper.register_callback(ActionType.SELECT, on_select)
    mapper.register_callback(ActionType.DRAG, on_drag)
    
    # Simular gestos
    print("\n--- Simulando gestos ---")
    
    # Simular open_palm sobre objeto
    event = mapper.process_gesture(
        gesture="open_palm",
        hand="Right",
        position=(0.5, 0.5),
        confidence=0.9,
        target_object_id=1,
        is_over_object=True
    )
    
    import time
    time.sleep(0.4)  # Esperar hold_time
    
    event = mapper.process_gesture(
        gesture="open_palm",
        hand="Right",
        position=(0.5, 0.5),
        confidence=0.9,
        target_object_id=1,
        is_over_object=True
    )
    
    # Simular drag
    for i in range(3):
        event = mapper.process_gesture(
            gesture="closed_fist",
            hand="Right",
            position=(0.5 + i*0.1, 0.5),
            confidence=0.9,
            target_object_id=1,
            is_over_object=True
        )
        time.sleep(0.1)
    
    print("\n✅ Demo completado")
