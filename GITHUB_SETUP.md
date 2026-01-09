# 📤 Instrucciones para Publicar en GitHub

## Paso 1: Crear Repositorio en GitHub

1. Ve a https://github.com
2. Haz clic en el botón **"New"** o **"+"** → **"New repository"**
3. Configura el repositorio:
   - **Repository name**: `kinect_table_system`
   - **Description**: Sistema de reconocimiento de objetos y gestos con Kinect Xbox 360
   - **Visibility**: Public (o Private si prefieres)
   - ⚠️ **NO marcar** "Initialize this repository with a README" (ya tenemos uno)
   - ⚠️ **NO agregar** .gitignore ni license (ya los tenemos)
4. Haz clic en **"Create repository"**

## Paso 2: Conectar Repositorio Local con GitHub

GitHub te mostrará instrucciones. Usa estas:

```bash
# Navegar al directorio del proyecto
cd kinect_table_system

# Agregar el remote de GitHub (reemplaza TU-USUARIO con tu usuario de GitHub)
git remote add origin https://github.com/TU-USUARIO/kinect_table_system.git

# Verificar que se agregó correctamente
git remote -v

# Hacer push del código
git push -u origin main
```

## Paso 3: Configurar GitHub (Opcional pero Recomendado)

### Agregar Topics/Tags
En tu repositorio de GitHub:
1. Click en ⚙️ (Settings) junto a "About"
2. Agregar topics: `python`, `kinect`, `computer-vision`, `object-detection`, `gesture-recognition`, `yolo`, `opencv`

### Configurar Protección de Rama
En Settings → Branches:
1. Add rule para `main`
2. Marcar "Require pull request reviews before merging"
3. Marcar "Require status checks to pass before merging"

### Habilitar Issues y Discussions
En Settings → General:
- ✅ Issues
- ✅ Discussions (para Q&A y comunidad)

### Agregar GitHub Actions Secrets (si necesitas)
Si planeas CI/CD con deployment:
Settings → Secrets and variables → Actions

## Paso 4: Personalizar

Antes de hacer público, actualiza estos archivos con tu información:

### README.md
```markdown
- Email: tu-email@ejemplo.com
- GitHub: [@tu-usuario](https://github.com/tu-usuario)
```

### setup.py
```python
author="Tu Nombre",
author_email="tu-email@ejemplo.com",
url="https://github.com/tu-usuario/kinect_table_system",
```

### LICENSE
```
Copyright (c) 2025 [Tu Nombre]
```

Luego hacer commit y push de los cambios:
```bash
git add README.md setup.py LICENSE
git commit -m "Update: Personalize project information"
git push
```

## Paso 5: Agregar Badges (Opcional)

Edita README.md y agrega badges reales después del título:

```markdown
[![CI](https://github.com/TU-USUARIO/kinect_table_system/actions/workflows/ci.yml/badge.svg)](https://github.com/TU-USUARIO/kinect_table_system/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
```

## 📋 Checklist de Publicación

- [ ] Crear repositorio en GitHub
- [ ] Conectar repositorio local
- [ ] Push inicial exitoso
- [ ] Actualizar información personal en archivos
- [ ] Configurar topics/tags
- [ ] Habilitar Issues y Discussions
- [ ] Verificar que GitHub Actions funciona
- [ ] Agregar badges al README
- [ ] Crear primer Release (v0.1.0)

## 🎉 Siguiente Paso: Primer Release

Una vez que todo esté funcionando:

```bash
# Crear tag para primera versión
git tag -a v0.1.0 -m "Initial release - Phase 1 complete"
git push origin v0.1.0
```

Luego en GitHub:
1. Ve a "Releases"
2. Click "Create a new release"
3. Selecciona tag `v0.1.0`
4. Título: "v0.1.0 - Initial Release"
5. Descripción: Características de esta versión
6. Publish release

## 🔐 Notas de Seguridad

- ⚠️ **NUNCA** subas:
  - API keys
  - Contraseñas
  - Tokens de acceso
  - Modelos grandes (>100MB) sin Git LFS
  - Datos personales

- Usa `.gitignore` (ya está configurado)
- Para archivos grandes, considera Git LFS:
  ```bash
  git lfs install
  git lfs track "*.pt"
  git lfs track "*.h5"
  ```

## 📞 Soporte

Si tienes problemas:
1. Verifica que git esté instalado: `git --version`
2. Verifica tu usuario de GitHub: `git config user.name`
3. Si hay error de autenticación, usa Personal Access Token en vez de password

---

¡Tu proyecto está listo para GitHub! 🚀
