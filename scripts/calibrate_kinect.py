"""
Kinect Calibration Script
=========================
Script interactivo para calibrar el Kinect
- Calibración intrínseca con tablero de ajedrez
- Calibración de mesa/pantalla
- Validación visual
"""

import sys
from pathlib import Path

# Agregar path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import cv2
import json
import os
import time
from typing import Optional, Tuple

from modules.kinect_capture import KinectCapture
from modules.calibration import (
    IntrinsicCalibrator, CameraIntrinsics,
    CoordinateMapper, CalibrationData,
    TableCalibrator
)
from modules.point_cloud import PointCloudGenerator


class KinectCalibrationApp:
    """
    Aplicación de calibración interactiva del Kinect
    
    Modos:
    - intrinsic: Calibración de parámetros de cámara
    - table: Calibración de mesa/pantalla
    - validate: Validar calibración existente
    - flip: Ajustar orientación de ejes
    """
    
    def __init__(self):
        self.kinect: Optional[KinectCapture] = None
        self.intrinsic_calibrator: Optional[IntrinsicCalibrator] = None
        self.table_calibrator: Optional[TableCalibrator] = None
        self.coordinate_mapper: Optional[CoordinateMapper] = None
        self.pc_generator: Optional[PointCloudGenerator] = None
        
        # Rutas de archivos
        self.data_dir = Path(__file__).parent.parent / "data"
        self.intrinsics_file = self.data_dir / "camera_intrinsics.json"
        self.calibration_file = self.data_dir / "calibration_data.json"
        
        # Estado
        self.mode = "menu"
        self.running = True
        
        # Crear directorio de datos si no existe
        self.data_dir.mkdir(exist_ok=True)
    
    def initialize(self) -> bool:
        """Inicializar módulos"""
        print("\n" + "=" * 60)
        print("KINECT CALIBRATION TOOL")
        print("=" * 60)
        
        # Inicializar Kinect
        print("\nInicializando Kinect...")
        self.kinect = KinectCapture()
        
        if not self.kinect.is_running:
            print("❌ Error: No se pudo inicializar el Kinect")
            return False
        
        print("✅ Kinect inicializado")
        
        # Inicializar calibradores
        self.intrinsic_calibrator = IntrinsicCalibrator()
        self.table_calibrator = TableCalibrator()
        
        # Cargar calibración existente si existe
        self.coordinate_mapper = CoordinateMapper()
        if self.calibration_file.exists():
            self.coordinate_mapper.load_calibration(str(self.calibration_file))
            print("✅ Calibración existente cargada")
        
        # Generador de nube de puntos
        self.pc_generator = PointCloudGenerator()
        
        return True
    
    def show_menu(self):
        """Mostrar menú principal"""
        print("\n" + "-" * 40)
        print("MENÚ DE CALIBRACIÓN")
        print("-" * 40)
        print("1. Calibración intrínseca (tablero de ajedrez)")
        print("2. Calibración de mesa (4 esquinas)")
        print("3. Calibración automática de plano (RANSAC)")
        print("4. Ajustar orientación (flip)")
        print("5. Validar calibración")
        print("6. Ver estado de calibración")
        print("7. Guardar y salir")
        print("0. Salir sin guardar")
        print("-" * 40)
    
    def run(self):
        """Ejecutar aplicación"""
        if not self.initialize():
            return
        
        while self.running:
            self.show_menu()
            
            try:
                choice = input("\nSeleccione opción: ").strip()
                
                if choice == "1":
                    self.run_intrinsic_calibration()
                elif choice == "2":
                    self.run_table_calibration()
                elif choice == "3":
                    self.run_auto_plane_detection()
                elif choice == "4":
                    self.run_flip_adjustment()
                elif choice == "5":
                    self.run_validation()
                elif choice == "6":
                    self.show_calibration_status()
                elif choice == "7":
                    self.save_and_exit()
                elif choice == "0":
                    self.running = False
                else:
                    print("Opción no válida")
                    
            except KeyboardInterrupt:
                print("\n\nInterrumpido por usuario")
                self.running = False
        
        self.cleanup()
    
    def run_intrinsic_calibration(self):
        """Calibración intrínseca con tablero de ajedrez"""
        print("\n" + "=" * 50)
        print("CALIBRACIÓN INTRÍNSECA")
        print("=" * 50)
        print("\nInstrucciones:")
        print("1. Use un tablero de ajedrez 9x6 impreso")
        print("2. Muestre el tablero desde diferentes ángulos")
        print("3. Presione ESPACIO para capturar imagen")
        print("4. Presione 'c' para calibrar cuando tenga 10+ imágenes")
        print("5. Presione 'q' para volver al menú")
        print("\nIniciando captura...")
        
        self.intrinsic_calibrator.reset()
        
        cv2.namedWindow("Calibracion Intrinseca", cv2.WINDOW_NORMAL)
        
        while True:
            frame = self.kinect.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue
            
            rgb = frame.rgb.copy()
            
            # Intentar detectar tablero
            ret, corners = self.intrinsic_calibrator.detect_corners(rgb)
            
            if ret:
                # Dibujar esquinas detectadas
                cv2.drawChessboardCorners(rgb, self.intrinsic_calibrator.board_size, corners, ret)
                cv2.putText(rgb, "TABLERO DETECTADO - Presione ESPACIO para capturar",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(rgb, "Buscando tablero...",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            
            # Mostrar estado
            status = self.intrinsic_calibrator.get_status()
            cv2.putText(rgb, f"Imagenes: {status['images_captured']}/{status['min_images']}",
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            if status['ready_to_calibrate']:
                cv2.putText(rgb, "Presione 'c' para calibrar",
                           (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            cv2.imshow("Calibracion Intrinseca", rgb)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord(' ') and ret:
                # Capturar imagen
                success, _ = self.intrinsic_calibrator.add_image(frame.rgb)
                if success:
                    print(f"✅ Imagen {status['images_captured'] + 1} capturada")
            
            elif key == ord('c') and status['ready_to_calibrate']:
                # Calibrar
                print("\nCalibrando...")
                success, intrinsics = self.intrinsic_calibrator.calibrate()
                
                if success:
                    print(f"✅ Calibración exitosa!")
                    print(f"   Error de reproyección: {intrinsics.reprojection_error:.4f} px")
                    
                    # Guardar
                    intrinsics.save(str(self.intrinsics_file))
                    
                    # Actualizar coordinate mapper
                    self.coordinate_mapper.calibration.intrinsics = intrinsics
                    
                    input("\nPresione Enter para continuar...")
                    break
                else:
                    print("❌ Calibración fallida")
            
            elif key == ord('q'):
                break
        
        cv2.destroyWindow("Calibracion Intrinseca")
    
    def run_table_calibration(self):
        """Calibración de mesa con 4 esquinas"""
        print("\n" + "=" * 50)
        print("CALIBRACIÓN DE MESA")
        print("=" * 50)
        print("\nInstrucciones:")
        print("1. Coloque un objeto (mano, marcador) en cada esquina indicada")
        print("2. Presione ESPACIO cuando el objeto esté en posición")
        print("3. Repita para las 4 esquinas")
        print("4. Presione 'q' para cancelar")
        
        self.table_calibrator.reset()
        
        cv2.namedWindow("Calibracion Mesa", cv2.WINDOW_NORMAL)
        
        while True:
            frame = self.kinect.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue
            
            rgb = frame.rgb.copy()
            depth = frame.depth
            
            # Obtener esquina actual
            corner_name, corner_pos = self.table_calibrator.get_current_marker_position()
            
            if corner_name is None:
                cv2.putText(rgb, "Calibracion completada!",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
                # Escalar posición del marcador a la imagen
                scale_x = rgb.shape[1] / self.table_calibrator.screen_size[0]
                scale_y = rgb.shape[0] / self.table_calibrator.screen_size[1]
                
                marker_x = int(corner_pos[0] * scale_x)
                marker_y = int(corner_pos[1] * scale_y)
                
                # Dibujar marcador
                cv2.circle(rgb, (marker_x, marker_y), 20, (0, 255, 255), 3)
                cv2.line(rgb, (marker_x - 30, marker_y), (marker_x + 30, marker_y), (0, 255, 255), 2)
                cv2.line(rgb, (marker_x, marker_y - 30), (marker_x, marker_y + 30), (0, 255, 255), 2)
                
                cv2.putText(rgb, f"Coloque objeto en: {corner_name.upper()}",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                cv2.putText(rgb, "Presione ESPACIO cuando este listo",
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Mostrar estado
            status = self.table_calibrator.get_status()
            cv2.putText(rgb, f"Paso {status['calibration_step'] + 1}/4",
                       (rgb.shape[1] - 150, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow("Calibracion Mesa", rgb)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord(' ') and corner_name is not None:
                # Detectar punto 3D en el centro de la imagen (simplificado)
                # En producción, se detectaría el objeto/mano
                center_x, center_y = rgb.shape[1] // 2, rgb.shape[0] // 2
                
                # Obtener profundidad del centro
                depth_value = depth[center_y, center_x]
                
                if depth_value > 0:
                    # Convertir a 3D
                    depth_m = 0.1236 * np.tan(depth_value / 2842.5 + 1.1863)
                    
                    intrinsics = self.coordinate_mapper.calibration.intrinsics
                    x = (center_x - intrinsics.cx) * depth_m / intrinsics.fx
                    y = (center_y - intrinsics.cy) * depth_m / intrinsics.fy
                    z = depth_m
                    
                    point_3d = np.array([x, y, z])
                    
                    completed, msg = self.table_calibrator.advance_calibration_step(point_3d)
                    print(f"  {msg}")
                    
                    if completed:
                        # Actualizar calibración
                        cal_data = self.table_calibrator.get_calibration_data()
                        if cal_data:
                            self.coordinate_mapper.calibration.table_plane = np.array(cal_data['table_plane'])
                            self.coordinate_mapper.calibration.table_height = cal_data['table_height']
                        
                        input("\nPresione Enter para continuar...")
                        break
                else:
                    print("  ⚠️ No se pudo detectar profundidad. Intente de nuevo.")
            
            elif key == ord('q'):
                break
        
        cv2.destroyWindow("Calibracion Mesa")
    
    def run_auto_plane_detection(self):
        """Detección automática del plano de mesa con RANSAC"""
        print("\n" + "=" * 50)
        print("DETECCIÓN AUTOMÁTICA DE PLANO")
        print("=" * 50)
        print("\nCapturando nube de puntos...")
        
        # Capturar frames y generar nube de puntos
        frame = self.kinect.get_frame()
        if frame is None:
            print("❌ No se pudo capturar frame")
            return
        
        # Generar nube de puntos
        pc = self.pc_generator.depth_to_pointcloud(frame.depth, downsample=2)
        
        if pc.num_points < 1000:
            print(f"❌ Muy pocos puntos: {pc.num_points}")
            return
        
        print(f"✅ {pc.num_points} puntos generados")
        print("\nBuscando plano de mesa...")
        
        # Detectar plano
        success, plane = self.table_calibrator.detect_table_plane_ransac(pc.points)
        
        if success:
            print(f"✅ Plano detectado!")
            print(f"   Normal: [{plane[0]:.3f}, {plane[1]:.3f}, {plane[2]:.3f}]")
            print(f"   Altura: {self.table_calibrator.table_height:.3f}m")
            
            # Actualizar calibración
            self.coordinate_mapper.calibration.table_plane = plane
            self.coordinate_mapper.calibration.table_height = self.table_calibrator.table_height
        else:
            print("❌ No se pudo detectar plano de mesa")
        
        input("\nPresione Enter para continuar...")
    
    def run_flip_adjustment(self):
        """Ajustar orientación de ejes"""
        print("\n" + "=" * 50)
        print("AJUSTE DE ORIENTACIÓN")
        print("=" * 50)
        
        current = self.coordinate_mapper.calibration
        print(f"\nConfiguración actual:")
        print(f"  Flip X: {current.flip_x}")
        print(f"  Flip Y: {current.flip_y}")
        print(f"  Flip Z: {current.flip_z}")
        
        print("\nOpciones:")
        print("  x - Invertir eje X")
        print("  y - Invertir eje Y")
        print("  z - Invertir eje Z")
        print("  q - Volver al menú")
        
        cv2.namedWindow("Vista Previa", cv2.WINDOW_NORMAL)
        
        while True:
            frame = self.kinect.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue
            
            rgb = frame.rgb.copy()
            
            # Mostrar configuración actual
            cv2.putText(rgb, f"Flip X: {current.flip_x}  Y: {current.flip_y}  Z: {current.flip_z}",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(rgb, "Presione x/y/z para invertir, q para salir",
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
            cv2.imshow("Vista Previa", rgb)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('x'):
                current.flip_x = not current.flip_x
                print(f"  Flip X: {current.flip_x}")
            elif key == ord('y'):
                current.flip_y = not current.flip_y
                print(f"  Flip Y: {current.flip_y}")
            elif key == ord('z'):
                current.flip_z = not current.flip_z
                print(f"  Flip Z: {current.flip_z}")
            elif key == ord('q'):
                break
        
        cv2.destroyWindow("Vista Previa")
    
    def run_validation(self):
        """Validar calibración actual"""
        print("\n" + "=" * 50)
        print("VALIDACIÓN DE CALIBRACIÓN")
        print("=" * 50)
        print("\nMueva su mano frente al Kinect para validar...")
        print("Presione 'q' para salir")
        
        cv2.namedWindow("Validacion", cv2.WINDOW_NORMAL)
        
        while True:
            frame = self.kinect.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue
            
            rgb = frame.rgb.copy()
            
            # Mostrar información de calibración
            status = self.coordinate_mapper.get_calibration_status()
            y = 30
            for key, value in status.items():
                cv2.putText(rgb, f"{key}: {value}",
                           (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                y += 25
            
            cv2.imshow("Validacion", rgb)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cv2.destroyWindow("Validacion")
    
    def show_calibration_status(self):
        """Mostrar estado de calibración"""
        print("\n" + "=" * 50)
        print("ESTADO DE CALIBRACIÓN")
        print("=" * 50)
        
        status = self.coordinate_mapper.get_calibration_status()
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        if self.coordinate_mapper.calibration.intrinsics:
            intr = self.coordinate_mapper.calibration.intrinsics
            print(f"\nParámetros intrínsecos:")
            print(f"  fx={intr.fx:.2f}, fy={intr.fy:.2f}")
            print(f"  cx={intr.cx:.2f}, cy={intr.cy:.2f}")
        
        if self.table_calibrator.is_calibrated:
            print(f"\nMesa:")
            print(f"  Altura: {self.table_calibrator.table_height:.3f}m")
        
        input("\nPresione Enter para continuar...")
    
    def save_and_exit(self):
        """Guardar calibración y salir"""
        print("\nGuardando calibración...")
        
        # Guardar datos de calibración
        from datetime import datetime
        self.coordinate_mapper.calibration.calibration_date = datetime.now().isoformat()
        self.coordinate_mapper.save_calibration(str(self.calibration_file))
        
        print(f"✅ Calibración guardada en: {self.calibration_file}")
        
        self.running = False
    
    def cleanup(self):
        """Limpiar recursos"""
        print("\nCerrando...")
        cv2.destroyAllWindows()
        
        if self.kinect:
            self.kinect.release()
        
        print("✅ Recursos liberados")


def main():
    app = KinectCalibrationApp()
    app.run()


if __name__ == "__main__":
    main()
