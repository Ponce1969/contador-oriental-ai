# SPEC_LLAMA3_MEJORAS.md — Cerebro Híbrido

## 1. Visión General

Migración desde un modelo 100% local (Gemma 2:2b) hacia una **arquitectura de IA híbrida** donde cada modelo cumple un rol específico.

### Problema Actual
- Gemma 2:2b alucina en consultas complejas (inventa números, porcentajes, categorías)
- No puede cruzar datos de 3 meses con precisión
- No tiene conocimiento de normativa uruguaya (IVA, BPS, SUCIVE)

### Objetivos
1. Mejorar precisión en análisis financieros complejos
2. Reducir alucinaciones a cero en consultas con datos reales
3. Optimizar costos: modelo local para lo simple, cloud para lo complejo
4. Controlar gasto con cuotas diarias por usuario

---

## 2. Arquitectura: Hybrid Brain

```
┌─────────────────────────────────────────────────────┐
│                   AIAdvisorService                   │
│              (Orquestador Híbrido)                  │
│                                                     │
│  ┌──────────────┐    ┌─────────────────────────┐    │
│  │  QueryRouter │───▶│  Decisión de modelo     │    │
│  │              │    │                          │    │
│  │  Analiza:    │    │  simple → Gemma 2:2b     │    │
│  │  - Keywords  │    │  complejo → Llama 3 70B │    │
│  │  - Contexto  │    │  sin cuota → fallback    │    │
│  │  - Cuota     │    └─────────────────────────┘    │
│  └──────────────┘                                  │
│                                                     │
│  ┌──────────────┐    ┌─────────────────────────┐    │
│  │  Gemma 2:2b  │    │  Llama 3 70B (NVIDIA)   │    │
│  │  Ollama local│    │  API Cloud               │    │
│  │  temperature=0│   │  temperature=0.1          │    │
│  │  Gratis      │    │  Controlado por cuota    │    │
│  └──────────────┘    └─────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

### Modelo Local: Gemma 2:2b

| Campo | Valor |
|-------|-------|
| Modelo | `contador-oriental` (Modelfile custom) |
| Host | `OLLAMA_BASE_URL` (env var, default `http://localhost:11434`) |
| Tipo | Local / Offline |
| Temperatura | 0.0 (determinístico) |

**Usar cuando:**
- Clasificación de gastos simple
- Consultas de un solo mes ("¿cuánto gasté en supermercado?")
- Formateo rápido de respuestas pre-calculadas por Python
- El usuario agotó la cuota diaria de Llama 3

### Modelo Cloud: Llama 3 70B

| Campo | Valor |
|-------|-------|
| Modelo | `meta/llama3-70b-instruct` |
| Proveedor | NVIDIA API (build.nvidia.com) |
| Tipo | Cloud / Online |
| Temperatura | 0.1 |
| Auth | `NVIDIA_API_KEY` (env var) |

**Usar cuando (cualquiera de estas condiciones):**
- La pregunta involucra historial de ≥3 meses
- La pregunta menciona normativa uruguaya (IVA, BPS, IRPF, SUCIVE, patente, DGI)
- El botón "Preguntale al Contador sobre estos 3 meses" del Historial
- El `QueryAnalyzer` detecta keywords legales/fiscales
- Cálculos complejos (proyecciones de ahorro, optimización fiscal)

---

## 3. Gestión de Cuotas (QuotaManager)

### Tabla: `ai_usage`

```sql
CREATE TABLE ai_usage (
    id          SERIAL PRIMARY KEY,
    familia_id   INTEGER NOT NULL REFERENCES familias(id),
    date         DATE NOT NULL DEFAULT CURRENT_DATE,
    model       VARCHAR(20) NOT NULL,  -- 'gemma2' o 'llama3'
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(familia_id, date, model)
);

CREATE INDEX idx_ai_usage_lookup ON ai_usage(familia_id, date);
```

### Servicio: `QuotaManager`

```python
# services/infrastructure/quota_manager.py

class QuotaManager:
    DAILY_LIMIT_LLAMA3 = 10  # consultas diarias por familia

    def can_use_llama3(self, familia_id: int) -> bool:
        """Retorna True si la familia aún tiene cuota disponible."""

    def register_usage(self, familia_id: int, model: str, prompt_tokens: int, completion_tokens: int) -> None:
        """Registra una consulta en la tabla ai_usage."""

    def get_remaining(self, familia_id: int) -> int:
        """Retorna cuántas consultas Llama 3 quedan hoy."""

    def get_fallback_message(self) -> str:
        """Mensaje para el usuario cuando se agota la cuota."""
```

### Reglas de Cuota

| Regla | Detalle |
|-------|---------|
| Límite diario | 10 consultas Llama 3 por familia |
| Reset | Automático a medianoche (consulta por `date = CURRENT_DATE`) |
| Fallback | Si la cuota se agota: responder con Gemma 2 + mensaje "Respuesta con precisión reducida. Cuota diaria de consultas avanzadas agotada." |
| Uso de Gemma | Sin límite (es local y gratis) |
| Persistencia | PostgreSQL, tabla `ai_usage` |

### Comportamiento cuando la cuota se agota

1. El `QuotaManager.can_use_llama3()` retorna `False`
2. El orquestador cae automáticamente a Gemma 2:2b
3. El usuario ve un aviso en la respuesta: `⚠️ Respuesta con precisión reducida. La cuota diaria de consultas avanzadas está agotada. Se renueva a medianoche.`
4. El prompt de Gemma se refuerza con: "ADVERTENCIA: Estás respondiendo con información limitada. Sé conservador y agregá que la respuesta puede ser menos precisa."

---

## 4. El Orquestador Híbrido (AIAdvisorService)

### Routing de Modelo

```python
# services/ai/model_router.py

class ModelRouter:
    """Decide qué modelo usar basado en la pregunta y contexto."""

    KEYWORDS_LLAMA3 = frozenset([
        # Normativa uruguaya
        "iva", "bps", "irpf", "dgi", "sucive", "patente",
        "inclusion financiera", "beneficio tarjeta",
        # Análisis complejo
        "proyeccion", "ahorro", "optimizar", "planificar",
        "historial", "3 meses", "tres meses", "ultimos meses",
        # Legal/fiscal
        "deduccion", "exencion", "retencion", "tributo",
    ])

    def route(self, pregunta: str, ctx: AIContext, quota: QuotaManager, familia_id: int) -> str:
        """
        Retorna 'llama3' o 'gemma2'.

        Lógica:
        1. Si hay keywords de normativa → 'llama3' (si hay cuota)
        2. Si ctx.total_gastos_count >= 5 Y la pregunta involucra historial → 'llama3'
        3. Si viene del botón "Preguntale al Contador sobre estos 3 meses" → 'llama3'
        4. Si no hay cuota → 'gemma2' con aviso
        5. Default → 'gemma2'
        """
```

### Flujo Completo

```
Usuario pregunta
    │
    ▼
AIAdvisorService._construir_contexto()  ← Ya existe, sin cambios
    │
    ▼
QuotaManager.can_use_llama3(familia_id)
    │
    ├─ True ──→ ModelRouter.route()
    │              │
    │              ├─ "llama3" ──→ llamar NVIDIA API
    │              │                │
    │              │                ├─ Éxito ──→ Respuesta + register_usage()
    │              │                └─ Error ──→ fallback a Gemma 2
    │              │
    │              └─ "gemma2" ──→ llamar Ollama (ya existe)
    │
    └─ False ──→ Gemma 2 con aviso de cuota agotada
```

### Cambios en AIAdvisorService

```python
# Archivo: services/ai/ai_advisor_service.py

async def consultar(self, request, ctx, memoria_vectorial):
    # NUEVO: decisión de modelo
    model = self.router.route(request.pregunta, ctx, self.quota, request.familia_id)

    if model == "llama3":
        response = await self._call_nvidia_api(prompt, ctx)
        self.quota.register_usage(familia_id, "llama3", tokens)
        return response
    else:
        # Flujo existente con Ollama/Gemma (sin cambios)
        return await self._call_ollama(prompt, ctx)
```

### Cliente NVIDIA

```python
# services/infrastructure/nvidia_client.py

class NVIDIAClient:
    """Cliente async para NVIDIA API (Llama 3 70B)."""

    BASE_URL = "https://integrate.api.nvidia.com/v1"
    MODEL = "meta/llama3-70b-instruct"

    async def generate(self, prompt: str, temperature: float = 0.1, max_tokens: int = 1024) -> dict:
        """
        Llama a NVIDIA API con el prompt construido.
        Usa httpx AsyncClient con timeout de 30s.
        Retorna dict con 'response' y 'usage'.
        """
```

### Variables de Entorno

```bash
# AÑADIR a .env
NVIDIA_API_KEY=nvapi-xxxxx           # API key de NVIDIA
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
LLAMA3_DAILY_QUOTA=10                # Cuota diaria por familia
```

---

## 5. Base de Conocimiento (RAG)

### Ubicación: `knowledge/` (ya existe)

Archivos actuales:
- `irpf_familia_uy.md` — IRPF, deducciones familiares
- `inclusion_financiera_uy.md` — IVA, tarjetas
- `ahorro_ui_uy.md` — Unidades Indexadas

### Archivos a crear en `knowledge/`

| Archivo | Contenido |
|---------|-----------|
| `sucive_patentes_uy.md` | Calendario vencimientos 2026, descuentos pago anticipado |
| `bps_aportes_uy.md` | Monotributo, aportes sociales, categorías |
| `iva_general_uy.md` | Tasas 10%/22%, categorías exentas, beneficio inclusión financiera |

### Estructura de cada archivo `.md`

```markdown
# [Título]

## Conceptos
- Definiciones clave con montos exactos

## Consejos
- Buenas prácticas para familias uruguayas

## Ejemplos
- Casos reales con números

## Vencimientos (si aplica)
- Fecha | Concepto | Monto | Descuento anticipado

## Links Oficiales
- URLs gubernamentales verificadas
```

### Inyección de Contexto RAG (ya existe)

El sistema actual en `_seleccionar_contexto()` ya selecciona el archivo `.md` relevante por keywords. Se agrega `sucive_patentes_uy.md` al `mapa_conocimiento`:

```python
"sucive_patentes_uy.md": {
    "keywords": ["patente", "sucive", "vencimiento", "automotor", "vehiculo", "descuento"],
    "peso": 2,
},
```

---

## 6. Módulo Tributario (SUCIVE & Agenda)

### Funcionalidad

1. **Agenda Tributaria**: Vista que muestra próximos vencimientos
2. **Avisos Preventivos**: El Contador detecta fechas en la base de conocimiento y genera alertas
3. **Deep Links**: Las respuestas incluyen enlaces oficiales (ej: `https://sucive.gub.uy/consulta_deuda`)

### Implementación (Futura)

- Vista `views/pages/tributos_view.py`
- Ruta `/tributos`
- Datos cargados desde `knowledge/sucive_patentes_uy.md`

---

## 7. Reglas de Oro (Compliance del Agente)

### 💰 Moneda (MANDATORIO)

```
$    → Pesos Uruguayos (UYU)  — SIEMPRE con espacio: "$ 270.415"
USD  → Dólares estadounidenses — NUNCA U$S ni $U
```

### 🔢 Precisión Numérica (MANDATORIO — CRÍTICO)

```
❌ PROHIBIDO: float, 0.0, 0.5
✅ OBLIGATORIO: Decimal("0"), Decimal("270415")
```

**Regla absoluta**: En TODO el código financiero del Contador Oriental, los valores monetarios
son `Decimal`. Nunca `float`. Nunca `0.0`. Siempre `Decimal("0")`.

**Por qué**: Python `float` tiene errores de precisión. `0.1 + 0.2 = 0.30000000000000004`.
En sistema financiero, eso es inaceptable. `Decimal("0.1") + Decimal("0.2") = Decimal("0.3")`.

**Dónde aplicar**:
- Models: `monto: Decimal = Field(default=Decimal("0"))`
- Services: `total = sum((g.monto for g in gastos), Decimal("0"))`
- Controllers: `balance = ingresos - gastos  # Ambos son Decimal`
- AI formatters: `agrupar_gastos()` usa `Decimal("0")` como acumulador
- Formatters: `format_pesos()` recibe `Decimal` y retorna `str`

**Errores comunes a evitar**:
```python
# ❌ MAL — contamina Decimal con float
total = {"total": 0.0}  # float!
total["total"] += gasto.monto  # TypeError!

# ✅ BIEN — todo Decimal
total = {"total": Decimal("0")}
total["total"] += gasto.monto  # Decimal + Decimal = Decimal
```

### 🧑‍💼 Estilo del Agente

Perfil: **"Contador Oriental"**

Características:
- Directo y claro, sin tecnicismos innecesarios
- Conocimiento de normativa uruguaya
- Enfocado en ayudar al usuario a tomar decisiones
- Máximo 4 líneas de respuesta
- NUNCA inventar números ni porcentajes
- Si no tiene datos, decir "No tengo datos suficientes" en vez de inventar

### 📏 Límites del Prompt

```
- temperature: 0.0 (Gemma) / 0.1 (Llama 3) — minimizar alucinaciones
- max_tokens: 512 (Gemma) / 1024 (Llama 3)
- NUNCA inventar números — Los totales YA están calculados por Python
- NUNCA decir "la mitad" o porcentajes inventados — solo números exactos
- Si el dato no está en el contexto, NO mencionarlo
```

---

## 8. Flet 0.80 API (Referencia Rápida)

El proyecto usa Flet 0.80 que tiene APIs diferentes a versiones anteriores.

| Componente | Flet 0.25 (viejo) | Flet 0.80 (actual) |
|-----------|-------------------|-------------------|
| Botón primario | `ElevatedButton(text="X", icon=I)` | `ElevatedButton(content=ft.Row([ft.Icon(I), ft.Text("X")]))` |
| Botón texto | `TextButton(text="X")` | `TextButton(content=ft.Text("X"))` |
| Borde redondeado | `RoundedRectangleBorderRadius(radius=12)` | `RoundedRectangleBorder(radius=12)` |
| Markdown | `ft.Markdown(value=text, extension_set=GITHUB_WEB)` | ✅ igual, pero escapar `$` con `\$` antes de renderizar |
| Alineación | `ft.alignment.center` | `ft.Alignment(0, 0)` |

---

## 9. Estructura de Archivos Nueva

```
services/
├── ai/
│   ├── ai_advisor_service.py    # MODIFICAR: orquestador híbrido
│   ├── model_router.py           # NUEVO: decisión de modelo
│   ├── expense_formatters.py     # SIN CAMBIOS
│   ├── embedding_service.py      # SIN CAMBIOS
│   └── ia_memory_service.py     # SIN CAMBIOS
├── infrastructure/
│   ├── quota_manager.py          # NUEVO: control de cuotas
│   ├── nvidia_client.py          # NUEVO: cliente API NVIDIA
│   ├── exchange_rate_service.py  # SIN CAMBIOS
│   └── formatters.py             # SIN CAMBIOS

database/
├── tables.py                     # MODIFICAR: agregar AiUsageTable
└── migrations/
    └── 013_add_ai_usage.py       # NUEVO: migración

models/
└── ai_usage_model.py              # NUEVO: modelo Pydantic

knowledge/
├── irpf_familia_uy.md            # SIN CAMBIOS
├── inclusion_financiera_uy.md    # SIN CAMBIOS
├── ahorro_ui_uy.md               # SIN CAMBIOS
├── sucive_patentes_uy.md         # NUEVO: vencimientos y descuentos
├── iva_general_uy.md             # NUEVO: tasas y categorías
└── bps_aportes_uy.md             # NUEVO: monotributo y aportes

controllers/
├── ai_controller.py              # MODIFICAR: inyectar ModelRouter
└── history_controller.py          # SIN CAMBIOS
```

---

## 10. Plan de Ejecución (Fases)

### Fase 1: Infraestructura de Control (Freno de Mano)

**Objetivo**: Tener el QuotaManager funcionando ANTES de conectar Llama 3.

| Tarea | Archivos | Prioridad |
|-------|----------|-----------|
| Crear tabla `ai_usage` | `database/tables.py`, `migrations/013_add_ai_usage.py` | Alta |
| Crear modelo `AiUsage` | `models/ai_usage_model.py` | Alta |
| Crear `QuotaManager` | `services/infrastructure/quota_manager.py` | Alta |
| Crear repositorio `AiUsageRepository` | `repositories/ai_usage_repository.py` | Alta |
| Test unitario de cuota | `tests/test_quota_manager.py` | Alta |

**Criterio de aceptación**: `QuotaManager.can_use_llama3(familia_id=1)` retorna `True` las primeras 10 veces, `False` después.

### Fase 2: Orquestador Híbrido

**Objetivo**: El sistema decide qué modelo usar con base en la pregunta.

| Tarea | Archivos | Prioridad |
|-------|----------|-----------|
| Crear `ModelRouter` | `services/ai/model_router.py` | Alta |
| Crear `NVIDIAClient` | `services/infrastructure/nvidia_client.py` | Alta |
| Modificar `AIAdvisorService` | `services/ai/ai_advisor_service.py` | Alta |
| Inyectar router en `AIController` | `controllers/ai_controller.py` | Alta |
| Test de routing | `tests/test_model_router.py` | Alta |
| Agregar `NVIDIA_API_KEY` a `.env` | `.env`, `.env.example` | Media |

**Criterio de aceptación**: Preguntar "¿cuánto gasté en abril?" usa Gemma local. Preguntar "¿cuándo vence la patente?" use Llama 3 cloud.

### Fase 3: Conocimiento (RAG Mejorado)

**Objetivo**: El agente responde con datos reales de normativa uruguaya.

| Tarea | Archivos | Prioridad |
|-------|----------|-----------|
| Crear `sucive_patentes_uy.md` | `knowledge/sucive_patentes_uy.md` | Alta |
| Crear `iva_general_uy.md` | `knowledge/iva_general_uy.md` | Media |
| Crear `bps_aportes_uy.md` | `knowledge/bps_aportes_uy.md` | Media |
| Agregar keywords al mapa | `services/ai/ai_advisor_service.py` | Alta |
| Test de fuego: "¿Cuándo vence la patente?" | Manual | Alta |

**Criterio de aceptación**: Preguntar "¿Cuándo vence la patente este año y cuánto ahorro si pago todo junto?" responde con datos del `.md` SIN inventar.

### Fase 4: Módulo Tributario (Futuro)

**Objetivo**: Vista de Agenda Tributaria con alertas.

| Tarea | Archivos | Prioridad |
|-------|----------|-----------|
| Vista `TributosView` | `views/pages/tributos_view.py` | Baja |
| Ruta `/tributos` | `configs/routes.py` | Baja |
| Controlador | `controllers/tributos_controller.py` | Baja |

---

## 11. Notas de Implementación

### Principio fundamental: Python calcula, la IA narra

Los modelos de IA (ambos, Gemma y Llama) **NUNCA calculan**. Todos los números ya vienen pre-calculados por Python en `AIContext`. La IA solo lee y narra.

### Flujo de datos → IA

```
Python calcula:
  total_gastos = Decimal("270415")
  ingresos_total = Decimal("350000")
  balance = Decimal("79585")

AIContext se inyecta en el prompt:
  "TOTAL gastos del mes: $ 270.415"
  "Ingresos totales: $ 350.000"
  "BALANCE: $ 79.585"

La IA narra:
  "Tu balance es positivo: $ 79.585"
```

### Streaming

El flujo de streaming (`consultar_stream`) debe funcionar con ambos modelos. El `NVIDIAClient` también soporta streaming con `async for` sobre la respuesta.

### Manejo de errores NVIDIA API

```python
# Si NVIDIA falla:
try:
    response = await nvidia_client.generate(prompt)
except (ConnectionError, TimeoutError):
    # Fallback automático a Gemma 2
    logger.warning("NVIDIA API falló, usando Gemma como fallback")
    response = await self._call_ollama(prompt)
```

### Testing

Todos los servicios nuevos deben tener tests unitarios:
- `QuotaManager`: testear límite diario, reset, registro de uso
- `ModelRouter`: testear keywords, fallback, routing por contexto
- `NVIDIAClient`: mockear la API con `httpx` y `respx`