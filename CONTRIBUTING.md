# Guía de Contribución

¡Gracias por tu interés en contribuir al Kinect Table System! 🎉

## Cómo Contribuir

### Reportar Bugs

Si encuentras un bug, por favor abre un issue con:
- Descripción clara del problema
- Pasos para reproducirlo
- Comportamiento esperado vs. comportamiento actual
- Screenshots (si aplica)
- Tu configuración (OS, versión de Python, hardware)

### Sugerir Mejoras

Las sugerencias son bienvenidas. Abre un issue con:
- Descripción clara de la mejora
- Justificación (por qué sería útil)
- Ejemplos de uso
- Posible implementación (si tienes ideas)

### Pull Requests

1. **Fork** el repositorio
2. **Crea una rama** para tu feature:
   ```bash
   git checkout -b feature/nombre-descriptivo
   ```
3. **Realiza tus cambios** siguiendo las guías de estilo
4. **Escribe tests** para tu código
5. **Asegúrate** de que todos los tests pasen:
   ```bash
   pytest
   ```
6. **Commit** tus cambios:
   ```bash
   git commit -m "Add: descripción clara del cambio"
   ```
7. **Push** a tu fork:
   ```bash
   git push origin feature/nombre-descriptivo
   ```
8. **Abre un Pull Request** con descripción detallada

## Guías de Estilo

### Python

- Seguir **PEP 8**
- Usar **type hints** donde sea posible
- Docstrings en formato **Google Style**
- Nombres descriptivos para variables y funciones

Ejemplo:
```python
def detect_objects(image: np.ndarray, confidence: float = 0.5) -> List[Detection]:
    """
    Detecta objetos en una imagen.
    
    Args:
        image: Imagen en formato numpy array (RGB)
        confidence: Umbral de confianza para detecciones
    
    Returns:
        Lista de objetos detectados
    
    Raises:
        ValueError: Si la imagen no tiene el formato correcto
    """
    pass
```

### Commits

Usar prefijos claros:
- `Add:` Nueva funcionalidad
- `Fix:` Corrección de bugs
- `Update:` Actualización de funcionalidad existente
- `Refactor:` Refactorización de código
- `Docs:` Cambios en documentación
- `Test:` Agregar o modificar tests
- `Style:` Cambios de formato (no afectan funcionalidad)

### Documentación

- Actualizar README.md si cambias funcionalidad visible al usuario
- Documentar funciones y clases complejas
- Agregar ejemplos de uso cuando sea relevante
- Actualizar CHANGELOG.md

## Tests

- Escribir tests unitarios para nuevas funcionalidades
- Asegurar cobertura > 80%
- Usar pytest para escribir tests
- Colocar tests en el directorio `tests/`

Ejemplo:
```python
def test_object_detection():
    detector = ObjectDetector()
    image = np.zeros((640, 480, 3), dtype=np.uint8)
    detections = detector.detect(image)
    assert isinstance(detections, list)
```

## Proceso de Review

1. Un maintainer revisará tu PR
2. Se pueden solicitar cambios
3. Una vez aprobado, se hará merge a main
4. Tu contribución aparecerá en el siguiente release

## Código de Conducta

- Ser respetuoso y constructivo
- Aceptar críticas constructivas
- Enfocarse en lo mejor para el proyecto
- Mostrar empatía hacia otros colaboradores

## Preguntas

Si tienes preguntas, puedes:
- Abrir un issue con la etiqueta `question`
- Contactar a los maintainers
- Consultar la documentación en `docs/`

---

¡Gracias por contribuir! 🚀
