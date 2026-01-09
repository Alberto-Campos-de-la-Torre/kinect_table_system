"""
Test Standalone - Hand Tracking Module
=======================================
Prueba rápida del módulo de tracking sin necesidad de Tauri
"""

import sys
from pathlib import Path

# Agregar el directorio padre al path para importar hand_tracking
sys.path.insert(0, str(Path(__file__).parent.parent))

from hand_tracking import HandTracker, HandGesture
import cv2
import time

def main():
    print("=" * 70)
    print("TEST STANDALONE - HAND TRACKING MODULE")
    print("=" * 70)
    print()
    print("Controles:")
    print("  'q' - Salir")
    print("  's' - Capturar screenshot")
    print("  'h' - Ocultar/mostrar ayuda")
    print()
    print("Iniciando...")
    print("=" * 70)
    print()
    
    # Inicializar tracker
    tracker = HandTracker(
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5
    )
    
    # Inicializar cámara
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: No se pudo abrir la cámara")
        print("Verifica que:")
        print("  1. Tu cámara esté conectada")
        print("  2. No esté siendo usada por otra aplicación")
        print("  3. Tengas permisos para acceder a la cámara")
        return 1
    
    # Configurar resolución
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    print("✅ Cámara inicializada correctamente")
    print(f"📹 Resolución: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
    print()
    
    show_help = True
    screenshot_count = 0
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ Warning: No se pudo leer el frame")
                continue
            
            # Procesar frame
            annotated_frame, hands_data = tracker.process_frame(frame)
            
            # Mostrar información en consola cada 30 frames
            frame_count += 1
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                avg_fps = frame_count / elapsed
                
                print(f"\r📊 FPS: {tracker.fps:.1f} | Avg: {avg_fps:.1f} | Manos: {len(hands_data)}", end="")
                
                if hands_data:
                    gestures = [f"{h.handedness[0]}:{tracker.get_gesture_name(h.gesture)}" 
                               for h in hands_data]
                    print(f" | Gestos: {', '.join(gestures)}", end="")
            
            # Dibujar ayuda en el frame
            if show_help:
                help_text = [
                    "Controles:",
                    "Q - Salir",
                    "S - Screenshot",
                    "H - Ocultar ayuda"
                ]
                y = 30
                for text in help_text:
                    cv2.putText(
                        annotated_frame, text, (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2
                    )
                    y += 25
            
            # Mostrar contador de manos
            cv2.putText(
                annotated_frame,
                f"Manos: {len(hands_data)}",
                (annotated_frame.shape[1] - 150, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )
            
            # Mostrar frame
            cv2.imshow('Hand Tracking Test - Presiona Q para salir', annotated_frame)
            
            # Manejar teclas
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                print("\n\n👋 Saliendo...")
                break
            elif key == ord('s'):
                screenshot_count += 1
                filename = f"hand_tracking_screenshot_{screenshot_count}.jpg"
                cv2.imwrite(filename, annotated_frame)
                print(f"\n📸 Screenshot guardado: {filename}")
            elif key == ord('h'):
                show_help = not show_help
                print(f"\n{'📖' if show_help else '📕'} Ayuda {'mostrada' if show_help else 'ocultada'}")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupción detectada")
    
    finally:
        # Cleanup
        print("\n")
        print("=" * 70)
        print("Estadísticas finales:")
        print(f"  Frames procesados: {frame_count}")
        print(f"  Tiempo total: {time.time() - start_time:.2f}s")
        print(f"  FPS promedio: {frame_count / (time.time() - start_time):.2f}")
        print(f"  Screenshots: {screenshot_count}")
        print("=" * 70)
        
        tracker.release()
        cap.release()
        cv2.destroyAllWindows()
        
        print("\n✅ Recursos liberados correctamente")
        print("👋 ¡Hasta luego!\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
