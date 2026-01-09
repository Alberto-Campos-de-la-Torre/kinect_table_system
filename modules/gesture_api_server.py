"""
Servidor de API para Reconocimiento de Gestos
==============================================
Proporciona API WebSocket y REST para integración con Tauri frontend

Endpoints:
- WebSocket: ws://localhost:8765 - Stream de gestos en tiempo real
- REST: http://localhost:8000/gesture - Estado actual
- REST: http://localhost:8000/stats - Estadísticas
"""

import asyncio
import json
import cv2
import numpy as np
from typing import Set, Dict, Any
from datetime import datetime
import websockets
from aiohttp import web
import threading
import time

from modules.gesture_recognition import GestureRecognizer, GestureType


class GestureAPIServer:
    """Servidor de API para reconocimiento de gestos"""
    
    def __init__(self, host: str = "localhost", ws_port: int = 8765, http_port: int = 8000):
        """
        Inicializar servidor
        
        Args:
            host: Host del servidor
            ws_port: Puerto para WebSocket
            http_port: Puerto para HTTP REST
        """
        self.host = host
        self.ws_port = ws_port
        self.http_port = http_port
        
        # Estado compartido
        self.current_gestures = []
        self.stats = {
            "total_frames": 0,
            "total_gestures_detected": 0,
            "gestures_count": {gesture.value: 0 for gesture in GestureType},
            "fps": 0,
            "uptime": 0,
            "start_time": None
        }
        
        # Clientes WebSocket conectados
        self.ws_clients: Set[websockets.WebSocketServerProtocol] = set()
        
        # Reconocedor de gestos
        self.recognizer = GestureRecognizer(max_num_hands=2)
        
        # Cámara
        self.cap = None
        self.running = False
        
        # Lock para thread safety
        self.lock = threading.Lock()
    
    async def websocket_handler(self, websocket, path):
        """Handler para conexiones WebSocket"""
        # Registrar cliente
        self.ws_clients.add(websocket)
        print(f"Cliente WebSocket conectado: {websocket.remote_address}")
        
        try:
            # Enviar mensaje de bienvenida
            await websocket.send(json.dumps({
                "type": "connected",
                "message": "Conectado al servidor de gestos",
                "timestamp": datetime.now().isoformat()
            }))
            
            # Mantener conexión abierta
            async for message in websocket:
                # Procesar comandos del cliente si es necesario
                data = json.loads(message)
                
                if data.get("command") == "get_stats":
                    await websocket.send(json.dumps({
                        "type": "stats",
                        "data": self.get_stats()
                    }))
        
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            # Desregistrar cliente
            self.ws_clients.remove(websocket)
            print(f"Cliente WebSocket desconectado: {websocket.remote_address}")
    
    async def broadcast_gesture_data(self, gestures, frame_data=None):
        """Enviar datos de gestos a todos los clientes conectados"""
        if not self.ws_clients:
            return
        
        # Preparar datos
        gesture_data = []
        for gesture in gestures:
            gesture_data.append({
                "gesture": gesture.gesture.value,
                "confidence": float(gesture.confidence),
                "handedness": gesture.handedness,
                "bounding_box": gesture.bounding_box,
                "landmarks": {
                    "wrist": gesture.hand_landmarks.wrist,
                    "thumb_tip": gesture.hand_landmarks.thumb_tip,
                    "index_tip": gesture.hand_landmarks.index_tip,
                    "middle_tip": gesture.hand_landmarks.middle_tip,
                    "ring_tip": gesture.hand_landmarks.ring_tip,
                    "pinky_tip": gesture.hand_landmarks.pinky_tip
                }
            })
        
        message = {
            "type": "gesture_update",
            "timestamp": datetime.now().isoformat(),
            "gestures": gesture_data,
            "fps": self.stats["fps"]
        }
        
        # Enviar a todos los clientes
        disconnected = set()
        for client in self.ws_clients:
            try:
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
        
        # Limpiar clientes desconectados
        self.ws_clients -= disconnected
    
    async def handle_get_gesture(self, request):
        """Handler REST para obtener gesto actual"""
        with self.lock:
            gestures = self.current_gestures.copy()
        
        gesture_data = []
        for gesture in gestures:
            gesture_data.append({
                "gesture": gesture.gesture.value,
                "confidence": float(gesture.confidence),
                "handedness": gesture.handedness
            })
        
        return web.json_response({
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "gestures": gesture_data
        })
    
    async def handle_get_stats(self, request):
        """Handler REST para obtener estadísticas"""
        return web.json_response({
            "status": "success",
            "data": self.get_stats()
        })
    
    async def handle_cors_preflight(self, request):
        """Handler para CORS preflight"""
        return web.Response(
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas actuales"""
        with self.lock:
            stats = self.stats.copy()
        
        if stats["start_time"]:
            stats["uptime"] = time.time() - stats["start_time"]
        
        return stats
    
    def process_video_stream(self):
        """Procesar stream de video y reconocer gestos"""
        print("Iniciando procesamiento de video...")
        
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Error: No se pudo abrir la cámara")
            return
        
        # Configurar resolución
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        self.stats["start_time"] = time.time()
        prev_time = time.time()
        
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            # Voltear para efecto espejo
            frame = cv2.flip(frame, 1)
            
            # Procesar frame
            annotated_frame, gestures = self.recognizer.process_frame(frame)
            
            # Actualizar estadísticas
            curr_time = time.time()
            fps = 1 / (curr_time - prev_time)
            prev_time = curr_time
            
            with self.lock:
                self.current_gestures = gestures
                self.stats["total_frames"] += 1
                self.stats["fps"] = round(fps, 1)
                
                if gestures:
                    self.stats["total_gestures_detected"] += len(gestures)
                    for gesture in gestures:
                        self.stats["gestures_count"][gesture.gesture.value] += 1
            
            # Broadcast a clientes WebSocket
            if self.ws_clients:
                asyncio.run(self.broadcast_gesture_data(gestures))
            
            # Pequeño delay para no saturar CPU
            time.sleep(0.01)
        
        # Limpiar
        self.cap.release()
        print("Procesamiento de video detenido")
    
    async def start_websocket_server(self):
        """Iniciar servidor WebSocket"""
        print(f"Servidor WebSocket iniciando en ws://{self.host}:{self.ws_port}")
        async with websockets.serve(self.websocket_handler, self.host, self.ws_port):
            await asyncio.Future()  # run forever
    
    def start_http_server(self):
        """Iniciar servidor HTTP REST"""
        app = web.Application()
        
        # Middleware CORS
        @web.middleware
        async def cors_middleware(request, handler):
            if request.method == 'OPTIONS':
                return await self.handle_cors_preflight(request)
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
        
        app.middlewares.append(cors_middleware)
        
        # Rutas
        app.router.add_get('/gesture', self.handle_get_gesture)
        app.router.add_get('/stats', self.handle_get_stats)
        app.router.add_options('/{tail:.*}', self.handle_cors_preflight)
        
        print(f"Servidor HTTP REST iniciando en http://{self.host}:{self.http_port}")
        web.run_app(app, host=self.host, port=self.http_port, print=None)
    
    def start(self):
        """Iniciar servidor completo"""
        print("=" * 60)
        print("SERVIDOR DE API DE GESTOS")
        print("=" * 60)
        print(f"\nWebSocket: ws://{self.host}:{self.ws_port}")
        print(f"HTTP REST: http://{self.host}:{self.http_port}")
        print("\nEndpoints HTTP:")
        print(f"  GET http://{self.host}:{self.http_port}/gesture - Gesto actual")
        print(f"  GET http://{self.host}:{self.http_port}/stats - Estadísticas")
        print("\nPresiona Ctrl+C para detener")
        print("=" * 60)
        print()
        
        self.running = True
        
        # Iniciar procesamiento de video en thread separado
        video_thread = threading.Thread(target=self.process_video_stream, daemon=True)
        video_thread.start()
        
        # Iniciar servidor HTTP en thread separado
        http_thread = threading.Thread(target=self.start_http_server, daemon=True)
        http_thread.start()
        
        # Iniciar servidor WebSocket (bloquea el thread principal)
        try:
            asyncio.run(self.start_websocket_server())
        except KeyboardInterrupt:
            print("\n\nDeteniendo servidor...")
            self.stop()
    
    def stop(self):
        """Detener servidor"""
        self.running = False
        if self.cap:
            self.cap.release()
        self.recognizer.close()
        print("Servidor detenido correctamente")


def main():
    """Función principal"""
    server = GestureAPIServer(
        host="localhost",
        ws_port=8765,
        http_port=8000
    )
    
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
