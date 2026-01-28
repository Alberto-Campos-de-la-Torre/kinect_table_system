"""
Motor de Interacción
====================
Gestiona el estado de interacción entre manos, gestos y objetos.

Funcionalidades:
- Estados de interacción (idle, hover, selected, dragging, rotating)
- Detección de mano sobre objetos (hit testing)
- Selección y manipulación de objetos
- Feedback visual para el frontend
- Sistema de eventos de interacción
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Callable, Any
import time
import logging
import math
from collections import defaultdict

from .gesture_actions import (
    GestureActionMapper,
    ActionType,
    ActionState,
    ActionEvent,
    create_default_mapper,
    create_stable_mapper
)

logger = logging.getLogger(__name__)


class InteractionState(Enum):
    """Estados de interacción de una mano"""
    IDLE = "idle"              # Sin interacción
    HOVER = "hover"            # Sobre un objeto
    SELECTING = "selecting"    # Iniciando selección
    SELECTED = "selected"      # Objeto seleccionado
    DRAGGING = "dragging"      # Arrastrando objeto
    ROTATING = "rotating"      # Rotando objeto
    SCALING = "scaling"        # Escalando objeto
    MENU = "menu"              # En modo menú


@dataclass
class InteractiveObject:
    """Objeto interactivo en la escena"""
    id: int
    class_name: str
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    center: Tuple[float, float]
    confidence: float = 1.0
    
    # Estado de interacción
    is_hovered: bool = False
    is_selected: bool = False
    hovered_by: Optional[str] = None   # "Left" o "Right"
    selected_by: Optional[str] = None
    
    # Transformaciones aplicadas
    offset: Tuple[float, float] = (0.0, 0.0)    # Offset de drag
    rotation: float = 0.0                        # Rotación en grados
    scale: float = 1.0                           # Escala
    
    # Metadata
    created_at: float = field(default_factory=time.time)
    last_interaction: float = field(default_factory=time.time)
    
    @property
    def transformed_center(self) -> Tuple[float, float]:
        """Centro transformado con offset"""
        return (
            self.center[0] + self.offset[0],
            self.center[1] + self.offset[1]
        )
    
    @property
    def transformed_bbox(self) -> Tuple[int, int, int, int]:
        """Bounding box transformado"""
        x, y, w, h = self.bbox
        return (
            int(x + self.offset[0]),
            int(y + self.offset[1]),
            int(w * self.scale),
            int(h * self.scale)
        )
    
    def point_inside(self, px: float, py: float, margin: float = 0) -> bool:
        """Verificar si un punto está dentro del bbox"""
        x, y, w, h = self.transformed_bbox
        return (x - margin <= px <= x + w + margin and
                y - margin <= py <= y + h + margin)
    
    def reset_transform(self):
        """Resetear transformaciones"""
        self.offset = (0.0, 0.0)
        self.rotation = 0.0
        self.scale = 1.0
    
    def to_dict(self) -> Dict:
        """Serializar para envío"""
        result = {
            'id': self.id,
            'class_name': self.class_name,
            'bbox': self.bbox,
            'center': self.center,
            'confidence': self.confidence,
            'is_hovered': self.is_hovered,
            'is_selected': self.is_selected,
            'hovered_by': self.hovered_by,
            'selected_by': self.selected_by,
            'offset': self.offset,
            'rotation': self.rotation,
            'scale': self.scale,
            'transformed_center': self.transformed_center,
            'transformed_bbox': self.transformed_bbox
        }
        # Agregar datos 3D si existen
        if hasattr(self, 'position_3d'):
            result['position_3d'] = self.position_3d
        if hasattr(self, 'color'):
            result['color'] = self.color
        if hasattr(self, 'shape_type'):
            result['shape_type'] = self.shape_type
        return result


@dataclass
class HandState:
    """Estado de interacción de una mano"""
    hand: str  # "Left" o "Right"
    state: InteractionState = InteractionState.IDLE
    
    # Posición
    position: Tuple[float, float] = (0.0, 0.0)
    position_3d: Optional[Tuple[float, float, float]] = None
    
    # Profundidad y área (para zoom 2D/3D)
    depth: float = 0.0  # Profundidad en mm del sensor Kinect
    depth_smoothed: float = 0.0  # Profundidad suavizada
    depth_history: List[float] = field(default_factory=list)  # Historial para suavizado
    bbox_area: float = 0.0  # Área del bounding box actual
    bbox_area_baseline: float = 0.0  # Área de referencia al iniciar drag
    depth_baseline: float = 0.0  # Profundidad de referencia al seleccionar
    current_scale: float = 1.0  # Escala actual (para suavizar)
    position_3d_world: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # Posición 3D del mundo
    
    # Gesto actual
    current_gesture: str = "unknown"
    gesture_confidence: float = 0.0
    
    # Interacción con objetos
    hovered_object_id: Optional[int] = None
    selected_object_id: Optional[int] = None
    
    # Para drag
    drag_start_position: Optional[Tuple[float, float]] = None
    drag_start_object_offset: Optional[Tuple[float, float]] = None
    
    # Para rotate
    rotate_start_angle: float = 0.0
    rotate_start_object_rotation: float = 0.0
    
    # Timestamps
    state_start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        """Serializar para envío"""
        return {
            'hand': self.hand,
            'state': self.state.value,
            'position': self.position,
            'position_3d': self.position_3d,
            'gesture': self.current_gesture,
            'gesture_confidence': self.gesture_confidence,
            'hovered_object_id': self.hovered_object_id,
            'selected_object_id': self.selected_object_id,
            'state_duration': time.time() - self.state_start_time
        }


@dataclass
class InteractionEvent:
    """Evento de interacción para el frontend"""
    type: str
    hand: str
    object_id: Optional[int]
    position: Tuple[float, float]
    data: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            'type': self.type,
            'hand': self.hand,
            'object_id': self.object_id,
            'position': self.position,
            'data': self.data,
            'timestamp': self.timestamp
        }


class InteractionEngine:
    """
    Motor de interacción que procesa gestos y maneja estados.
    
    Características:
    - Hit testing: detectar qué objeto está bajo cada mano
    - Gestión de estados: idle, hover, selected, dragging, etc.
    - Manipulación de objetos: drag, rotate, scale
    - Eventos de interacción para el frontend
    - Soporte para dos manos simultáneas
    """
    
    def __init__(
        self,
        action_mapper: Optional[GestureActionMapper] = None,
        hover_margin: float = 30.0,        # Margen para hit testing (aumentado)
        drag_threshold: float = 5.0,       # Distancia mínima para iniciar drag
        selection_hold_time: float = 0.1,  # Tiempo para selección (reducido)
        use_stable_mode: bool = True,      # Usar modo estable por defecto
    ):
        """
        Inicializar motor de interacción
        
        Args:
            action_mapper: Mapper de gestos a acciones (usa stable si None)
            hover_margin: Margen extra para detección de hover
            drag_threshold: Distancia mínima para iniciar arrastre
            selection_hold_time: Tiempo para confirmar selección
            use_stable_mode: Usar mapper estable (solo palm/fist)
        """
        # Mapper de acciones - usar stable por defecto
        if action_mapper:
            self.action_mapper = action_mapper
        elif use_stable_mode:
            self.action_mapper = create_stable_mapper()
        else:
            self.action_mapper = create_default_mapper()
        
        self.use_stable_mode = use_stable_mode
        
        # Configuración
        self.hover_margin = hover_margin
        self.drag_threshold = drag_threshold
        self.selection_hold_time = selection_hold_time
        
        # Configuración de zoom por profundidad
        self.depth_zoom_enabled = True
        self.depth_baseline_mm = 700.0  # Profundidad de referencia (mm) - aprox 70cm
        self.depth_scale_factor = 0.0008  # Factor de escala por mm de cambio (reducido)
        self.min_scale = 0.5  # Escala mínima
        self.max_scale = 2.5  # Escala máxima
        self.bbox_area_baseline = 15000.0  # Área de referencia para fallback
        
        # Suavizado de profundidad
        self.depth_history_size = 10  # Tamaño del historial para suavizado
        self.scale_smoothing = 0.15  # Factor de suavizado (0-1, menor = más suave)
        self.depth_change_threshold = 150  # Ignorar cambios mayores a este valor (mm)
        
        # Objetos en la escena
        self.objects: Dict[int, InteractiveObject] = {}
        self.next_object_id = 1
        self.demo_object_ids: set = set()  # IDs de objetos de demo (protegidos)
        self.demo_mode: bool = False  # Modo demo activo
        
        # Configuración de espejo
        self.mirror_x: bool = True  # Invertir eje X para efecto espejo
        self.frame_width: int = 640  # Ancho del frame para calcular espejo
        self.frame_height: int = 480  # Alto del frame
        
        # Ángulo de inclinación del Kinect (grados hacia abajo)
        # Usado para corregir la perspectiva cuando el Kinect no está perpendicular
        self.kinect_tilt_angle: float = 0.0
        
        # Estado de las manos
        self.hands: Dict[str, HandState] = {
            "Left": HandState(hand="Left"),
            "Right": HandState(hand="Right")
        }
        
        # Eventos pendientes para enviar
        self.pending_events: List[InteractionEvent] = []
        
        # Callbacks
        self.event_callbacks: List[Callable[[InteractionEvent], None]] = []
        
        # Registrar callbacks en el action mapper
        self._register_action_callbacks()
        
        # Estadísticas
        self.stats = {
            'interactions': 0,
            'selections': 0,
            'drags': 0,
            'hovers': 0
        }
        
        logger.info("InteractionEngine inicializado")
    
    def _register_action_callbacks(self):
        """Registrar callbacks para acciones del mapper"""
        self.action_mapper.register_callback(ActionType.SELECT, self._on_select_action)
        self.action_mapper.register_callback(ActionType.DRAG, self._on_drag_action)
        self.action_mapper.register_callback(ActionType.GRAB, self._on_grab_action)
        self.action_mapper.register_callback(ActionType.ROTATE, self._on_rotate_action)
        self.action_mapper.register_callback(ActionType.SCALE, self._on_scale_action)
        self.action_mapper.register_callback(ActionType.DESELECT, self._on_deselect_action)
        self.action_mapper.register_callback(ActionType.CONFIRM, self._on_confirm_action)
        self.action_mapper.register_callback(ActionType.CANCEL, self._on_cancel_action)
    
    def update_objects(self, detections: List[Dict]):
        """
        Actualizar objetos desde detecciones del sistema.
        En modo demo, NO actualiza ni elimina objetos de demo.
        
        Args:
            detections: Lista de detecciones de objetos
        """
        # En modo demo, ignorar detecciones de YOLO
        if self.demo_mode:
            return
        
        # Mapear detecciones existentes por posición
        current_ids = set()
        
        for det in detections:
            # Buscar objeto existente cercano (excluyendo objetos de demo)
            obj_id = self._find_matching_object(det)
            
            if obj_id is None:
                # Nuevo objeto
                obj_id = self.next_object_id
                self.next_object_id += 1
                
                self.objects[obj_id] = InteractiveObject(
                    id=obj_id,
                    class_name=det.get('class_name', 'unknown'),
                    bbox=(
                        det.get('bbox', {}).get('x', 0),
                        det.get('bbox', {}).get('y', 0),
                        det.get('bbox', {}).get('width', 100),
                        det.get('bbox', {}).get('height', 100)
                    ),
                    center=(
                        det.get('center', {}).get('x', 0),
                        det.get('center', {}).get('y', 0)
                    ),
                    confidence=det.get('confidence', 1.0)
                )
            else:
                # Actualizar objeto existente
                obj = self.objects[obj_id]
                obj.bbox = (
                    det.get('bbox', {}).get('x', obj.bbox[0]),
                    det.get('bbox', {}).get('y', obj.bbox[1]),
                    det.get('bbox', {}).get('width', obj.bbox[2]),
                    det.get('bbox', {}).get('height', obj.bbox[3])
                )
                obj.center = (
                    det.get('center', {}).get('x', obj.center[0]),
                    det.get('center', {}).get('y', obj.center[1])
                )
                obj.confidence = det.get('confidence', obj.confidence)
            
            current_ids.add(obj_id)
        
        # Eliminar objetos que ya no se detectan (excepto demo y seleccionados)
        to_remove = []
        for obj_id, obj in self.objects.items():
            # NUNCA eliminar objetos de demo
            if obj_id in self.demo_object_ids:
                continue
            if obj_id not in current_ids and not obj.is_selected:
                # Solo eliminar si pasó tiempo suficiente
                if time.time() - obj.last_interaction > 2.0:
                    to_remove.append(obj_id)
        
        for obj_id in to_remove:
            del self.objects[obj_id]
    
    def _find_matching_object(self, detection: Dict) -> Optional[int]:
        """Encontrar objeto existente que coincida con la detección (excluyendo objetos de demo)"""
        det_center = (
            detection.get('center', {}).get('x', 0),
            detection.get('center', {}).get('y', 0)
        )
        det_class = detection.get('class_name', '')
        
        best_match = None
        best_distance = float('inf')
        
        for obj_id, obj in self.objects.items():
            # Nunca coincidir con objetos de demo
            if obj_id in self.demo_object_ids:
                continue
                
            # Solo coincidir si es la misma clase
            if obj.class_name != det_class:
                continue
            
            # Calcular distancia
            dx = obj.center[0] - det_center[0]
            dy = obj.center[1] - det_center[1]
            distance = math.sqrt(dx*dx + dy*dy)
            
            # Si está cerca y es el más cercano
            if distance < 100 and distance < best_distance:
                best_distance = distance
                best_match = obj_id
        
        return best_match
    
    def process_hand(
        self,
        hand: str,
        position: Tuple[float, float],
        gesture: str,
        confidence: float = 1.0,
        position_3d: Optional[Tuple[float, float, float]] = None,
        depth: float = 0.0,
        bbox_area: float = 0.0
    ) -> Optional[ActionEvent]:
        """
        Procesar actualización de una mano
        
        En modo estable:
        - open_palm sobre objeto: hover → selección automática
        - closed_fist con objeto seleccionado: arrastrar por posición
        - La profundidad controla el zoom de los objetos seleccionados
        
        Args:
            hand: "Left" o "Right"
            position: Posición (x, y) en pixels
            gesture: Nombre del gesto detectado
            confidence: Confianza del gesto
            position_3d: Posición 3D opcional
            depth: Profundidad de la mano en mm (del sensor Kinect)
            bbox_area: Área del bounding box de la mano (fallback para zoom)
            
        Returns:
            ActionEvent si se generó una acción
        """
        if hand not in self.hands:
            return None
        
        hand_state = self.hands[hand]
        current_time = time.time()
        
        # Aplicar efecto espejo si está habilitado
        # NOTA: El sensor ve la imagen invertida, así que NO invertimos
        # para que el movimiento sea natural (derecha física = derecha en pantalla)
        # Si mirror_x es True, NO aplicamos inversión (ya está correcto)
        # Si mirror_x es False, invertimos
        if not self.mirror_x:
            position = (self.frame_width - position[0], position[1])
        
        # Corrección de perspectiva por inclinación del Kinect
        # Cuando el Kinect está inclinado, la posición Y en la imagen necesita corrección
        if self.kinect_tilt_angle != 0.0 and depth > 100:  # depth > 100mm para asegurar dato válido
            """
            EXPLICACIÓN DEL CÁLCULO:
            
            Cuando el Kinect está inclinado θ grados hacia abajo:
            - Los objetos más lejanos aparecen más arriba en la imagen
            - Los objetos más cercanos aparecen más abajo
            
            Para corregir esto, movemos la posición Y según:
            1. El ángulo de inclinación (más ángulo = más corrección)
            2. La profundidad de la mano (más profundidad = más corrección)
            
            Fórmula: y_correction = tan(θ) × profundidad_normalizada × altura_frame × factor_escala
            """
            tilt_rad = math.radians(self.kinect_tilt_angle)
            
            # Profundidad normalizada (rango típico 400-1500mm para manos sobre mesa)
            # 400mm = mano muy levantada, 1500mm = mano en la mesa
            depth_normalized = (depth - 400) / 1100.0
            depth_normalized = max(0, min(1, depth_normalized))
            
            # Corrección de Y basada en geometría de perspectiva
            # Factor 0.4 ajustado para el campo de visión del Kinect (~57° vertical)
            y_correction = math.tan(tilt_rad) * depth_normalized * self.frame_height * 0.4
            
            original_y = position[1]
            new_y = position[1] + y_correction
            new_y = max(0, min(self.frame_height, new_y))
            
            # Log solo ocasionalmente para no saturar
            if hasattr(self, '_tilt_log_counter'):
                self._tilt_log_counter += 1
            else:
                self._tilt_log_counter = 0
            
            if self._tilt_log_counter % 30 == 0:  # Log cada 30 frames
                logger.debug(f"📐 Tilt correction: angle={self.kinect_tilt_angle}°, "
                           f"depth={depth:.0f}mm, y: {original_y:.0f} → {new_y:.0f} "
                           f"(Δ{y_correction:+.1f}px)")
            
            position = (position[0], new_y)
        
        # Filtrar gestos en modo estable - solo open_palm y closed_fist
        if self.use_stable_mode:
            # Gestos que se interpretan como PUÑO CERRADO (mano cerrada/agarrando)
            fist_like_gestures = ['pinch', 'grab', 'thumbs_up', 'thumbs_down']
            
            # Gestos que se interpretan como PALMA ABIERTA (dedos extendidos)
            palm_like_gestures = ['four', 'three', 'ok_sign', 'peace_sign', 'love', 'rock', 'call_me', 'spiderman']
            
            # Gestos ambiguos que mantienen el estado anterior
            ambiguous_gestures = ['pointing', 'gun', 'unknown']
            
            if gesture in fist_like_gestures:
                gesture = 'closed_fist'
            elif gesture in palm_like_gestures:
                gesture = 'open_palm'
            elif gesture in ambiguous_gestures:
                # Mantener gesto anterior para evitar cambios bruscos
                gesture = hand_state.current_gesture if hand_state.current_gesture in ['open_palm', 'closed_fist'] else 'open_palm'
            elif gesture not in ['open_palm', 'closed_fist']:
                # Cualquier otro gesto desconocido → mantener anterior
                gesture = hand_state.current_gesture if hand_state.current_gesture in ['open_palm', 'closed_fist'] else 'open_palm'
        
        # Actualizar posición, gesto y profundidad
        old_position = hand_state.position
        old_gesture = hand_state.current_gesture
        hand_state.position = position
        hand_state.position_3d = position_3d
        hand_state.current_gesture = gesture
        hand_state.gesture_confidence = confidence
        hand_state.last_update = current_time
        hand_state.bbox_area = bbox_area
        
        # Suavizar profundidad para evitar saltos bruscos
        hand_state.depth = depth
        if depth > 0:
            # Filtrar cambios bruscos (probablemente errores del sensor)
            if len(hand_state.depth_history) > 0:
                last_depth = hand_state.depth_history[-1]
                if abs(depth - last_depth) > self.depth_change_threshold:
                    # Cambio muy brusco, usar valor anterior
                    depth = last_depth
            
            # Agregar al historial
            hand_state.depth_history.append(depth)
            if len(hand_state.depth_history) > self.depth_history_size:
                hand_state.depth_history.pop(0)
            
            # Calcular profundidad suavizada (media móvil)
            if len(hand_state.depth_history) >= 3:
                # Usar mediana para filtrar outliers
                sorted_depths = sorted(hand_state.depth_history)
                mid = len(sorted_depths) // 2
                hand_state.depth_smoothed = sorted_depths[mid]
            else:
                hand_state.depth_smoothed = depth
        else:
            hand_state.depth_smoothed = hand_state.depth_smoothed  # Mantener valor anterior
        
        # Calcular posición 3D del mundo
        hand_state.position_3d_world = self._calculate_position_3d(hand_state)
        
        # Hit testing - encontrar objeto bajo la mano
        hovered_obj = self._find_object_at(position)
        old_hovered_id = hand_state.hovered_object_id
        
        action_event = None
        
        if self.use_stable_mode:
            # ===== MODO ESTABLE =====
            # Lógica simplificada basada en posición y solo 2 gestos
            
            # Actualizar hover
            if hovered_obj:
                hand_state.hovered_object_id = hovered_obj.id
                if old_hovered_id != hovered_obj.id:
                    self._emit_event('hover_start', hand, hovered_obj.id, position)
                    self.stats['hovers'] += 1
                    if old_hovered_id and old_hovered_id in self.objects:
                        self.objects[old_hovered_id].is_hovered = False
                        self.objects[old_hovered_id].hovered_by = None
                    hovered_obj.is_hovered = True
                    hovered_obj.hovered_by = hand
            else:
                if old_hovered_id:
                    self._emit_event('hover_end', hand, old_hovered_id, position)
                    if old_hovered_id in self.objects:
                        self.objects[old_hovered_id].is_hovered = False
                        self.objects[old_hovered_id].hovered_by = None
                hand_state.hovered_object_id = None
            
            # Procesar según gesto actual
            if gesture == "closed_fist":
                # PUÑO CERRADO: Arrastrar
                if hand_state.state == InteractionState.DRAGGING:
                    # Continuar arrastrando (incluyendo zoom por profundidad)
                    self._handle_drag_update(hand_state, position)
                elif hand_state.selected_object_id:
                    # Iniciar arrastre si hay objeto seleccionado
                    obj = self.objects.get(hand_state.selected_object_id)
                    if obj:
                        hand_state.state = InteractionState.DRAGGING
                        hand_state.drag_start_position = position
                        hand_state.drag_start_object_offset = obj.offset
                        hand_state.state_start_time = current_time
                        # Guardar baselines para zoom
                        hand_state.depth_baseline = hand_state.depth_smoothed if hand_state.depth_smoothed > 0 else self.depth_baseline_mm
                        hand_state.bbox_area_baseline = hand_state.bbox_area if hand_state.bbox_area > 0 else self.bbox_area_baseline
                        hand_state.current_scale = obj.scale
                        hand_state.depth_history.clear()
                        self._emit_event('drag_start', hand, obj.id, position)
                        self.stats['drags'] += 1
                elif hovered_obj:
                    # Seleccionar y empezar a arrastrar inmediatamente
                    hovered_obj.is_selected = True
                    hovered_obj.selected_by = hand
                    hand_state.selected_object_id = hovered_obj.id
                    hand_state.state = InteractionState.DRAGGING
                    hand_state.drag_start_position = position
                    hand_state.drag_start_object_offset = hovered_obj.offset
                    hand_state.state_start_time = current_time
                    # Guardar baselines para zoom
                    hand_state.depth_baseline = hand_state.depth_smoothed if hand_state.depth_smoothed > 0 else self.depth_baseline_mm
                    hand_state.bbox_area_baseline = hand_state.bbox_area if hand_state.bbox_area > 0 else self.bbox_area_baseline
                    hand_state.current_scale = hovered_obj.scale
                    hand_state.depth_history.clear()
                    self._emit_event('select', hand, hovered_obj.id, position)
                    self._emit_event('drag_start', hand, hovered_obj.id, position)
                    self.stats['selections'] += 1
                    self.stats['drags'] += 1
                    
            elif gesture == "open_palm":
                # PALMA ABIERTA: Soltar objeto
                if hand_state.state == InteractionState.DRAGGING:
                    # Soltar objeto arrastrado
                    self._finish_drag(hand_state)
                    hand_state.state = InteractionState.IDLE
                    # Deseleccionar el objeto
                    if hand_state.selected_object_id:
                        obj = self.objects.get(hand_state.selected_object_id)
                        if obj:
                            obj.is_selected = False
                            obj.selected_by = None
                        self._emit_event('deselect', hand, hand_state.selected_object_id, position)
                        hand_state.selected_object_id = None
                    # NO seleccionar otro objeto inmediatamente después de soltar
                    # El usuario debe cerrar puño para seleccionar de nuevo
                elif hand_state.selected_object_id:
                    # Si hay objeto seleccionado pero no estamos arrastrando, deseleccionar
                    obj = self.objects.get(hand_state.selected_object_id)
                    if obj:
                        obj.is_selected = False
                        obj.selected_by = None
                    self._emit_event('deselect', hand, hand_state.selected_object_id, position)
                    hand_state.selected_object_id = None
                    hand_state.state = InteractionState.IDLE
                # Con palma abierta solo hacemos hover, NO seleccionamos
                # El usuario debe cerrar el puño para seleccionar/agarrar
                else:
                    # Palma abierta = solo hover
                    hand_state.state = InteractionState.HOVER if hovered_obj else InteractionState.IDLE
            else:
                # Otros gestos: mantener estado actual pero actualizar arrastre si aplica
                if hand_state.state == InteractionState.DRAGGING:
                    self._handle_drag_update(hand_state, position)
                    
        else:
            # ===== MODO NORMAL (con action mapper) =====
            # Actualizar hover
            if hovered_obj:
                hand_state.hovered_object_id = hovered_obj.id
                if old_hovered_id != hovered_obj.id:
                    self._emit_event('hover_start', hand, hovered_obj.id, position)
                    self.stats['hovers'] += 1
                    if old_hovered_id and old_hovered_id in self.objects:
                        self.objects[old_hovered_id].is_hovered = False
                        self.objects[old_hovered_id].hovered_by = None
                    hovered_obj.is_hovered = True
                    hovered_obj.hovered_by = hand
            else:
                if old_hovered_id:
                    self._emit_event('hover_end', hand, old_hovered_id, position)
                    if old_hovered_id in self.objects:
                        self.objects[old_hovered_id].is_hovered = False
                        self.objects[old_hovered_id].hovered_by = None
                hand_state.hovered_object_id = None
            
            # Procesar gesto a través del action mapper
            is_over_object = hovered_obj is not None
            target_id = hovered_obj.id if hovered_obj else hand_state.selected_object_id
            
            action_event = self.action_mapper.process_gesture(
                gesture=gesture,
                hand=hand,
                position=position,
                position_3d=position_3d,
                confidence=confidence,
                target_object_id=target_id,
                is_over_object=is_over_object
            )
            
            # Manejar estados de arrastre
            if hand_state.state == InteractionState.DRAGGING:
                self._handle_drag_update(hand_state, position)
            elif hand_state.state == InteractionState.ROTATING:
                self._handle_rotate_update(hand_state, position)
            elif hand_state.state == InteractionState.SCALING:
                self._handle_scale_update(hand_state, position)
        
        self.stats['interactions'] += 1
        
        return action_event
    
    def _find_object_at(self, position: Tuple[float, float]) -> Optional[InteractiveObject]:
        """Encontrar objeto en una posición"""
        px, py = position
        
        # Priorizar objetos seleccionados
        for obj in self.objects.values():
            if obj.is_selected and obj.point_inside(px, py, self.hover_margin):
                return obj
        
        # Buscar en todos los objetos
        for obj in self.objects.values():
            if obj.point_inside(px, py, self.hover_margin):
                return obj
        
        return None
    
    def _emit_event(
        self,
        event_type: str,
        hand: str,
        object_id: Optional[int],
        position: Tuple[float, float],
        data: Dict = None
    ):
        """Emitir evento de interacción"""
        event = InteractionEvent(
            type=event_type,
            hand=hand,
            object_id=object_id,
            position=position,
            data=data or {}
        )
        
        self.pending_events.append(event)
        
        # Notificar callbacks
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error en callback de evento: {e}")
    
    def get_pending_events(self) -> List[InteractionEvent]:
        """Obtener y limpiar eventos pendientes"""
        events = self.pending_events.copy()
        self.pending_events.clear()
        return events
    
    # ========== Action Callbacks ==========
    
    def _on_select_action(self, event: ActionEvent):
        """Manejar acción de selección"""
        if event.state != ActionState.COMPLETED:
            return
        
        hand_state = self.hands.get(event.hand)
        if not hand_state:
            return
        
        obj_id = event.target_object_id
        if obj_id and obj_id in self.objects:
            obj = self.objects[obj_id]
            
            # Deseleccionar objeto anterior si hay
            if hand_state.selected_object_id:
                old_obj = self.objects.get(hand_state.selected_object_id)
                if old_obj:
                    old_obj.is_selected = False
                    old_obj.selected_by = None
            
            # Seleccionar nuevo objeto
            obj.is_selected = True
            obj.selected_by = event.hand
            obj.last_interaction = time.time()
            
            hand_state.selected_object_id = obj_id
            hand_state.state = InteractionState.SELECTED
            hand_state.state_start_time = time.time()
            
            self._emit_event('select', event.hand, obj_id, event.hand_position, {
                'class_name': obj.class_name
            })
            
            self.stats['selections'] += 1
            logger.debug(f"Objeto {obj_id} seleccionado por {event.hand}")
    
    def _on_drag_action(self, event: ActionEvent):
        """Manejar acción de arrastre"""
        hand_state = self.hands.get(event.hand)
        if not hand_state:
            return
        
        obj_id = event.target_object_id or hand_state.selected_object_id
        
        if event.state == ActionState.STARTED:
            # Iniciar arrastre
            if obj_id and obj_id in self.objects:
                obj = self.objects[obj_id]
                
                hand_state.state = InteractionState.DRAGGING
                hand_state.drag_start_position = event.hand_position
                hand_state.drag_start_object_offset = obj.offset
                hand_state.state_start_time = time.time()
                
                self._emit_event('drag_start', event.hand, obj_id, event.hand_position)
                self.stats['drags'] += 1
        
        elif event.state == ActionState.IN_PROGRESS:
            # Continuar arrastre
            if hand_state.state == InteractionState.DRAGGING:
                self._handle_drag_update(hand_state, event.hand_position)
        
        elif event.state == ActionState.COMPLETED:
            # Finalizar arrastre
            if hand_state.state == InteractionState.DRAGGING:
                self._finish_drag(hand_state)
    
    def _on_grab_action(self, event: ActionEvent):
        """Manejar acción de agarrar (similar a drag)"""
        # Reutilizar lógica de drag
        self._on_drag_action(event)
    
    def _on_rotate_action(self, event: ActionEvent):
        """Manejar acción de rotación"""
        hand_state = self.hands.get(event.hand)
        if not hand_state:
            return
        
        obj_id = event.target_object_id or hand_state.selected_object_id
        
        if event.state == ActionState.STARTED:
            if obj_id and obj_id in self.objects:
                obj = self.objects[obj_id]
                
                hand_state.state = InteractionState.ROTATING
                hand_state.rotate_start_angle = self._calculate_angle(
                    obj.center, event.hand_position
                )
                hand_state.rotate_start_object_rotation = obj.rotation
                hand_state.state_start_time = time.time()
                
                self._emit_event('rotate_start', event.hand, obj_id, event.hand_position)
        
        elif event.state == ActionState.COMPLETED:
            if hand_state.state == InteractionState.ROTATING:
                hand_state.state = InteractionState.SELECTED
                self._emit_event('rotate_end', event.hand, obj_id, event.hand_position)
    
    def _on_scale_action(self, event: ActionEvent):
        """Manejar acción de escala"""
        hand_state = self.hands.get(event.hand)
        if not hand_state:
            return
        
        obj_id = event.target_object_id or hand_state.selected_object_id
        
        if event.state == ActionState.STARTED:
            if obj_id and obj_id in self.objects:
                hand_state.state = InteractionState.SCALING
                hand_state.state_start_time = time.time()
                self._emit_event('scale_start', event.hand, obj_id, event.hand_position)
        
        elif event.state == ActionState.COMPLETED:
            if hand_state.state == InteractionState.SCALING:
                hand_state.state = InteractionState.SELECTED
                self._emit_event('scale_end', event.hand, obj_id, event.hand_position)
    
    def _on_deselect_action(self, event: ActionEvent):
        """Manejar acción de deselección"""
        hand_state = self.hands.get(event.hand)
        if not hand_state:
            return
        
        if hand_state.selected_object_id:
            obj = self.objects.get(hand_state.selected_object_id)
            if obj:
                obj.is_selected = False
                obj.selected_by = None
            
            self._emit_event('deselect', event.hand, hand_state.selected_object_id,
                           event.hand_position)
            
            hand_state.selected_object_id = None
            hand_state.state = InteractionState.IDLE
    
    def _on_confirm_action(self, event: ActionEvent):
        """Manejar acción de confirmación"""
        if event.state == ActionState.COMPLETED:
            self._emit_event('confirm', event.hand, None, event.hand_position)
    
    def _on_cancel_action(self, event: ActionEvent):
        """Manejar acción de cancelación"""
        if event.state == ActionState.COMPLETED:
            hand_state = self.hands.get(event.hand)
            if hand_state and hand_state.selected_object_id:
                # Cancelar y resetear objeto
                obj = self.objects.get(hand_state.selected_object_id)
                if obj:
                    obj.reset_transform()
                    obj.is_selected = False
                    obj.selected_by = None
                
                hand_state.selected_object_id = None
                hand_state.state = InteractionState.IDLE
            
            self._emit_event('cancel', event.hand, None, event.hand_position)
    
    # ========== Drag/Rotate/Scale Updates ==========
    
    def _handle_drag_update(self, hand_state: HandState, position: Tuple[float, float]):
        """Actualizar arrastre en progreso (incluyendo zoom y posición 3D)"""
        if not hand_state.selected_object_id:
            return
        
        obj = self.objects.get(hand_state.selected_object_id)
        if not obj or not hand_state.drag_start_position:
            return
        
        # Calcular delta desde inicio
        dx = position[0] - hand_state.drag_start_position[0]
        dy = position[1] - hand_state.drag_start_position[1]
        
        # Aplicar offset 2D
        start_offset = hand_state.drag_start_object_offset or (0, 0)
        obj.offset = (start_offset[0] + dx, start_offset[1] + dy)
        obj.last_interaction = time.time()
        
        # Calcular zoom basado en área (modo 2D)
        if self.depth_zoom_enabled:
            new_scale = self._calculate_depth_scale(hand_state)
            obj.scale = new_scale
        
        # Actualizar posición 3D del objeto (para modo 3D)
        # El objeto sigue la posición 3D de la mano
        if hasattr(obj, 'position_3d') and hand_state.position_3d_world:
            hand_pos = hand_state.position_3d_world
            # El objeto se mueve con la mano
            obj.position_3d = (hand_pos[0], hand_pos[1], hand_pos[2])
        
        self._emit_event('drag_move', hand_state.hand, obj.id, position, {
            'offset': obj.offset,
            'delta': (dx, dy),
            'scale': obj.scale,
            'position_3d': getattr(obj, 'position_3d', None)
        })
    
    def _calculate_depth_scale(self, hand_state: HandState) -> float:
        """
        Calcular escala basada en el área de la mano (modo 2D estable).
        
        Área mayor (mano más cerca) = escala mayor
        Área menor (mano más lejos) = escala menor
        
        Args:
            hand_state: Estado de la mano
            
        Returns:
            Factor de escala suavizado (0.5 a 2.5)
        """
        # MODO 2D ESTABLE: Usar área del bounding box
        # El área es más estable que la profundidad del sensor
        if hand_state.bbox_area > 0 and hand_state.bbox_area_baseline > 0:
            # Calcular ratio de área
            area_ratio = hand_state.bbox_area / hand_state.bbox_area_baseline
            
            # Aplicar curva suave (raíz cuadrada para menos sensibilidad)
            # sqrt hace que los cambios grandes tengan menos impacto
            target_scale = math.sqrt(area_ratio)
            
            # Limitar a rango válido
            target_scale = max(self.min_scale, min(self.max_scale, target_scale))
        else:
            # Sin datos de área, mantener escala actual
            return hand_state.current_scale
        
        # Suavizar el cambio de escala (interpolación)
        current = hand_state.current_scale
        smoothed_scale = current + (target_scale - current) * self.scale_smoothing
        
        # Actualizar escala en el estado
        hand_state.current_scale = smoothed_scale
        
        return smoothed_scale
    
    def _calculate_position_3d(self, hand_state: HandState) -> Tuple[float, float, float]:
        """
        Calcular posición 3D cuando el sensor Kinect está ARRIBA mirando hacia ABAJO.
        
        Configuración física:
        - Kinect montado arriba de la mesa, apuntando hacia abajo
        - La mano se mueve sobre la superficie de la mesa
        - Efecto espejo aplicado para que sea como mirarse en un espejo
        
        Mapeo intuitivo:
        - Posición horizontal (x_pixel) → Eje X (izquierda/derecha) CON ESPEJO
        - Posición vertical en cámara (y_pixel) → Eje Z (cerca/lejos en la mesa)
        - Profundidad (distancia al sensor) → Eje Y (altura de la mano)
          * Mano cerca del sensor = mano levantada = Y alto
          * Mano lejos del sensor = mano en la mesa = Y bajo
        
        Args:
            hand_state: Estado de la mano
            
        Returns:
            Posición (x, y, z) en metros
        """
        # La posición ya viene con espejo aplicado desde process_hand
        x_pixel, y_pixel = hand_state.position
        depth_mm = hand_state.depth_smoothed if hand_state.depth_smoothed > 0 else hand_state.depth
        
        if depth_mm <= 0:
            depth_mm = 700  # Valor por defecto
        
        # Dimensiones del frame
        frame_width = self.frame_width
        frame_height = 480
        
        # X: Posición horizontal (ya con espejo aplicado)
        # El espejo ya se aplicó en process_hand, así que aquí solo convertimos
        x = (x_pixel / frame_width - 0.5) * 0.8  # [-0.4, 0.4] metros
        
        # Z: Posición vertical en cámara → Z del mundo (profundidad en la mesa)
        # Arriba en la imagen = más lejos de la cámara = Z negativo
        # Abajo en la imagen = más cerca de la cámara = Z positivo
        z = (y_pixel / frame_height - 0.5) * 0.6  # [-0.3, 0.3] metros
        
        # Y: Profundidad del sensor → Altura de la mano sobre la mesa
        # Sensor arriba: distancia menor = mano más alta, distancia mayor = mano más baja
        # Rango típico: 400mm (mano muy levantada) a 900mm (mano en la mesa)
        depth_normalized = (depth_mm - 400) / 500  # 400-900mm → 0-1
        depth_normalized = max(0, min(1, depth_normalized))
        # Invertir: menos distancia = más alto
        y = 0.35 - depth_normalized * 0.33  # 0.35 (levantada) a 0.02 (en mesa)
        
        return (x, y, z)
    
    def _handle_rotate_update(self, hand_state: HandState, position: Tuple[float, float]):
        """Actualizar rotación en progreso"""
        if not hand_state.selected_object_id:
            return
        
        obj = self.objects.get(hand_state.selected_object_id)
        if not obj:
            return
        
        # Calcular ángulo actual
        current_angle = self._calculate_angle(obj.center, position)
        delta_angle = current_angle - hand_state.rotate_start_angle
        
        # Aplicar rotación
        obj.rotation = hand_state.rotate_start_object_rotation + delta_angle
        obj.last_interaction = time.time()
        
        self._emit_event('rotate_move', hand_state.hand, obj.id, position, {
            'rotation': obj.rotation,
            'delta_angle': delta_angle
        })
    
    def _handle_scale_update(self, hand_state: HandState, position: Tuple[float, float]):
        """Actualizar escala en progreso"""
        if not hand_state.selected_object_id:
            return
        
        obj = self.objects.get(hand_state.selected_object_id)
        if not obj:
            return
        
        # Escala basada en distancia vertical del gesto
        # (simplificado - en producción usar dos manos o pinch)
        obj.last_interaction = time.time()
    
    def _finish_drag(self, hand_state: HandState):
        """Finalizar arrastre"""
        obj_id = hand_state.selected_object_id
        if obj_id and obj_id in self.objects:
            obj = self.objects[obj_id]
            
            # Aplicar offset al bbox permanentemente
            x, y, w, h = obj.bbox
            obj.bbox = (
                int(x + obj.offset[0]),
                int(y + obj.offset[1]),
                w, h
            )
            obj.center = (
                obj.center[0] + obj.offset[0],
                obj.center[1] + obj.offset[1]
            )
            obj.offset = (0.0, 0.0)
            
            self._emit_event('drag_end', hand_state.hand, obj_id, hand_state.position, {
                'final_position': obj.center
            })
        
        hand_state.state = InteractionState.SELECTED
        hand_state.drag_start_position = None
        hand_state.drag_start_object_offset = None
    
    def _calculate_angle(
        self,
        center: Tuple[float, float],
        point: Tuple[float, float]
    ) -> float:
        """Calcular ángulo desde centro a punto"""
        dx = point[0] - center[0]
        dy = point[1] - center[1]
        return math.degrees(math.atan2(dy, dx))
    
    # ========== Public API ==========
    
    def clear_hand(self, hand: str):
        """Limpiar estado de una mano (cuando se pierde tracking)"""
        if hand not in self.hands:
            return
        
        hand_state = self.hands[hand]
        
        # Cancelar arrastre si estaba activo
        if hand_state.state == InteractionState.DRAGGING:
            self._finish_drag(hand_state)
        
        # Deseleccionar objeto si había uno seleccionado
        if hand_state.selected_object_id and hand_state.selected_object_id in self.objects:
            obj = self.objects[hand_state.selected_object_id]
            obj.is_selected = False
            obj.selected_by = None
            self._emit_event('deselect', hand, hand_state.selected_object_id, hand_state.position)
        
        # Limpiar hover
        if hand_state.hovered_object_id and hand_state.hovered_object_id in self.objects:
            obj = self.objects[hand_state.hovered_object_id]
            obj.is_hovered = False
            obj.hovered_by = None
        
        # Resetear estado completamente
        hand_state.state = InteractionState.IDLE
        hand_state.selected_object_id = None
        hand_state.hovered_object_id = None
        hand_state.current_gesture = "unknown"
        hand_state.gesture_confidence = 0.0
        hand_state.drag_start_position = None
        hand_state.drag_start_object_offset = None
        
        # Limpiar en action mapper
        self.action_mapper.clear_hand_state(hand)
    
    def deselect_all(self):
        """Deseleccionar todos los objetos"""
        for obj in self.objects.values():
            obj.is_selected = False
            obj.selected_by = None
            obj.is_hovered = False
            obj.hovered_by = None
        
        for hand_state in self.hands.values():
            hand_state.selected_object_id = None
            hand_state.hovered_object_id = None
            hand_state.state = InteractionState.IDLE
    
    def get_selected_objects(self) -> List[InteractiveObject]:
        """Obtener objetos seleccionados"""
        return [obj for obj in self.objects.values() if obj.is_selected]
    
    def get_hovered_objects(self) -> List[InteractiveObject]:
        """Obtener objetos en hover"""
        return [obj for obj in self.objects.values() if obj.is_hovered]
    
    def register_event_callback(self, callback: Callable[[InteractionEvent], None]):
        """Registrar callback para eventos de interacción"""
        self.event_callbacks.append(callback)
    
    def to_dict(self) -> Dict:
        """Serializar estado completo para WebSocket"""
        return {
            'hands': {
                hand: state.to_dict() 
                for hand, state in self.hands.items()
            },
            'objects': {
                obj_id: obj.to_dict() 
                for obj_id, obj in self.objects.items()
            },
            'selected_objects': [obj.id for obj in self.get_selected_objects()],
            'hovered_objects': [obj.id for obj in self.get_hovered_objects()],
            'stats': self.stats,
            'action_mapper': self.action_mapper.to_dict()
        }
    
    def get_interaction_summary(self) -> Dict:
        """Obtener resumen para enviar frecuentemente"""
        return {
            'hands': {
                hand: {
                    'state': state.state.value,
                    'gesture': state.current_gesture,
                    'position': state.position,
                    'position_3d': state.position_3d_world,
                    'selected': state.selected_object_id,
                    'hovered': state.hovered_object_id,
                    'depth': state.depth,
                    'depth_smoothed': state.depth_smoothed,
                    'bbox_area': state.bbox_area,
                    'current_scale': state.current_scale
                }
                for hand, state in self.hands.items()
            },
            'selected_count': len(self.get_selected_objects()),
            'hovered_count': len(self.get_hovered_objects()),
            'objects': [obj.to_dict() for obj in self.objects.values()],
            'demo_mode': self.demo_mode,
            'mirror_enabled': self.mirror_x,
            'depth_zoom_enabled': self.depth_zoom_enabled
        }
    
    def add_demo_objects(self):
        """
        Agregar objetos de demostración para pruebas de interacción.
        Crea figuras geométricas virtuales que se pueden manipular.
        Activa el modo demo para proteger los objetos de ser eliminados.
        """
        # Activar modo demo
        self.demo_mode = True
        
        # Limpiar objetos de demo anteriores
        for obj_id in list(self.demo_object_ids):
            if obj_id in self.objects:
                del self.objects[obj_id]
        self.demo_object_ids.clear()
        
        demo_shapes = [
            {
                'class_name': '🔴 Círculo Rojo',
                'bbox': (80, 80, 100, 100),
                'center': (130, 130),
                'color': '#ef4444'
            },
            {
                'class_name': '🟢 Cuadrado Verde',
                'bbox': (270, 80, 100, 100),
                'center': (320, 130),
                'color': '#22c55e'
            },
            {
                'class_name': '🔵 Triángulo Azul',
                'bbox': (460, 80, 100, 100),
                'center': (510, 130),
                'color': '#3b82f6'
            },
            {
                'class_name': '🟡 Estrella Amarilla',
                'bbox': (80, 280, 100, 100),
                'center': (130, 330),
                'color': '#eab308'
            },
            {
                'class_name': '🟣 Diamante Púrpura',
                'bbox': (270, 280, 100, 100),
                'center': (320, 330),
                'color': '#a855f7'
            },
            {
                'class_name': '🟠 Hexágono Naranja',
                'bbox': (460, 280, 100, 100),
                'center': (510, 330),
                'color': '#f97316'
            },
        ]
        
        for shape in demo_shapes:
            obj_id = self.next_object_id
            self.next_object_id += 1
            
            self.objects[obj_id] = InteractiveObject(
                id=obj_id,
                class_name=shape['class_name'],
                bbox=shape['bbox'],
                center=shape['center'],
                confidence=1.0
            )
            # Marcar como objeto de demo
            self.demo_object_ids.add(obj_id)
        
        logger.info(f"🎮 Modo DEMO 2D activado - {len(demo_shapes)} objetos creados")
        return len(demo_shapes)
    
    def add_demo_objects_3d(self):
        """
        Agregar objetos de demostración 3D para pruebas.
        Los objetos tienen posiciones 3D para el visualizador Three.js.
        """
        # Activar modo demo
        self.demo_mode = True
        
        # Limpiar objetos anteriores
        for obj_id in list(self.demo_object_ids):
            if obj_id in self.objects:
                del self.objects[obj_id]
        self.demo_object_ids.clear()
        
        # Objetos 3D con posiciones en el espacio (4 objetos para mejor control)
        # Vista aérea: X=horizontal, Y=altura, Z=profundidad
        demo_shapes_3d = [
            {
                'class_name': '🔴 Esfera Roja',
                'bbox': (160, 160, 80, 80),
                'center': (200, 200),
                'position_3d': (-0.15, 0.08, -0.1),  # Izquierda-arriba
                'color': '#ef4444',
                'shape_type': 'sphere'
            },
            {
                'class_name': '🟢 Cubo Verde',
                'bbox': (400, 160, 80, 80),
                'center': (440, 200),
                'position_3d': (0.15, 0.08, -0.1),  # Derecha-arriba
                'color': '#22c55e',
                'shape_type': 'cube'
            },
            {
                'class_name': '🔵 Cono Azul',
                'bbox': (160, 320, 80, 80),
                'center': (200, 360),
                'position_3d': (-0.15, 0.08, 0.1),  # Izquierda-abajo
                'color': '#3b82f6',
                'shape_type': 'cone'
            },
            {
                'class_name': '🟡 Torus Amarillo',
                'bbox': (400, 320, 80, 80),
                'center': (440, 360),
                'position_3d': (0.15, 0.08, 0.1),  # Derecha-abajo
                'color': '#eab308',
                'shape_type': 'torus'
            },
        ]
        
        for shape in demo_shapes_3d:
            obj_id = self.next_object_id
            self.next_object_id += 1
            
            obj = InteractiveObject(
                id=obj_id,
                class_name=shape['class_name'],
                bbox=shape['bbox'],
                center=shape['center'],
                confidence=1.0
            )
            # Guardar datos 3D adicionales
            obj.position_3d = shape['position_3d']
            obj.color = shape['color']
            obj.shape_type = shape['shape_type']
            
            self.objects[obj_id] = obj
            self.demo_object_ids.add(obj_id)
        
        logger.info(f"🎮 Modo DEMO 3D activado - {len(demo_shapes_3d)} objetos creados")
        return len(demo_shapes_3d)
    
    def clear_objects(self):
        """Limpiar todos los objetos y desactivar modo demo"""
        self.objects.clear()
        self.demo_object_ids.clear()
        self.demo_mode = False
        for hand_state in self.hands.values():
            hand_state.selected_object_id = None
            hand_state.hovered_object_id = None
            hand_state.state = InteractionState.IDLE
            hand_state.drag_start_position = None
            hand_state.drag_start_object_offset = None
        logger.info("🎮 Modo DEMO desactivado - Objetos limpiados")
    
    def set_frame_size(self, width: int, height: int = 480):
        """Configurar tamaño del frame para el efecto espejo"""
        self.frame_width = width
        self.frame_height = height
        logger.info(f"Frame size: {width}x{height}")
    
    def set_kinect_tilt(self, angle_degrees: float):
        """
        Configurar el ángulo de inclinación del Kinect
        
        Args:
            angle_degrees: Ángulo en grados hacia abajo (positivo = mirando hacia abajo)
                          Por ejemplo: 20 si el Kinect está inclinado 20° hacia abajo
        """
        self.kinect_tilt_angle = float(angle_degrees)
        logger.info(f"📐 Kinect tilt angle: {self.kinect_tilt_angle}°")


if __name__ == "__main__":
    # Demo del motor de interacción
    print("=" * 60)
    print("INTERACTION ENGINE - DEMO")
    print("=" * 60)
    
    # Crear motor
    engine = InteractionEngine()
    
    # Registrar callback de eventos
    def on_event(event: InteractionEvent):
        print(f"📢 Evento: {event.type} | Mano: {event.hand} | Objeto: {event.object_id}")
    
    engine.register_event_callback(on_event)
    
    # Simular detección de objeto
    print("\n--- Añadiendo objeto ---")
    engine.update_objects([{
        'class_name': 'cup',
        'bbox': {'x': 100, 'y': 100, 'width': 80, 'height': 80},
        'center': {'x': 140, 'y': 140},
        'confidence': 0.95
    }])
    
    print(f"Objetos: {list(engine.objects.keys())}")
    
    # Simular mano acercándose
    print("\n--- Mano acercándose al objeto ---")
    engine.process_hand(
        hand="Right",
        position=(140, 140),
        gesture="open_palm",
        confidence=0.9
    )
    
    # Simular hover
    print(f"Estado mano: {engine.hands['Right'].state.value}")
    print(f"Objeto hovereado: {engine.hands['Right'].hovered_object_id}")
    
    # Simular selección (mantener gesto)
    print("\n--- Seleccionando objeto ---")
    import time
    time.sleep(0.4)
    engine.process_hand(
        hand="Right",
        position=(140, 140),
        gesture="open_palm",
        confidence=0.9
    )
    
    # Simular arrastre
    print("\n--- Arrastrando objeto ---")
    for i in range(5):
        engine.process_hand(
            hand="Right",
            position=(140 + i*20, 140),
            gesture="closed_fist",
            confidence=0.9
        )
        time.sleep(0.1)
    
    # Soltar
    print("\n--- Soltando objeto ---")
    engine.process_hand(
        hand="Right",
        position=(220, 140),
        gesture="open_palm",
        confidence=0.9
    )
    
    # Mostrar estado final
    print("\n--- Estado Final ---")
    state = engine.to_dict()
    print(f"Estadísticas: {state['stats']}")
    
    print("\n✅ Demo completado")
