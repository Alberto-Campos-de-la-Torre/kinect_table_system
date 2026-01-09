# Comandos para Pushear el Proyecto a GitHub

## Pasos para subir el proyecto a GitHub

### 1. Inicializar el repositorio Git (si no está inicializado)

```powershell
# Navegar al directorio del proyecto
cd C:\Users\mayip\Desktop\kinect_table_system

# Inicializar git
git init

# Configurar usuario (si no está configurado globalmente)
git config user.name "Tu Nombre"
git config user.email "tu.email@ejemplo.com"
```

### 2. Agregar todos los archivos al staging

```powershell
# Ver qué archivos se van a agregar (opcional)
git status

# Agregar todos los archivos (respetando .gitignore)
git add .
```

### 3. Hacer el primer commit

```powershell
git commit -m "Initial commit: Kinect Table System con reconocimiento de gestos"
```

### 4. Crear el repositorio en GitHub

1. Ve a [GitHub](https://github.com) e inicia sesión
2. Haz clic en el botón "+" en la esquina superior derecha
3. Selecciona "New repository"
4. Nombre del repositorio: `kinect_table_system` (o el que prefieras)
5. **NO** inicialices con README, .gitignore o licencia (ya los tenemos)
6. Haz clic en "Create repository"

### 5. Conectar el repositorio local con GitHub

```powershell
# Reemplaza 'TU_USUARIO' con tu nombre de usuario de GitHub
# y 'kinect_table_system' con el nombre de tu repositorio si es diferente

git remote add origin https://github.com/TU_USUARIO/kinect_table_system.git

# O si prefieres usar SSH (requiere configuración previa):
# git remote add origin git@github.com:TU_USUARIO/kinect_table_system.git
```

### 6. Verificar la conexión remota

```powershell
git remote -v
```

### 7. Pushear el código a GitHub

```powershell
# Primera vez (establecer upstream)
git branch -M main
git push -u origin main

# En futuras ocasiones, solo necesitas:
# git push
```

## Comandos Adicionales Útiles

### Ver el estado del repositorio
```powershell
git status
```

### Ver qué archivos están siendo ignorados
```powershell
git status --ignored
```

### Ver el historial de commits
```powershell
git log --oneline
```

### Hacer cambios y pushear actualizaciones
```powershell
# Después de hacer cambios
git add .
git commit -m "Descripción de los cambios"
git push
```

### Crear una nueva rama
```powershell
git checkout -b nombre-de-la-rama
git push -u origin nombre-de-la-rama
```

## Notas Importantes

- El archivo `.gitignore` ya está configurado para excluir:
  - Archivos de modelos (`.task`, `.pt`, `.pth`, etc.)
  - Entornos virtuales (`venv/`)
  - Archivos de configuración sensibles (`.env`, `.key`, `.pem`)
  - Archivos de build y compilación
  - Node modules
  - Archivos temporales y logs

- **Nunca subas**:
  - Archivos `.env` con credenciales
  - Claves privadas (`.key`, `.pem`)
  - Modelos grandes (`.task`, `.pt`, etc.)
  - Datos sensibles o personales

- Si accidentalmente agregaste un archivo que debería estar en `.gitignore`:
  ```powershell
  git rm --cached nombre-del-archivo
  git commit -m "Remove archivo sensible del tracking"
  ```
