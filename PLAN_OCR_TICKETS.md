# 📷 Plan OCR de Tickets — Contador Oriental AI

## 🎯 Visión General

Permitir que el usuario saque una foto a un ticket de compra y el sistema lo ingrese
automáticamente como gasto, con categoría sugerida y confirmación antes de guardar.
El OCR es 100% local (Tesseract), sin APIs externas, compatible con Orange Pi 5 Plus (ARM64).

---

## 🏗️ Arquitectura del Nuevo Flujo

```
Usuario sube foto (FilePicker en Flet)
    └─→ OCRController
            ├─→ [async] OCRService.extraer_texto()
            │       └─→ Tesseract (lang=spa) → texto_crudo (imperfecto)
            ├─→ [async] TicketService.parsear_con_gemma(texto_crudo)
            │       └─→ Gemma 2:2b → {monto, fecha, comercio, items[]}
            ├─→ [async] ExpenseRepository.buscar_por_similitud(comercio)
            │       └─→ cosine search en expenses.embedding → categoría sugerida
            └─→ Vista: formulario pre-llenado para confirmación
                    └─→ Usuario confirma/edita
                            └─→ ExpenseController (flujo normal ya existente)
                                    └─→ GASTO_CREADO → embedding → vectorización
```

### Principios de diseño
- **No romper lo existente** — el OCR es una entrada alternativa al formulario manual
- **Fire-and-forget** — el procesamiento OCR no bloquea la UI (igual que los embeddings)
- **Confirmación obligatoria** — el usuario siempre revisa antes de guardar
- **Fallback defensivo** — si Gemma falla al parsear, se muestra el texto crudo para edición manual

---

## 📋 Estado Actual del Proyecto (Prerrequisitos)

### ✅ Ya implementado (no tocar)
- `expenses.embedding vector(768)` — columna para búsqueda cosine
- `ExpenseRepository.buscar_por_similitud()` — cosine search funcional
- `EventSystem` fire-and-forget — para vectorización en background
- `ExpenseController` → `GASTO_CREADO` — flujo de guardado completo
- `EmbeddingService` → `nomic-embed-text` — genera embeddings 768d
- `AIAdvisorService` → Gemma 2:2b — modelo disponible para parseo

### ❌ Lo que falta implementar
- `migrations/008_add_ticket_fields.py`
- `models/ticket_model.py` — `PartialExpense` (modelo de dominio temporal)
- `services/ocr_service.py` — extracción de texto con Tesseract
- `services/ticket_service.py` — orquestador OCR + parser + sugerencia
- `controllers/ocr_controller.py`
- `views/pages/ticket_upload_view.py` — FilePicker + spinner + formulario
- Actualización del `Dockerfile`
- Tests correspondientes

---

## 🗄️ Fase 1: Migración de Base de Datos

### `migrations/008_add_ticket_fields.py`

```python
def up(conn):
    conn.execute("""
        ALTER TABLE expenses
        ADD COLUMN IF NOT EXISTS ticket_image_path TEXT,
        ADD COLUMN IF NOT EXISTS ocr_texto_crudo   TEXT,
        ADD COLUMN IF NOT EXISTS ocr_confianza     FLOAT;
    """)

def down(conn):
    conn.execute("""
        ALTER TABLE expenses
        DROP COLUMN IF EXISTS ticket_image_path,
        DROP COLUMN IF EXISTS ocr_texto_crudo,
        DROP COLUMN IF EXISTS ocr_confianza;
    """)
```

**Campos:**
| Campo | Tipo | Propósito |
|---|---|---|
| `ticket_image_path` | TEXT | Ruta relativa de la imagen (temporal, se limpia) |
| `ocr_texto_crudo` | TEXT | Texto extraído por Tesseract (para auditoría) |
| `ocr_confianza` | FLOAT | 0.0–1.0, confianza del OCR (para detectar tickets ilegibles) |

---

## 📦 Fase 2: Modelo de Dominio

### `models/ticket_model.py`

```python
"""
Modelo temporal de dominio para un ticket OCR antes de ser confirmado
como Expense definitivo. No persiste en BD directamente.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date


@dataclass
class PartialExpense:
    """
    Resultado del parseo de un ticket. Todos los campos son opcionales
    porque el OCR puede no encontrar todos (ticket roto, mala foto, etc.)
    El usuario completa lo que falte en la vista de confirmación.
    """
    monto: float | None = None
    fecha: date | None = None
    comercio: str | None = None
    items: list[str] = field(default_factory=list)
    categoria_sugerida: str | None = None   # Viene del cosine search
    confianza_ocr: float = 0.0              # 0.0 = ilegible, 1.0 = perfecto
    texto_crudo: str = ""                   # Texto Tesseract sin procesar
    imagen_path: str = ""                   # Ruta temporal de la imagen
```

---

## ⚙️ Fase 3: Servicios

### 3.1 `services/ocr_service.py` — Extracción Tesseract

```python
"""
Servicio de OCR local con Tesseract.
Extrae texto de imágenes de tickets. No interpreta — solo extrae texto crudo.
La interpretación la hace TicketService con Gemma.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter
from result import Err, Ok, Result

from models.errors import AppError
from models.ticket_model import PartialExpense

logger = logging.getLogger(__name__)


class OCRService:
    """Extrae texto de imágenes de tickets usando Tesseract (local, sin GPU)."""

    # Umbral mínimo de caracteres para considerar que el OCR tuvo éxito
    _MIN_CHARS = 20

    def _preprocesar_imagen(self, imagen: Image.Image) -> Image.Image:
        """
        Mejora la imagen antes de pasarla a Tesseract:
        escala de grises → contraste → nitidez.
        Mejora la tasa de acierto en tickets de papel térmico.

        🇺🇾 Tip Uruguay: los tickets locales suelen tener el RUT del comercio
        al principio o al final. Gemma los ignora bien con el prompt actual.
        Si en el futuro Gemma se confunde con el RUT (ej. lo interpreta como monto),
        se puede recortar los márgenes superior/inferior aquí antes de pasar a Tesseract:
            ancho, alto = imagen.size
            imagen = imagen.crop((0, 50, ancho, alto - 50))  # recortar 50px arriba y abajo
        Por ahora NO se recorta — el contraste + nitidez es suficiente para papel térmico.
        """
        imagen = imagen.convert("L")                        # Escala de grises
        imagen = ImageEnhance.Contrast(imagen).enhance(2.0) # Más contraste
        imagen = imagen.filter(ImageFilter.SHARPEN)          # Nitidez
        return imagen

    async def extraer_texto(self, imagen_path: str) -> Result[PartialExpense, AppError]:
        """
        Lee una imagen y extrae el texto con Tesseract (lang=spa).
        Retorna un PartialExpense con texto_crudo y confianza_ocr.
        """
        try:
            import pytesseract  # Import tardío: no falla si no está instalado

            path = Path(imagen_path)
            if not path.exists():
                return Err(AppError(f"Imagen no encontrada: {imagen_path}"))

            imagen = Image.open(path)
            imagen = self._preprocesar_imagen(imagen)

            # Extraer texto + datos de confianza por palabra
            datos = pytesseract.image_to_data(
                imagen,
                lang="spa",
                output_type=pytesseract.Output.DICT,
            )
            texto_crudo = " ".join(
                w for w in datos["text"] if w.strip()
            )
            # Confianza promedio de palabras con conf > 0
            confs = [c for c in datos["conf"] if c > 0]
            confianza = round(sum(confs) / len(confs) / 100, 2) if confs else 0.0

            if len(texto_crudo) < self._MIN_CHARS:
                logger.warning("[OCR] Texto muy corto (%.0f chars) — imagen ilegible", len(texto_crudo))
                confianza = 0.0

            logger.info("[OCR] Extraídos %d chars (confianza=%.2f)", len(texto_crudo), confianza)

            return Ok(PartialExpense(
                texto_crudo=texto_crudo,
                confianza_ocr=confianza,
                imagen_path=imagen_path,
            ))

        except ImportError:
            return Err(AppError("pytesseract no está instalado. Ejecutá: uv add pytesseract pillow"))
        except Exception as e:
            logger.error("[OCR] Error procesando imagen: %s", e)
            return Err(AppError(f"Error OCR: {e}"))
```

---

### 3.2 `services/ticket_service.py` — Orquestador

```python
"""
Orquestador del flujo OCR completo:
  1. OCRService extrae texto crudo
  2. Gemma parsea el texto y extrae monto/fecha/comercio
  3. ExpenseRepository busca categoría por similitud cosine
  4. Retorna PartialExpense listo para mostrar al usuario
"""
from __future__ import annotations

import json
import logging
import re

from result import Err, Ok, Result

from models.errors import AppError
from models.ticket_model import PartialExpense
from services.ocr_service import OCRService
from services.embedding_service import EmbeddingService
from repositories.expense_repository import ExpenseRepository

logger = logging.getLogger(__name__)

# Prompt estructurado para Gemma — respuesta JSON estricta
_PROMPT_PARSEO = """Analizá este texto de un ticket de compra uruguayo y extraé los datos.
Respondé ÚNICAMENTE con un JSON válido, sin texto adicional, en este formato exacto:

{{
  "monto": 1250.0,
  "fecha": "2026-02-28",
  "comercio": "Tienda Inglesa",
  "items": ["leche", "pan", "aceite"]
}}

Si no podés determinar un campo, usá null.
La fecha debe estar en formato YYYY-MM-DD.
El monto debe ser el TOTAL del ticket (número sin símbolos).

Texto del ticket:
{texto}
"""


class TicketService:
    """Orquesta OCR + parseo Gemma + sugerencia de categoría."""

    def __init__(
        self,
        ocr_service: OCRService,
        embedding_service: EmbeddingService,
        expense_repo: ExpenseRepository,
        ai_service,  # AIAdvisorService — inyectado para reutilizar conexión Ollama
    ):
        self.ocr = ocr_service
        self.embedding = embedding_service
        self.expense_repo = expense_repo
        self.ai_service = ai_service

    async def procesar_ticket(self, imagen_path: str) -> Result[PartialExpense, AppError]:
        """Flujo completo: imagen → PartialExpense con categoría sugerida."""

        # 1. Extraer texto con Tesseract
        ocr_result = await self.ocr.extraer_texto(imagen_path)
        if isinstance(ocr_result, Err):
            return ocr_result

        partial = ocr_result.ok()

        # Si la confianza es muy baja, avisar pero seguir (usuario puede corregir)
        if partial.confianza_ocr < 0.3:
            logger.warning("[TICKET] Confianza OCR baja (%.2f) — imagen de mala calidad", partial.confianza_ocr)

        # 2. Parsear con Gemma
        parsed = await self._parsear_con_gemma(partial.texto_crudo)
        if parsed:
            partial.monto = parsed.get("monto")
            partial.fecha = parsed.get("fecha")
            partial.comercio = parsed.get("comercio")
            partial.items = parsed.get("items") or []

        # 3. Sugerir categoría via cosine search (si tenemos comercio o items)
        termino_busqueda = partial.comercio or " ".join(partial.items[:3])
        if termino_busqueda:
            partial.categoria_sugerida = await self._sugerir_categoria(termino_busqueda)

        return Ok(partial)

    async def _parsear_con_gemma(self, texto: str) -> dict | None:
        """
        Pide a Gemma que extraiga monto/fecha/comercio/items del texto crudo.
        Parser defensivo: si Gemma devuelve basura, retorna None (el usuario llena a mano).
        """
        try:
            prompt = _PROMPT_PARSEO.format(texto=texto[:1500])  # Limitar tokens
            respuesta = await self.ai_service.llamada_directa(prompt)

            # Buscar JSON en la respuesta (Gemma a veces agrega texto antes/después)
            match = re.search(r'\{.*?\}', respuesta, re.DOTALL)
            if not match:
                logger.warning("[TICKET] Gemma no devolvió JSON válido")
                return None

            datos = json.loads(match.group())
            logger.info("[TICKET] Gemma parseó: comercio=%s monto=%s", datos.get("comercio"), datos.get("monto"))
            return datos

        except (json.JSONDecodeError, Exception) as e:
            logger.warning("[TICKET] Error parseando respuesta de Gemma: %s", e)
            return None  # Fallback: el usuario completa manualmente

    async def _sugerir_categoria(self, termino: str) -> str | None:
        """Busca la categoría más probable via cosine search en expenses.embedding."""
        try:
            emb_result = await self.embedding.generar_embedding(termino)
            from result import Err as ErrType
            if isinstance(emb_result, ErrType):
                return None
            resultados = self.expense_repo.buscar_por_similitud(emb_result.ok(), umbral_cosine=0.25)
            if resultados:
                # Categoría más frecuente entre los resultados
                from collections import Counter
                cats = Counter(g.categoria.value for g, _ in resultados)
                return cats.most_common(1)[0][0]
        except Exception as e:
            logger.warning("[TICKET] Error sugiriendo categoría: %s", e)
        return None
```

---

## 🖥️ Fase 4: Vista de Upload

### `views/pages/ticket_upload_view.py` — puntos clave

```python
# Estructura de la vista (pseudocódigo Flet)

class TicketUploadView:
    """
    Vista de carga de ticket OCR.
    
    Estados:
      IDLE      — FilePicker disponible, botón "Subir ticket"
      LOADING   — Spinner mientras Tesseract + Gemma procesan
      CONFIRM   — Formulario pre-llenado con datos del ticket
      ERROR     — Mensaje de error + opción de carga manual
    """

    def build_idle(self):
        # FilePicker + botón + instrucciones ("Foto clara, buena luz")
        ...

    def build_loading(self):
        # ProgressRing + mensaje "Leyendo tu ticket..."
        ...

    def build_confirm(self, partial: PartialExpense):
        # Formulario con todos los campos de Expense pre-llenados
        # Campos editables: monto, fecha, categoria, descripcion
        # Chip de confianza OCR: verde/amarillo/rojo según ocr_confianza
        # Botones: "Guardar" (→ ExpenseController) | "Descartar"
        ...

    def build_error(self, mensaje: str):
        # Mensaje + botón "Cargar manualmente"
        ...
```

---

## 🐳 Fase 5: Docker

### Cambios en `Dockerfile`

```dockerfile
# Agregar DESPUÉS de la instalación de gcc y libpq-dev
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    tesseract-ocr \
    tesseract-ocr-spa \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*
```

> ⚠️ `tesseract-ocr-spa` pesa ~20MB. La imagen Docker va a crecer proporcionalmente.
> Para Orange Pi: la imagen `pgvector/pgvector:pg16` ya es ARM64, Tesseract también tiene paquete ARM64 en Debian.

### Dependencias Python (`pyproject.toml`)

```toml
# Agregar en [project.dependencies]
"pytesseract>=0.3.13",
"pillow>=11.0.0",
```

---

## 🧪 Fase 6: Tests

### Estructura de tests a crear

```
tests/
├── test_ocr_service.py        # Mock de pytesseract, test con imagen de ejemplo
├── test_ticket_service.py     # Mock de OCRService + Gemma, test flujo completo
└── fixtures/
    └── ticket_ejemplo.png     # Imagen de ticket real para test de integración
```

### Tests mínimos requeridos

```python
# test_ocr_service.py
def test_ocr_imagen_ilegible_retorna_confianza_baja()
def test_ocr_imagen_valida_retorna_texto()
def test_ocr_archivo_no_existe_retorna_error()

# test_ticket_service.py
def test_parseo_gemma_json_valido()
def test_parseo_gemma_json_invalido_retorna_none()  # Fallback defensivo
def test_categoria_sugerida_via_cosine()
def test_flujo_completo_con_mocks()
```

---

## 📁 Estructura Final de Archivos Nuevos

```
contador-oriental/
├── 📁 models/
│   └── ticket_model.py            # PartialExpense (nuevo)
├── 📁 services/
│   ├── ocr_service.py             # Tesseract wrapper (nuevo)
│   └── ticket_service.py         # Orquestador (nuevo)
├── 📁 controllers/
│   └── ocr_controller.py         # Thin controller (nuevo)
├── 📁 views/pages/
│   └── ticket_upload_view.py     # UI de upload + confirmación (nuevo)
├── 📁 migrations/
│   └── 008_add_ticket_fields.py  # ticket_image_path, ocr_texto_crudo, ocr_confianza (nuevo)
├── 📁 tests/
│   ├── test_ocr_service.py        # (nuevo)
│   ├── test_ticket_service.py    # (nuevo)
│   └── fixtures/
│       └── ticket_ejemplo.png    # (nuevo)
└── 📄 Dockerfile                 # + tesseract-ocr-spa
```

---

## ⚠️ Decisiones de Diseño Importantes

| Decisión | Razón |
|---|---|
| **Tesseract, no EasyOCR** | EasyOCR requiere PyTorch (~500MB). Tesseract: ~20MB, compatible ARM64 |
| **Gemma como parser, no regex** | Los tickets uruguayos no tienen formato estándar. Regex falla con variaciones |
| **`PartialExpense` no hereda de `Expense`** | Es un DTO temporal, no un objeto de dominio. No debe persistir directamente |
| **Confirmación obligatoria** | OCR tiene ~85% de acierto en tickets de papel térmico. El usuario es la última validación |
| **`llamada_directa()` en AIAdvisorService** | Necesitamos una llamada síncrona/directa a Gemma sin el contexto financiero del Contador |
| **Imágenes temporales** | No guardar fotos en producción. Borrar después de procesar. Solo guardar la ruta en BD si el usuario confirma |
| **`ocr_texto_crudo` en BD** | Permite auditar después si el OCR categorizó mal. Útil para mejorar el sistema |

---

## 🚦 Orden de Implementación

```
Día 1:
  [1] migrations/008_add_ticket_fields.py   → uv run fleting db migrate
  [2] models/ticket_model.py                → PartialExpense dataclass

Día 2:
  [3] services/ocr_service.py               → Tesseract wrapper + preprocesado
  [4] tests/test_ocr_service.py             → Tests con mocks
  [5] Dockerfile                            → tesseract-ocr-spa + rebuild

Día 3:
  [6] AIAdvisorService.llamada_directa()    → Método nuevo para llamada directa a Gemma
  [7] services/ticket_service.py            → Orquestador completo
  [8] tests/test_ticket_service.py          → Tests con mocks

Día 4:
  [9] controllers/ocr_controller.py
  [10] views/pages/ticket_upload_view.py    → UI con estados IDLE/LOADING/CONFIRM/ERROR
  [11] Agregar ruta en configs/routes.py
  [12] Tests de integración
```

---

## 📌 Notas para el Siguiente Agente / Junior

1. **No modificar `ExpenseController`** — el OCR desemboca en el flujo normal existente
2. **No modificar `Modelfile`** — Gemma 2:2b ya puede parsear tickets con el prompt correcto
3. **El método `llamada_directa()` en `AIAdvisorService`** es el único cambio en servicios existentes
4. **`buscar_por_similitud()` en `ExpenseRepository` ya existe** — usarlo tal cual para la categoría sugerida
5. **La ruta de upload debe ser `assets/uploads/`** — ya está en `.gitignore`, no commitear fotos
6. **`APP_ENV=production`** — en producción, limpiar automáticamente `assets/uploads/` después de procesar

---

**🇺🇾 Próximo paso: `uv run fleting db make 008_add_ticket_fields`**
