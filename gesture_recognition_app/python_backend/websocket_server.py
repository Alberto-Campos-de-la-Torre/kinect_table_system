"""
WebSocket Server para Hand Tracking
====================================
Servidor que transmite datos de tracking de manos a la aplicación Tauri.

Cambios de calibración:
- Incluye frame_width/frame_height en cada frame para que el frontend
  use las dimensiones reales de captura en lugar de 640×480 hardcodeado.
- Expone index_tip (landmark 8, punta del índice) para puntero preciso.
- Expone screen_pos cuando hay calibración de homografía activa.
- Maneja todos los mensajes de calibración del CalibrationPanel.
"""

import asyncio
import websockets
import json
import cv2
import base64
import numpy as np
from typing import Set, Optional
import logging
import sys
from pathlib import Path

# Configurar logging primero
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Intentar importar TurboJPEG, si no está disponible usar OpenCV como fallback
try:
    from turbojpeg import TurboJPEG
    TURBOJPEG_AVAILABLE = True
except (ImportError, RuntimeError) as e:
    TURBOJPEG_AVAILABLE = False
    logger.warning(f"TurboJPEG no disponible: {e}. Usando OpenCV como fallback.")

# Agregar el directorio padre al path para importar hand_tracking
sys.path.insert(0, str(Path(__file__).parent.parent))

from hand_tracking import HandTracker, HandGesture

# Import calibration – works whether run as script or as module
try:
    from python_backend.calibration import ScreenCalibrator
except ImportError:
    from calibration import ScreenCalibrator


class HandTrackingServer:
    """Servidor WebSocket para streaming de hand tracking"""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.tracker = HandTracker(max_num_hands=2)
        self.cap = None
        self.running = False

        # Dimensiones reales del frame capturado (se actualizan al abrir cámara)
        self.frame_width: int = 640
        self.frame_height: int = 480

        # Calibración de homografía pantalla.
        # El calibrador emite coordenadas NORMALIZADAS (0-1) independientes de resolución.
        self.calibrator = ScreenCalibrator()
        self.calibration_active: bool = False   # True mientras capturamos esquinas

        # Volteo de video
        self.flip_h: bool = False
        self.flip_v: bool = False

        # Ángulo de inclinación Kinect (almacenado; Kinect v2 no tiene motor)
        self.kinect_tilt: float = 0.0

        # Inicializar encoder JPEG
        self.use_turbojpeg = False
        self.jpeg_encoder: Optional[TurboJPEG] = None

        if TURBOJPEG_AVAILABLE:
            try:
                self.jpeg_encoder = TurboJPEG()
                self.use_turbojpeg = True
                logger.info("Usando TurboJPEG para codificación de frames")
            except RuntimeError as e:
                logger.warning(f"No se pudo inicializar TurboJPEG: {e}. Usando OpenCV.")
        else:
            logger.info("Usando OpenCV para codificación de frames")

    # ------------------------------------------------------------------
    # Client management
    # ------------------------------------------------------------------

    async def register_client(self, websocket):
        self.clients.add(websocket)
        logger.info(f"Cliente conectado. Total: {len(self.clients)}")

    async def unregister_client(self, websocket):
        self.clients.discard(websocket)
        logger.info(f"Cliente desconectado. Total: {len(self.clients)}")

    # ------------------------------------------------------------------
    # Encoding
    # ------------------------------------------------------------------

    def _encode_frame(self, frame: np.ndarray, quality: int = 75) -> str:
        """Codificar frame a base64 JPEG (con TurboJPEG si está disponible)."""
        if frame.shape[1] > 960:
            scale = 960 / frame.shape[1]
            new_size = (960, int(frame.shape[0] * scale))
            frame = cv2.resize(frame, new_size, interpolation=cv2.INTER_LINEAR)

        if self.use_turbojpeg and self.jpeg_encoder is not None:
            try:
                jpg_bytes = self.jpeg_encoder.encode(frame, quality=quality)
                return base64.b64encode(jpg_bytes).decode("utf-8")
            except Exception as e:
                logger.warning(f"Error con TurboJPEG, usando OpenCV: {e}")
                self.use_turbojpeg = False

        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return base64.b64encode(buffer).decode("utf-8")

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def _serialize_hand_data(self, hands_data: list) -> list:
        """
        Serializar datos de manos a JSON.

        Cada mano incluye:
          center      – promedio de los 21 landmarks (pixel space)
          index_tip   – punta del índice suavizada (pixel space, mejor para puntero)
          screen_pos  – posición en pantalla si hay calibración activa
          frame_w/h   – dimensiones reales del frame (para escalar en el frontend)
        """
        serialized = []
        for hand in hands_data:
            tip_x, tip_y = hand.index_tip

            # Aplicar homografía si está calibrado.
            # Resultado: coordenadas NORMALIZADAS (0.0-1.0), resolución-independientes.
            # El frontend las multiplica directamente por 100 para obtener porcentajes CSS.
            if self.calibrator.is_calibrated:
                nx, ny = self.calibrator.apply(tip_x, tip_y)
                screen_pos = {"x": nx, "y": ny} if nx is not None else None
            else:
                screen_pos = None

            serialized.append({
                "handedness": hand.handedness,
                "gesture": hand.gesture.value,
                "gesture_name": self.tracker.get_gesture_name(hand.gesture),
                "confidence": float(hand.confidence),
                "bbox": {
                    "x": int(hand.bbox[0]),
                    "y": int(hand.bbox[1]),
                    "width": int(hand.bbox[2]),
                    "height": int(hand.bbox[3]),
                },
                "center": {
                    "x": float(hand.center[0]),
                    "y": float(hand.center[1]),
                },
                # Punta del índice (landmark 8) – más precisa para señalar
                "index_tip": {
                    "x": float(tip_x),
                    "y": float(tip_y),
                },
                # Posición en pantalla calibrada (None si no calibrado)
                "screen_pos": screen_pos,
                # Dimensiones del frame para que el frontend pueda escalar
                "frame_w": self.frame_width,
                "frame_h": self.frame_height,
                "landmarks": [
                    {"x": float(lm.x), "y": float(lm.y), "z": float(lm.z)}
                    for lm in hand.landmarks
                ],
            })
        return serialized

    # ------------------------------------------------------------------
    # Main capture loop
    # ------------------------------------------------------------------

    async def send_frame_data(self):
        """Capturar y enviar frames a todos los clientes."""
        while self.running:
            if not self.cap or not self.cap.isOpened():
                await asyncio.sleep(0.1)
                continue

            ret, frame = self.cap.read()
            if not ret:
                logger.warning("No se pudo leer frame de la cámara")
                await asyncio.sleep(0.1)
                continue

            # Aplicar volteos de video si están activos
            if self.flip_h and self.flip_v:
                frame = cv2.flip(frame, -1)
            elif self.flip_h:
                frame = cv2.flip(frame, 1)
            elif self.flip_v:
                frame = cv2.flip(frame, 0)

            # Procesar con MediaPipe
            annotated_frame, hands_data = self.tracker.process_frame(frame)

            # Codificar frame
            encoded_frame = self._encode_frame(annotated_frame, quality=75)

            # Serializar manos
            hands_json = self._serialize_hand_data(hands_data)

            # Preparar mensaje – incluir dimensiones reales del frame
            message = json.dumps({
                "type": "frame",
                "timestamp": asyncio.get_event_loop().time(),
                "fps": float(self.tracker.fps),
                "frame": encoded_frame,
                "frame_width": self.frame_width,
                "frame_height": self.frame_height,
                "hands": hands_json,
                "calibrated": self.calibrator.is_calibrated,
            })

            if self.clients:
                await asyncio.gather(
                    *[client.send(message) for client in self.clients],
                    return_exceptions=True,
                )

            await asyncio.sleep(0.033)  # ~30 FPS

    # ------------------------------------------------------------------
    # WebSocket handlers
    # ------------------------------------------------------------------

    async def handle_client(self, websocket, path: str = None):
        await self.register_client(websocket)
        try:
            await websocket.send(json.dumps({
                "type": "welcome",
                "message": "Conectado al servidor de hand tracking",
                "calibration": self.calibrator.status(),
            }))

            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(websocket, data)
                except json.JSONDecodeError:
                    logger.error(f"Mensaje inválido: {message}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("Conexión cerrada por el cliente")
        finally:
            await self.unregister_client(websocket)

    async def handle_message(self, websocket, data: dict):
        """Despachar mensajes recibidos del cliente."""
        msg_type = data.get("type")

        # ---- Camera control ----------------------------------------
        if msg_type == "start_camera":
            await self.start_camera(data.get("camera_id", 0))
            await websocket.send(json.dumps({
                "type": "camera_started",
                "success": self.cap is not None and self.cap.isOpened(),
                "frame_width": self.frame_width,
                "frame_height": self.frame_height,
            }))

        elif msg_type == "stop_camera":
            await self.stop_camera()
            await websocket.send(json.dumps({"type": "camera_stopped", "success": True}))

        elif msg_type == "ping":
            await websocket.send(json.dumps({
                "type": "pong",
                "timestamp": asyncio.get_event_loop().time(),
            }))

        # ---- Calibration status ------------------------------------
        elif msg_type == "calibration_get_status":
            await websocket.send(json.dumps({
                "type": "calibration_status",
                "calibration": {
                    **self.calibrator.status(),
                    "has_table_plane": self.calibrator.is_calibrated,
                    "has_intrinsics": True,
                    "flip": {"x": self.flip_h, "y": self.flip_v, "z": False},
                },
            }))

        # ---- Calibration: start corner capture ---------------------
        elif msg_type == "calibration_start":
            self.calibrator.start()
            self.calibration_active = True
            await self._broadcast({
                "type": "calibration_started",
                "status": {
                    "calibration_step": 0,
                    "corners_captured": 0,
                },
            })

        # ---- Calibration: capture one corner -----------------------
        elif msg_type == "calibration_capture":
            if not self.calibration_active:
                await websocket.send(json.dumps({
                    "type": "calibration_error",
                    "error": "Calibración no iniciada. Envía calibration_start primero.",
                }))
                return

            raw_x = float(data.get("x", 0))
            raw_y = float(data.get("y", 0))

            # The frontend maps canvas clicks → 640×480 coords.
            # Scale to actual frame resolution so homography is correct.
            img_x = raw_x * (self.frame_width / 640.0)
            img_y = raw_y * (self.frame_height / 480.0)

            count = self.calibrator.add_corner(img_x, img_y)
            completed = False
            error_msg = None

            if count >= 4:
                success, msg = self.calibrator.compute_homography()
                if success:
                    self.calibration_active = False
                    completed = True
                    logger.info("Calibración de pantalla completada")
                else:
                    error_msg = msg

            if error_msg:
                await self._broadcast({
                    "type": "calibration_error",
                    "error": error_msg,
                })
                return

            await self._broadcast({
                "type": "calibration_point_captured",
                # point_3d compat: send [img_x, img_y, 0] so panel can display coords
                "point_3d": [img_x, img_y, 0.0],
                "status": {
                    "calibration_step": min(count, 4),
                    "corners_captured": count,
                },
                "completed": completed,
            })

        # ---- Calibration: cancel -----------------------------------
        elif msg_type == "calibration_cancel":
            self.calibration_active = False
            self.calibrator.src_pts = []
            await self._broadcast({"type": "calibration_cancelled"})

        # ---- Calibration: reset ------------------------------------
        elif msg_type == "calibration_reset":
            self.calibration_active = False
            self.calibrator.reset()
            await self._broadcast({"type": "calibration_reset_complete"})

        # ---- Calibration: flip -------------------------------------
        elif msg_type == "calibration_set_flip":
            if "flip_x" in data:
                self.flip_h = bool(data["flip_x"])
            if "flip_y" in data:
                self.flip_v = bool(data["flip_y"])
            flip_state = {"x": self.flip_h, "y": self.flip_v, "z": False}
            await self._broadcast({
                "type": "calibration_flip_updated",
                "flip": flip_state,
            })

        # ---- Video flip --------------------------------------------
        elif msg_type == "set_video_flip":
            self.flip_h = bool(data.get("flip_h", self.flip_h))
            self.flip_v = bool(data.get("flip_v", self.flip_v))
            await self._broadcast({
                "type": "video_flip_updated",
                "flip_h": self.flip_h,
                "flip_v": self.flip_v,
            })

        # ---- Screen size notification from frontend ----------------
        # Frontend sends this on connect and on window resize.
        # We store it in the calibrator for informational/logging use.
        elif msg_type == "set_screen_size":
            w = int(data.get("width", 1920))
            h = int(data.get("height", 1080))
            self.calibrator.screen_width = w
            self.calibrator.screen_height = h
            logger.info("Frontend screen size: %dx%d", w, h)

        # ---- Kinect tilt (stored only; Kinect v2 has no motor) ----
        elif msg_type == "set_kinect_tilt":
            self.kinect_tilt = float(data.get("angle", 0.0))
            await websocket.send(json.dumps({
                "type": "kinect_tilt_updated",
                "angle": self.kinect_tilt,
            }))

        # ---- Auto plane detection (stub) ---------------------------
        elif msg_type == "calibration_auto_plane":
            await websocket.send(json.dumps({
                "type": "calibration_error",
                "error": "Detección automática no disponible con cámara RGB. Use calibración manual de 4 esquinas.",
            }))

    async def _broadcast(self, payload: dict):
        """Enviar un mensaje JSON a todos los clientes conectados."""
        message = json.dumps(payload)
        if self.clients:
            await asyncio.gather(
                *[c.send(message) for c in self.clients],
                return_exceptions=True,
            )

    # ------------------------------------------------------------------
    # Camera lifecycle
    # ------------------------------------------------------------------

    async def start_camera(self, camera_id: int = 0):
        if self.cap is None or not self.cap.isOpened():
            logger.info(f"Iniciando cámara {camera_id}...")
            self.cap = cv2.VideoCapture(camera_id)

            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

                # Read back actual delivered dimensions
                self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                logger.info(
                    f"Cámara iniciada: {self.frame_width}×{self.frame_height}"
                )
            else:
                logger.error("No se pudo abrir la cámara")
                self.cap = None

    async def stop_camera(self):
        if self.cap:
            logger.info("Deteniendo cámara...")
            self.cap.release()
            self.cap = None

    async def start_server(self):
        self.running = True
        logger.info(f"Iniciando servidor en ws://{self.host}:{self.port}")

        await self.start_camera(0)

        async def handler(websocket, *args):
            path = args[0] if args else None
            await self.handle_client(websocket, path)

        async with websockets.serve(handler, self.host, self.port):
            await self.send_frame_data()

    async def stop_server(self):
        logger.info("Deteniendo servidor...")
        self.running = False
        await self.stop_camera()
        self.tracker.release()
        logger.info("Servidor detenido")


async def main():
    server = HandTrackingServer(host="localhost", port=8765)
    try:
        await server.start_server()
    except KeyboardInterrupt:
        logger.info("Interrupción detectada")
    finally:
        await server.stop_server()


if __name__ == "__main__":
    print("=" * 60)
    print("HAND TRACKING WEBSOCKET SERVER")
    print("=" * 60)
    print(f"Servidor: ws://localhost:8765")
    print("Presiona Ctrl+C para detener")
    print("=" * 60)
    print()
    asyncio.run(main())
