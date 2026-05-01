# Diseño Técnico: Integración Cotización USD/UYU

## 1. Objetivo

Proveer al usuario la cotización diaria del dólar (USD/UYU) en el header de la app, persistirla para análisis histórico, e inyectarla en el contexto de IA para que el Contador Oriental pueda referirse a ella en consultas macroeconómicas.

## 2. Principios No Negociables

| Principio | Regla |
|-----------|-------|
| **0 FLOATS** | El valor del dólar se maneja como `Decimal` desde la respuesta JSON hasta la UI. |
| **Patrón Result** | Toda llamada externa devuelve `Result[Decimal, AppError]`. |
| **1 petición/día** | Los datos se persisten. Nunca se llama a la API más de una vez por día. |
| **Fallback silencioso** | Si falla la API, se muestra el último valor de la DB con indicador visual. |
| **Sin dependencias nuevas** | Se usa `httpx` que ya existe en el proyecto. |

## 3. Proveedor: exchangerate-api.com

```
GET https://api.exchangerate-api.com/v4/latest/USD
```

**Respuesta esperada:**
```json
{
  "base": "USD",
  "date": "2026-04-30",
  "rates": {
    "UYU": 41.2567,
    "ARS": 1250.50,
    "BRL": 5.89
  }
}
```

**Conversión a Decimal:**
```python
rate = Decimal(str(data["rates"]["UYU"]))  # Decimal("41.2567")
```

> **IMPORTANTE:** Nunca hacer `Decimal(41.2567)` (pasa por float). Siempre `Decimal(str(valor))`.

## 4. Modelo de Datos

### 4.1 Tabla PostgreSQL (Migración)

```sql
CREATE TABLE exchange_rates (
    id SERIAL PRIMARY KEY,
    currency_pair VARCHAR(10) NOT NULL DEFAULT 'USD/UYU',
    rate NUMERIC(10, 4) NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_exchange_rate_date UNIQUE (date)
);

CREATE INDEX idx_exchange_rate_date ON exchange_rates(date DESC);
```

### 4.2 SQLAlchemy Table

```python
class ExchangeRateTable(Base):
    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    currency_pair: Mapped[str] = mapped_column(String(10), default="USD/UYU")
    rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
```

### 4.3 Modelo Pydantic

```python
class ExchangeRate(BaseModel):
    id: int | None = None
    currency_pair: str = "USD/UYU"
    rate: Decimal = Field(gt=0, description="Cotización del dólar")
    date: date
    created_at: datetime = Field(default_factory=datetime.now)
```

## 5. Arquitectura Hexagonal

### 5.1 Servicio: `services/infrastructure/exchange_rate_service.py`

Responsabilidad: Llamar a la API y devolver `Result[Decimal, AppError]`.

```python
class ExchangeRateService:
    _API_URL = "https://api.exchangerate-api.com/v4/latest/USD"
    _TIMEOUT = 10

    async def fetch_rate(self) -> Result[Decimal, AppError]:
        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
                response = await client.get(self._API_URL)
                response.raise_for_status()
                data = response.json()
                rate = Decimal(str(data["rates"]["UYU"]))
                return Ok(rate)
        except (KeyError, json.JSONDecodeError) as e:
            return Err(AppError(message=f"Respuesta inválida de API: {e}"))
        except httpx.HTTPStatusError as e:
            return Err(AppError(message=f"API error {e.response.status_code}"))
        except Exception as e:
            return Err(AppError(message=f"Error consultando dólar: {e}"))
```

### 5.2 Repositorio: `repositories/exchange_rate_repository.py`

Responsabilidad: Persistir y recuperar cotizaciones.

```python
class ExchangeRateRepository(BaseTableRepository[ExchangeRateTable]):
    def get_today(self) -> ExchangeRate | None:
        row = self._filter(ExchangeRateTable.date == date.today()).first()
        return self._to_domain(row) if row else None

    def get_latest(self) -> ExchangeRate | None:
        row = (
            self._filter()
            .order_by(ExchangeRateTable.date.desc())
            .first()
        )
        return self._to_domain(row) if row else None

    def save(self, rate: Decimal, rate_date: date) -> ExchangeRate:
        table = ExchangeRateTable(
            rate=rate,
            date=rate_date,
            currency_pair="USD/UYU",
        )
        self.session.add(table)
        self.session.flush()
        return self._to_domain(table)
```

### 5.3 Script de actualización: `scripts/update_exchange_rate.py`

Responsabilidad: Job independiente ejecutado por cron (1 vez al día).

```bash
# Cron (ejecutar a las 9:00 AM todos los días)
0 9 * * * cd /opt/contador-oriental && uv run python scripts/update_exchange_rate.py
```

```python
async def main():
    service = ExchangeRateService()
    result = await service.fetch_rate()
    if isinstance(result, Ok):
        with get_db_session() as session:
            repo = ExchangeRateRepository(session)
            existing = repo.get_today()
            if not existing:
                repo.save(result.ok(), date.today())
                print(f"Cotización guardada: {result.ok()}")
            else:
                print(f"Ya existe cotización para hoy: {existing.rate}")
    else:
        print(f"Error: {result.err().message}")
        sys.exit(1)
```

### 5.4 Controlador/Provider para UI: `controllers/exchange_rate_controller.py`

Responsabilidad: Proveer a la UI el valor del día con lógica de fallback.

```python
class ExchangeRateController:
    def __init__(self):
        self.service = ExchangeRateService()

    def get_display_rate(self) -> tuple[Decimal, bool]:
        """
        Retorna (rate, es_fresh).
        es_fresh=True si es del día de hoy.
        es_fresh=False si es fallback (día anterior o más viejo).
        """
        with get_db_session() as session:
            repo = ExchangeRateRepository(session)
            today = repo.get_today()
            if today:
                return today.rate, True
            latest = repo.get_latest()
            if latest:
                return latest.rate, False
        return Decimal("0"), False
```

## 6. Integración con UI

### 6.1 Ubicación

`views/layouts/main_layout.py` — entre el `AppBar` y el contenido principal, centrado.

### 6.2 Componente Flet

```python
def _exchange_rate_badge(self) -> ft.Control | None:
    rate, is_fresh = self._exchange_controller.get_display_rate()
    if rate == Decimal("0"):
        return None  # Sin datos, no mostrar nada

    color = ft.Colors.LIGHT_BLUE_300 if is_fresh else ft.Colors.AMBER_400
    icon = ft.Icons.TRENDING_UP if is_fresh else ft.Icons.WARNING_AMBER
    label = f"U$S 1.00 = $U {rate}"

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(icon, size=14, color=color),
                ft.Text(
                    label,
                    size=12,
                    color=ft.Colors.with_opacity(0.85, ft.Colors.ON_SURFACE),
                    weight=ft.FontWeight.W_500,
                ),
            ],
            spacing=4,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=12, vertical=4),
        bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.SURFACE_VARIANT),
        border_radius=20,
        alignment=ft.alignment.center,
    )
```

**Comportamiento:**
- **Fresh** (cotización de hoy): Icono `TRENDING_UP` en celeste suave.
- **Stale** (fallback, día anterior): Icono `WARNING_AMBER` en ámbar + tooltip "Última cotización disponible".
- **Sin datos**: El badge desaparece completamente para no mostrar basura.

### 6.3 Posición en Layout

Se inserta entre `_top_bar()` y el contenido principal:

```python
# En MainLayout._build():
self.controls.append(self._top_bar())
self.controls.append(self._exchange_rate_badge())  # <- NUEVO
# ... resto del contenido
```

## 7. Integración con IA (AIContext)

### 7.1 Modelo

```python
class AIContext(BaseModel):
    # ... campos existentes ...
    cotizacion_dolar: Decimal | None = Field(
        default=None,
        description="Cotización USD/UYU del día para contexto macroeconómico",
    )
```

### 7.2 Construcción del contexto

En `AIController._construir_contexto()`:

```python
from controllers.exchange_rate_controller import ExchangeRateController

# ...
exchange_ctrl = ExchangeRateController()
rate, _ = exchange_ctrl.get_display_rate()

return AIContext(
    # ... campos existentes ...
    cotizacion_dolar=rate if rate > 0 else None,
)
```

### 7.3 Prompt para Gemma

En `AIAdvisorService._formatear_datos_financieros()`:

```python
if ctx.cotizacion_dolar:
    lineas.append(
        f"- Cotización del dólar hoy: $U {ctx.cotizacion_dolar} por U$S 1.00"
    )
```

**Regla de negocio:** Si el usuario pregunta por "inflación", "precios", "dólar" o "tipo de cambio", Gemma puede usar este valor para contextualizar el poder adquisitivo.

## 8. Manejo de Errores (Fallback)

```
Flujo:
1. UI pide cotización → va al Controller
2. Controller consulta DB: ¿hay cotización de hoy?
   ├── Sí → Devuelve (rate, True)  [verde/celeste]
   └── No → Consulta última disponible
       ├── Sí → Devuelve (rate, False) [ámbar + warning]
       └── No → Devuelve (0, False) → UI oculta badge
3. Si API falla → Solo afecta al script cron. La UI sigue funcionando con fallback.
```

**Nunca se bloquea la app** por un error de API externa.

## 9. Migración

### 9.1 Archivo: `migrations/012_add_exchange_rates.py`

```python
def up(db):
    db.execute("""
        CREATE TABLE exchange_rates (
            id SERIAL PRIMARY KEY,
            currency_pair VARCHAR(10) NOT NULL DEFAULT 'USD/UYU',
            rate NUMERIC(10, 4) NOT NULL,
            date DATE NOT NULL DEFAULT CURRENT_DATE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_exchange_rate_date UNIQUE (date)
        )
    """)
    db.execute("""
        CREATE INDEX idx_exchange_rate_date ON exchange_rates(date DESC)
    """)

def down(db):
    db.execute("DROP TABLE IF EXISTS exchange_rates")
```

## 10. Archivos a Crear/Modificar

| Acción | Archivo |
|--------|---------|
| **Crear** | `migrations/012_add_exchange_rates.py` |
| **Crear** | `models/exchange_rate_model.py` |
| **Crear** | `services/infrastructure/exchange_rate_service.py` |
| **Crear** | `repositories/exchange_rate_repository.py` |
| **Crear** | `controllers/exchange_rate_controller.py` |
| **Crear** | `scripts/update_exchange_rate.py` |
| **Modificar** | `database/tables.py` — agregar `ExchangeRateTable` |
| **Modificar** | `models/ai_model.py` — agregar `cotizacion_dolar` a `AIContext` |
| **Modificar** | `controllers/ai_controller.py` — inyectar cotización en contexto |
| **Modificar** | `services/ai/ai_advisor_service.py` — mostrar cotización en prompt |
| **Modificar** | `views/layouts/main_layout.py` — badge de cotización en header |

## 11. Testing

```python
# tests/test_exchange_rate_service.py
async def test_fetch_rate_devuelve_decimal():
    service = ExchangeRateService()
    result = await service.fetch_rate()
    assert isinstance(result, Ok)
    assert isinstance(result.ok(), Decimal)
    assert result.ok() > Decimal("30")  # El dólar nunca estuvo tan bajo en UY
```

---

## 12. Checklist de Implementación

- [ ] Tabla `exchange_rates` creada en migración
- [ ] `ExchangeRateTable` agregado a `database/tables.py`
- [ ] `ExchangeRate` modelo Pydantic creado
- [ ] `ExchangeRateService` con `Result[Decimal, AppError]`
- [ ] `ExchangeRateRepository` con `get_today()` y `get_latest()`
- [ ] `ExchangeRateController` con lógica de fallback
- [ ] Badge en `MainLayout` con colores suaves
- [ ] `AIContext` incluye `cotizacion_dolar`
- [ ] `AIController` inyecta cotización
- [ ] `AIAdvisorService` muestra cotización en prompt
- [ ] Script `update_exchange_rate.py` funcional
- [ ] Tests unitarios pasan
- [ ] **0 floats** en todo el módulo (verificar con `audit_project.py`)

---

*Diseñado para: Contador Oriental v0.1.0*
*API: exchangerate-api.com (sin key, httpx nativo)*
*Precisión: Decimal(10,4) — ni un float a la vista*
