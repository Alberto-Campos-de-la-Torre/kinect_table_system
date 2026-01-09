# Script para configurar Git y preparar el proyecto para GitHub
# Ejecutar: .\setup-git.ps1

Write-Host "=== Configuración de Git para Kinect Table System ===" -ForegroundColor Cyan
Write-Host ""

# Verificar si git está instalado
try {
    $gitVersion = git --version
    Write-Host "✓ Git encontrado: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Error: Git no está instalado. Por favor instálalo primero." -ForegroundColor Red
    exit 1
}

# Verificar si estamos en el directorio correcto
$currentDir = Get-Location
if (-not (Test-Path ".gitignore")) {
    Write-Host "✗ Error: No se encontró .gitignore. Asegúrate de estar en el directorio raíz del proyecto." -ForegroundColor Red
    exit 1
}

Write-Host "✓ Directorio correcto detectado" -ForegroundColor Green
Write-Host ""

# Verificar si ya existe un repositorio git
if (Test-Path ".git") {
    Write-Host "⚠ Ya existe un repositorio Git en este directorio." -ForegroundColor Yellow
    $continue = Read-Host "¿Deseas continuar de todas formas? (s/n)"
    if ($continue -ne "s" -and $continue -ne "S") {
        Write-Host "Operación cancelada." -ForegroundColor Yellow
        exit 0
    }
} else {
    Write-Host "Inicializando repositorio Git..." -ForegroundColor Cyan
    git init
    Write-Host "✓ Repositorio inicializado" -ForegroundColor Green
}

Write-Host ""
Write-Host "Verificando archivos que serán ignorados..." -ForegroundColor Cyan
$ignoredFiles = git status --ignored --short 2>$null
if ($ignoredFiles) {
    Write-Host "✓ Archivos ignorados correctamente por .gitignore" -ForegroundColor Green
} else {
    Write-Host "⚠ No se detectaron archivos ignorados (esto es normal si no hay archivos aún)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Agregando archivos al staging..." -ForegroundColor Cyan
git add .
Write-Host "✓ Archivos agregados" -ForegroundColor Green

Write-Host ""
Write-Host "Estado del repositorio:" -ForegroundColor Cyan
git status --short

Write-Host ""
Write-Host "=== Próximos pasos ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Haz tu primer commit:" -ForegroundColor Yellow
Write-Host "   git commit -m 'Initial commit: Kinect Table System'" -ForegroundColor White
Write-Host ""
Write-Host "2. Crea un repositorio en GitHub (https://github.com/new)" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Conecta tu repositorio local con GitHub:" -ForegroundColor Yellow
Write-Host "   git remote add origin https://github.com/TU_USUARIO/kinect_table_system.git" -ForegroundColor White
Write-Host ""
Write-Host "4. Pushea tu código:" -ForegroundColor Yellow
Write-Host "   git branch -M main" -ForegroundColor White
Write-Host "   git push -u origin main" -ForegroundColor White
Write-Host ""
Write-Host "Para más detalles, consulta: GITHUB_PUSH_COMMANDS.md" -ForegroundColor Cyan
Write-Host ""
