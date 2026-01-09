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

**Windows:**
1. Descargar [Kinect for Windows SDK 2.0](https://www.microsoft.com/en-us/download/details.aspx?id=44561)
2. Instalar el SDK
3. Conectar el Kinect con adaptador de corriente

**Linux:**
```bash
sudo apt-get update
sudo apt-get install libfreenect-dev freenect
```

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

### "No module named 'pykinect2'"
**Solución:** Instala PyKinect2
```bash
pip install pykinect2
```

### "Kinect not detected"
**Solución:** 
- Verifica que el Kinect esté conectado con adaptador de corriente
- En Windows, verifica que el SDK esté instalado
- Revisa que los drivers estén actualizados

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
