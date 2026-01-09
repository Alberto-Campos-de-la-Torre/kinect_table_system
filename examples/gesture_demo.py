#!/usr/bin/env python3
"""
Script de Ejemplo - Reconocimiento de Gestos Standalone
========================================================
Demo completo del sistema de reconocimiento de gestos sin necesidad de Tauri

Uso:
    python examples/gesture_demo.py
"""

import sys
from pathlib import Path

# Agregar módulos al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.gesture_recognition import main

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("DEMO STANDALONE - RECONOCIMIENTO DE GESTOS")
    print("=" * 60)
    print("\nEste es un demo standalone que no requiere Tauri.")
    print("Para la versión completa con UI moderna, ver tauri-app/")
    print("\nControles:")
    print("  - 'q': Salir")
    print("  - 'ESC': Salir")
    print("\n" + "=" * 60 + "\n")
    
    main()
