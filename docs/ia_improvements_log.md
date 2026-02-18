# Mejoras en el Contador Oriental (IA) - 18/02/2026

## Problema Detectado
El modelo `gemma2:2b` no respondía correctamente sobre los gastos de "Almacén" cuando:
1. El usuario tenía errores tipográficos (ej: "alamcen").
2. El usuario usaba palabras que contenían substrings de otras categorías (ej: "gastos" activaba la categoría "Hogar" por contener "gas").
3. El filtro limitaba arbitrariamente a 10 gastos en consultas generales.

## Solución Técnica Implementada

### 1. Lógica de Filtrado Inteligente (`ai_controller.py`)
Se mejoró el método `_detectar_categorias_relevantes`:
- **Tokenización:** Se usa `re.findall(r'\w+', ...)` para analizar palabras completas. Esto evita falsos positivos (ej: "gastos" ya no machea con "gas").
- **Fuzzy Matching:** Se implementó `difflib.get_close_matches` con un cutoff de 0.8.
  - Resultado: "alamcen" -> Detecta "almacen" -> Asocia categoría "🛒 Almacén".

### 2. Eliminación de Límites Arbitrarios
- Se eliminó la restricción de `gastos[-10:]` en consultas generales.
- Ahora, si no se detecta categoría, se envían **todos** los gastos del mes actual al contexto del modelo.

### 3. Corrección de Scope (`ai_advisor_service.py`)
- Se solucionó un `UnboundLocalError` moviendo la importación e inicialización del `logger` dentro del método `consultar` y renombrándolo a `ai_logger` para evitar conflictos con la variable global.

## Verificación
Los logs confirman el funcionamiento correcto:
```log
INFO | controllers.ai_controller | Fuzzy match: 'alamcen' -> 'almacen' (🛒 Almacén)
INFO | controllers.ai_controller | Categorías detectadas...: ['🛒 Almacén']
INFO | services.ai_advisor_service | Contexto formateado: 3 gastos...
```
