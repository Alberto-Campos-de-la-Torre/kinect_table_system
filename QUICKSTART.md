# 🚀 Guía de Inicio Rápido

## Instalación en 5 Pasos

### 1️⃣ Clonar el Repositorio
```bash
git clone https://github.com/tu-usuario/kinect_table_system.git
cd kinect_table_system
```

### 2️⃣ Crear Entorno Virtual
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 4️⃣ Instalar Drivers del Kinect

**Para Kinect Xbox 360 (v1):**

Windows:
1. Descargar [Kinect for Windows SDK 1.8](https://www.microsoft.com/en-us/download/details.aspx?id=40278)
2. Instalar el SDK
3. Instalar biblioteca Python:
```bash
pip install freenect
```

Linux:
```bash
sudo apt-get update
sudo apt-get install libfreenect-dev freenect python3-freenect
pip install freenect
```

**Para Kinect Xbox ONE (v2):**

Windows:
1. Descargar [Kinect for Windows SDK 2.0](https://www.microsoft.com/en-us/download/details.aspx?id=44561)
2. Instalar el SDK
3. Instalar PyKinect2:
```bash
pip install git+https://github.com/Kinect/PyKinect2.git
```

> ⚠️ **IMPORTANTE:** PyKinect2 es SOLO para Kinect Xbox ONE (v2), NO funciona con Kinect Xbox 360

### 5️⃣ Descargar Modelos
```bash
python scripts/download_models.py
```

## ✅ Verificar Instalación

Ejecuta el sistema en modo prueba:
```bash
python main.py --test
```

## 📝 Primeros Pasos

### Ejecutar el Sistema
```bash
python main.py
```

### Calibrar el Kinect
```bash
python main.py --calibrate
```

### Modo Demostración
```bash
python main.py --demo
```

### Sin Kinect Físico (Simulación)
```bash
python main.py --simulation tu_video.mp4
```

## 🎯 Próximos Pasos

1. Lee el [README.md](README.md) completo
2. Revisa la [documentación](docs/)
3. Explora los [ejemplos](examples/)
4. Únete a las [discusiones](https://github.com/tu-usuario/kinect_table_system/discussions)

## ❓ Problemas Comunes

### "No module named 'pykinect2'" o "Wrong version"
**Causa:** Estás usando PyKinect2 (para Kinect v2) pero tienes Kinect Xbox 360 (v1)

**Solución para Kinect Xbox 360 (v1):**
```bash
pip uninstall pykinect2
pip install freenect
```

**Solución para Kinect Xbox ONE (v2):**
```bash
pip install git+https://github.com/Kinect/PyKinect2.git
```

### "Kinect not detected"
**Solución:** 
- Verifica qué Kinect tienes:
  - **Xbox 360**: Sensor rectangular, necesita adaptador de corriente AC
  - **Xbox ONE**: Sensor más grande y redondeado
- Verifica que el SDK correcto esté instalado:
  - Xbox 360 → SDK 1.8
  - Xbox ONE → SDK 2.0
- Revisa que los drivers estén actualizados en Device Manager

### Error de CUDA
**Solución:** Si no tienes GPU NVIDIA, ejecuta:
```bash
python main.py --no-gpu
```

## 📞 Soporte

¿Necesitas ayuda? 
- 📖 [Documentación completa](docs/)
- 🐛 [Reportar un bug](https://github.com/tu-usuario/kinect_table_system/issues)
- 💬 [Discusiones](https://github.com/tu-usuario/kinect_table_system/discussions)

---

¡Listo para comenzar! 🎉
