# Problemas Graves de Contador Oriental AI

Este documento explica los problemas más serios que pueden causar fallos en producción o comprometer la seguridad.

---

## 🔴 PROBLEMA #1: Estado Global en Memoria (No Escalable)

### ¿Qué está mal?

Tu aplicación usa diccionarios en memoria para guardar sesiones y rate limiting. Esto funciona con **una sola instancia**, pero fallará si alguna vez necesitas escalar.

### Archivos afectados:
- `core/security.py:29-52` - `RateLimiter` usa `_entradas: dict[str, _EntradaIntento]`
- `core/session.py:9-10` - `SessionManager` usa `_sessions = {}`

### Código problemático:

```python
# core/security.py - Línea 51
self._entradas: dict[str, _EntradaIntento] = {}
```

```python
# core/session.py - Línea 10
_sessions = {}
```

### ¿Por qué es grave?

1. **Si reinicias el contenedor Docker**: Se pierden todas las sesiones activas. Los usuarios tienen que volver a loguearse.
2. **Si tienes 2+ contenedores (load balancing)**: Cada uno tiene su propio diccionario. Un usuario logueado en contenedor A no está logueado en contenedor B.
3. **Rate limiting no funciona**: Un atacante puede hacer login fallido en contenedor A, luego en contenedor B, y nunca será bloqueado.

### Escenario real:

```
Usuario hace login → Contenedor 1 guarda sesión en _sessions
Usuario hace otro request → Load balancer envía a Contenedor 2
Contenedor 2 NO tiene esa sesión → Usuario es deslogueado
```

### Solución:

Mover el estado a **Redis** o **PostgreSQL**:

```python
# En lugar de:
_sessions = {}

# Usar Redis:
import redis
redis_client = redis.Redis(host='redis', port=6379, db=0)

def guardar_sesion(session_id, user_data):
    redis_client.setex(f"session:{session_id}", 28800, json.dumps(user_data))

def obtener_sesion(session_id):
    data = redis_client.get(f"session:{session_id}")
    return json.loads(data) if data else None
```

---

## 🔴 PROBLEMA #2: SECRET_KEY en .env.example

### ¿Qué está mal?

El archivo `.env.example` tiene un valor de ejemplo que podría ser usado accidentalmente en producción sin reemplazar.

### Archivo afectado:
- `.env.example:38`

### Código problemático:

```bash
# .env.example - Línea 38
SECRET_KEY=CAMBIA_ESTO_genera_con_python_secrets_token_hex_32
```

### ¿Por qué es grave?

1. Si alguien copia `.env.example` → `.env` sin cambiar el valor, tu app usa una SECRET_KEY pública.
2. La SECRET_KEY se usa para firmar sesiones/cookies. Si es conocida, un atacante puede falsificar sesiones.
3. No hay validación que impida iniciar la app con este valor.

### Escenario real:

```
Desarrollador nuevo copia .env.example → .env
No lee el comentario "CAMBIA_ESTO"
App inicia con SECRET_KEY pública
Atacante puede falsificar cookies de sesión
```

### Solución:

Validar al inicio que la SECRET_KEY no sea el valor por defecto:

```python
# main.py - Agregar al inicio
SECRET_KEY = os.getenv("SECRET_KEY")
if SECRET_KEY == "CAMBIA_ESTO_genera_con_python_secrets_token_hex_32":
    raise ValueError(
        "SECRET_KEY no está configurado correctamente. "
        "Usar: python -c 'import secrets; print(secrets.token_hex(32))'"
    )
```

---

## 🔴 PROBLEMA #3: Manejo de Errores en IA Oculta Causa Raíz

### ¿Qué está mal?

El servicio de IA catch excepciones genéricas y retorna strings vacíos, haciendo imposible debuggear problemas.

### Archivo afectado:
- `services/ai/ai_advisor_service.py:303-305`

### Código problemático:

```python
# services/ai/ai_advisor_service.py - Líneas 303-305
except Exception as e:
    logger.warning("[AI] llamada_directa falló: %s", e)
    return ""
```

### ¿Por qué es grave?

1. No sabes **por qué** falló la IA. ¿Falla de red? Timeout? Modelo no encontrado? Prompt inválido?
2. El usuario ve una respuesta vacía sin explicación.
3. No hay métricas de qué tipo de errores ocurren más frecuentemente.

### Escenario real:

```
Usuario pregunta: "¿Cuánto gasté en alimentación?"
Ollama está caído → Exception
logger dice: "[AI] llamada_directa falló: Connection refused"
Usuario ve: "" (nada)
Usuario piensa: "La app no funciona"
Tú no sabes que Ollama está caído hasta revisar logs
```

### Solución:

Retornar errores específicos con mensajes para el usuario:

```python
except ConnectionError as e:
    logger.error("[AI] Ollama no responde: %s", e)
    return Err(AppError(
        message="El Contador Oriental no está disponible. Intentá más tarde."
    ))
except TimeoutError as e:
    logger.error("[AI] Timeout en Ollama: %s", e)
    return Err(AppError(
        message="La consulta está tardando demasiado. Intentá con una pregunta más corta."
    ))
except Exception as e:
    logger.exception("[AI] Error inesperado")  # Stack trace completo
    return Err(AppError(
        message="Ocurrió un error inesperado. Contactá al administrador."
    ))
```

---

## 🔴 PROBLEMA #4: Consulta SQL Raw Potencialmente Vulnerable

### ¿Qué está mal?

La búsqueda de embeddings usa SQL raw con conversión de embedding a string. Aunque usa parámetros, la conversión podría ser problemática.

### Archivo afectado:
- `repositories/expense_repository.py:83-97`

### Código problemático:

```python
# repositories/expense_repository.py - Líneas 83-97
sql = text("""
    SELECT id, (embedding <=> CAST(:emb AS vector)) AS distancia
    FROM expenses
    WHERE familia_id = :fid
      AND embedding IS NOT NULL
      AND (embedding <=> CAST(:emb AS vector)) <= :umbral
    ORDER BY distancia ASC
    LIMIT :limite
""")
rows = self.session.execute(sql, {
    "emb": str(embedding),  # ← Aquí está el riesgo
    "fid": self.familia_id,
    "umbral": umbral_cosine,
    "limite": limite,
}).fetchall()
```

### ¿Por qué es grave?

1. `str(embedding)` convierte una lista de floats a string. Si el embedding viene de input externo (OCR, usuario), podría contener caracteres maliciosos.
2. SQLAlchemy `text()` con parámetros es seguro, pero la conversión previa no está validada.
3. Si alguien logra inyectar SQL en el embedding string, podrían leer datos de otras familias.

### Escenario real (hipotético):

```python
# Embedding malicioso (si viene de input externo sin validar)
embedding_malicioso = [1.0, 2.0, "'); DROP TABLE expenses; --"]
str(embedding_malicioso)  # → "[1.0, 2.0, ''); DROP TABLE expenses; --]"
```

### Solución:

Validar que el embedding sea una lista de floats válida antes de convertir:

```python
def _validar_embedding(embedding: list[float]) -> None:
    """Validar que el embedding sea una lista de floats válida."""
    if not isinstance(embedding, list):
        raise ValueError("Embedding debe ser una lista")
    for i, val in enumerate(embedding):
        if not isinstance(val, (int, float)):
            raise ValueError(f"Embedding[{i}] no es un número: {val}")
        if not (-1 <= val <= 1):  # pgvector embeddings suelen estar normalizados
            raise ValueError(f"Embedding[{i}] fuera de rango [-1, 1]: {val}")

# Usar antes de la query
_validar_embedding(embedding)
rows = self.session.execute(sql, {...})
```

---

## 🟠 PROBLEMA #5: Performance - Cálculos en Python en vez de SQL

### ¿Qué está mal?

El resumen de gastos por categoría se calcula iterando en Python en vez de usar SQL `GROUP BY`.

### Archivo afectado:
- `services/domain/expense_service.py:90-104`

### Código problemático:

```python
# services/domain/expense_service.py - Líneas 90-104
def get_summary_by_categories(self, ...) -> dict[str, float]:
    expenses = self.list_expenses()  # ← Carga TODOS los gastos
    summary: dict[str, float] = {}
    for expense in expenses:  # ← Itera en Python
        categoria = expense.categoria.value
        summary[categoria] = summary.get(categoria, 0.0) + expense.monto
    return summary
```

### ¿Por qué es grave?

1. Carga **todos** los gastos en memoria. Si tienes 10,000 gastos, son 10,000 objetos en RAM.
2. Itera en Python (lento) en vez de SQL (optimizado).
3. Si agregas filtros (por mes, año), primero carga TODO y luego filtra.

### Escenario real:

```
Familia tiene 50,000 gastos históricos
Usuario quiere resumen de este mes
list_expenses() carga 50,000 objetos en memoria
Python itera 50,000 veces
Tarda 5-10 segundos
```

### Solución:

Usar SQL `GROUP BY`:

```python
def get_summary_by_categories(self, year: int | None, month: int | None) -> dict[str, float]:
    from sqlalchemy import func, extract
    
    query = self.session.query(
        ExpenseTable.categoria,
        func.sum(ExpenseTable.monto).label('total')
    )
    
    if year and month:
        query = query.filter(
            extract('year', ExpenseTable.fecha) == year,
            extract('month', ExpenseTable.fecha) == month
        )
    
    query = self._filter_by_family(query)
    query = query.group_by(ExpenseTable.categoria)
    
    results = query.all()
    return {row.categoria: row.total for row in results}
```

**Resultado**: 1 query SQL vs 50,000 objetos en memoria.

---

## 🟠 PROBLEMA #6: Sin Paginación en Listados

### ¿Qué está mal?

Los listados de gastos e ingresos no tienen paginación. Cargan todos los registros.

### Archivos afectados:
- `services/domain/expense_service.py:44-47`
- `services/domain/income_service.py:46-49`

### Código problemático:

```python
# services/domain/expense_service.py - Líneas 44-47
def list_expenses(self) -> list[Expense]:
    expenses = self._repo.get_all()  # ← Todos, sin límite
    return list(expenses)
```

### ¿Por qué es grave?

1. Si tienes 100,000 gastos, el navegador se congela al renderizar.
2. Transferencia de datos masiva del servidor al cliente.
3. Timeout en Cloudflare Tunnel si la respuesta es muy grande.

### Escenario real:

```
Usuario tiene 5 años de datos = 60,000 gastos
Abre página de gastos
Servidor devuelve 60,000 objetos (JSON de ~10MB)
Navegador intenta renderizar 60,000 filas
Se congela por 10-20 segundos
```

### Solución:

Agregar paginación:

```python
def list_expenses(self, page: int = 1, per_page: int = 50) -> list[Expense]:
    offset = (page - 1) * per_page
    expenses = self._repo.get_all_paginated(offset, per_page)
    return list(expenses)

# En el repository:
def get_all_paginated(self, offset: int, limit: int) -> Sequence[T]:
    query = self.session.query(self.table_model)
    query = self._filter_by_family(query)
    query = query.order_by(self.table_model.fecha.desc())
    query = query.offset(offset).limit(limit)
    return query.all()
```

---

## 🟠 PROBLEMA #7: Logging Sin Niveles por Entorno

### ¿Qué está mal?

El logger está configurado en `INFO` para todos los entornos. No hay diferencia entre desarrollo y producción.

### Archivo afectado:
- `core/logger.py:33-40`

### Código problemático:

```python
# core/logger.py - Líneas 33-40
logging.basicConfig(
    level=logging.INFO,  # ← Siempre INFO, nunca DEBUG en dev
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[...],
)
```

### ¿Por qué es grave?

1. En desarrollo, quieres `DEBUG` para ver queries SQL, detalles de requests, etc.
2. En producción, `DEBUG` genera too much noise y puede exponer datos sensibles.
3. No hay forma de cambiar el nivel sin editar código.

### Escenario real:

```
Desarrollador intenta debuggear un problema
No ve detalles porque logging está en INFO
Tiene que agregar print() statements (mala práctica)
```

### Solución:

Configurar por entorno:

```python
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[...],
)

# .env.example
LOG_LEVEL=DEBUG  # En desarrollo
# LOG_LEVEL=INFO  # En producción
```

---

## 🟡 PROBLEMA #8: Validación de Contraseña Débil

### ¿Qué está mal?

La validación de contraseña solo verifica longitud >= 6. No hay validación de complejidad.

### Archivo afectado:
- `services/domain/auth_service.py:135-140`

### Código problemático:

```python
# services/domain/auth_service.py - Líneas 135-140
if len(new_password) < 6:
    return Err(
        ValidationError(
            message="La contraseña debe tener al menos 6 caracteres"
        )
    )
```

### ¿Por qué es grave?

1. `123456` pasa la validación pero es muy insegura.
2. Sin mayúsculas, números, símbolos, las contraseñas son fáciles de crackear.
3. Ataques de diccionario pueden encontrar contraseñas simples rápidamente.

### Escenario real:

```
Usuario crea contraseña: "password123"
Pasa validación (longitud >= 6)
Atacante usa diccionario de contraseñas comunes
Encuentra "password123" en segundos
```

### Solución:

Validar complejidad:

```python
import re

def _validar_contrasena(password: str) -> Result[None, ValidationError]:
    if len(password) < 8:
        return Err(ValidationError(message="Mínimo 8 caracteres"))
    if not re.search(r"[A-Z]", password):
        return Err(ValidationError(message="Debe tener mayúscula"))
    if not re.search(r"[a-z]", password):
        return Err(ValidationError(message="Debe tener minúscula"))
    if not re.search(r"\d", password):
        return Err(ValidationError(message="Debe tener número"))
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return Err(ValidationError(message="Debe tener símbolo"))
    return Ok(None)
```

---

## 🟡 PROBLEMA #9: Sin Índices en Base de Datos

### ¿Qué está mal?

Las tablas no tienen índices definidos más allá de primary keys. Queries frecuentes son lentas.

### Archivo afectado:
- `database/tables.py` (todas las tablas)

### Código problemático:

```python
# database/tables.py - Ejemplo de tabla sin índices
class ExpenseTable(Base):
    __tablename__ = "expenses"
    
    id: Mapped[int] = mapped_column(primary_key=True)  # ← Solo PK
    familia_id: Mapped[int] = mapped_column(Integer, ...)  # ← Sin índice
    fecha: Mapped[date] = mapped_column(Date, ...)  # ← Sin índice
    categoria: Mapped[str] = mapped_column(String(50), ...)  # ← Sin índice
```

### ¿Por qué es grave?

1. Queries por `familia_id` hacen full table scan.
2. Queries por `fecha` (mes/año) son lentas.
3. Queries por `categoria` son lentas.
4. Con 100,000+ registros, la app se vuelve lenta.

### Escenario real:

```
SELECT * FROM expenses WHERE familia_id = 1 AND fecha = '2026-03-01'
→ PostgreSQL escanea todas las filas (100,000)
→ Tarda 2-3 segundos
```

### Solución:

Agregar índices:

```python
from sqlalchemy import Index

class ExpenseTable(Base):
    __tablename__ = "expenses"
    
    # ... campos ...
    
    # Índices compuestos para queries frecuentes
    __table_args__ = (
        Index('idx_expenses_familia_fecha', 'familia_id', 'fecha'),
        Index('idx_expenses_familia_categoria', 'familia_id', 'categoria'),
    )
```

**Resultado**: Queries pasan de 2-3s a <50ms.

---

## 🟢 PROBLEMA #10: Placeholder sin Reemplazar

### ¿Qué está mal?

`AppConfig.APP_NAME` tiene un placeholder que nunca se reemplaza.

### Archivo afectado:
- `configs/app_config.py:28`

### Código problemático:

```python
# configs/app_config.py - Línea 28
APP_NAME = "{project_name}"  # ← Placeholder
```

### ¿Por qué es grave?

Es menor, pero indica falta de atención al detalle. Si alguna parte del código usa `AppConfig.APP_NAME`, mostrará "{project_name}" en vez del nombre real.

### Solución:

```python
APP_NAME = "Contador Oriental AI"
```

---

## Resumen de Prioridades

### Para arreglar HOY (crítico):
1. **PROBLEMA #2**: Validar que `SECRET_KEY` no sea el valor por defecto
2. **PROBLEMA #3**: Mejorar manejo de errores en IA para debuggear
3. **PROBLEMA #4**: Validar embeddings antes de SQL

### Para arreglar esta semana (alto):
4. **PROBLEMA #1**: Mover estado a Redis o PostgreSQL
5. **PROBLEMA #5**: Optimizar `get_summary_by_categories` con SQL
6. **PROBLEMA #6**: Agregar paginación a listados

### Para arreglar este mes (medio):
7. **PROBLEMA #7**: Configurar logging por entorno
8. **PROBLEMA #8**: Mejorar validación de contraseñas
9. **PROBLEMA #9**: Agregar índices a BD

### Cosas menores:
10. **PROBLEMA #10**: Reemplazar placeholder

---

## Nota sobre tu infraestructura

Dado que tu app corre en **Orange Pi 5 Plus** detrás de **Cloudflare Tunnel** con **PostgreSQL en Docker**:

- El **PROBLEMA #1** (estado en memoria) es MENOS grave si solo tienes 1 contenedor. Pero sigue siendo un problema si reinicias.
- El **PROBLEMA #2** (SECRET_KEY) es MUY grave porque Cloudflare Tunnel expone tu app públicamente.
- El **PROBLEMA #5** (performance) es MUY grave en Orange Pi porque tiene menos RAM/CPU que un servidor dedicado.
- El **PROBLEMA #9** (índices) es CRÍTICO en Orange Pi porque PostgreSQL en ARM64 puede ser más lento.

**Recomendación inmediata**: Arreglar PROBLEMA #2 y #9 primero, porque tienen el mayor impacto en tu infraestructura actual.
