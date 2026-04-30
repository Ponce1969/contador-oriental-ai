# INSTALLMENT_EXPENSES_SPEC.md - Pagos en Cuotas con Tarjeta

> **Change ID**: `feat/credit-card-installments`  
> **Status**: Proposed  
> **Created**: 2026-05-01  
> **Target**: v2.1

## Requirements

### User Story 1: Registrar compra en cuotas (Primary)

**As a** usuario familiar
**I want** registrar una compra hecha con tarjeta de crédito en cuotas
**So that** pueda hacer un seguimiento mes a mes de los pagos pendientes

**Acceptance Criteria:**
- `GIVEN` el usuario está en la vista de gastos
- `WHEN` selecciona "Tarjeta de crédito" como método de pago
- `THEN` se habilita un campo para ingresar:
  - Nombre de la tarjeta (texto libre, ej: "OCA", "Scotia", "Santander")
  - Número de cuotas (1-48)
  - Fecha de vencimiento de la primera cuota
  - **Mes de inicio del pago** (opcional): en Uruguay, la fecha de compra no determina cuándo se paga la primera cuota - depende del cierre de la tarjeta

- `GIVEN` el usuario ingresa una compra en cuotas
- `WHEN` guarda el gasto
- `THEN` el sistema calcula:
  - Monto por cuota: `monto_total / cantidad_cuotas`
  - Fechas de cada cuota: `mes_inicio + i * 30 días` (aproximado)
  - Crea un `InstallmentPurchase` con `total_pagos = cantidad_cuotas`
  - **Vectoriza la compra total** (no las cuotas individuales) con metadato `is_installment: true`
    para que Gemma2:2B pueda responder correctamente a consultas como "¿En qué gasté mucha plata?"

- `GIVEN` hay cuotas pendientes de pago
- `WHEN` el usuario inicia sesión en el mes correspondiente
- `THEN` aparece una notificación/badge con los pagos pendientes del mes

- `GIVEN` una compra en cuotas está registrada
- `WHEN` el usuario paga una cuota
- `THEN` se registra el pago individual como un gasto del mes
- `AND` se actualiza el contador de cuotas restantes

- `GIVEN` todas las cuotas fueron pagadas
- `WHEN` se registra el último pago
- `THEN` el gasto recurrente se marca como completado
- `AND` deja de aparecer en pendientes

### User Story 2: Ver resumen de cuotas pendientes (Secondary)

**As a** usuario familiar
**I want** ver un resumen de todas las compras en cuotas pendientes
**So that** pueda planificar los gastos del mes

**Acceptance Criteria:**
- `GIVEN` el usuario está en la vista principal
- `WHEN` hay compras en cuotas pendientes
- `THEN` se muestra un card con:
  - Total de cuotas a pagar este mes
  - Lista de compras con detalles: comercio, monto cuota, cuotas restantes
  - Tarjeta asociada a cada compra

- `GIVEN` no hay cuotas pendientes
- `WHEN` el usuario está en la vista principal
- `THEN` no se muestra el card de cuotas (o muestra "Sin cuotas pendientes")

### User Story 3: Gestión de tarjetas (Secondary)

**As a** usuario familiar
**I want** gestionar las tarjetas de crédito de la familia
**So that** pueda identificarlas fácilmente al registrar compras

**Acceptance Criteria:**
- `GIVEN` el usuario ingresa tarjetas usadas previamente
- `WHEN` escribe el nombre de la tarjeta en el campo
- `THEN` se sugieren tarjetas ya registradas (autocompletado)

- `GIVEN` no se requiere un catálogo predefinido
- `WHEN` el usuario necesita registrar una tarjeta
- `THEN` puede escribir cualquier nombre (texto libre)
- `AND` las tarjetas usadas se guardan para futuros autocompletados

**Uruguayan Cards (commonly entered):**
- OCA
- Scotia
- Santander
- Itaú
- BBVA
- Brou (BROU)
- BBVA
- Mi dinero (Prex, Mercado Pago)
- Anda
- Crédito de la casa

## Database Changes

### New Table: `installment_purchases`

```sql
CREATE TABLE installment_purchases (
    id SERIAL PRIMARY KEY,

    -- Relación con el gasto original (SET NULL para no perder historial)
    expense_id INTEGER REFERENCES expenses(id) ON DELETE SET NULL,

    -- Multi-tenant
    familia_id INTEGER NOT NULL REFERENCES familias(id),

    -- Datos de la compra
    nombre_tarjeta VARCHAR(50) NOT NULL,    -- ej: "OCA", "Scotia"
    monto_total DECIMAL(12,2) NOT NULL,
    numero_cuotas INTEGER NOT NULL CHECK (numero_cuotas > 0),
    cuotas_pagadas INTEGER NOT NULL DEFAULT 0,
    monto_por_cuota DECIMAL(12,2) NOT NULL,

    -- Fechas
    fecha_compra DATE NOT NULL,
    mes_inicio_pago DATE,                   -- Primer mes de pago (según cierre tarjeta)
    fecha_ultima_cuota DATE,

    -- Estado
    activo BOOLEAN NOT NULL DEFAULT TRUE,    -- FALSE cuando se pagaron todas
    completado BOOLEAN NOT NULL DEFAULT FALSE, -- TRUE cuando se pagaron todas

    -- Metadatos RAG
    vectorizado BOOLEAN NOT NULL DEFAULT FALSE, -- TRUE si ya se vectorizó

    -- Metadatos
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Descripción original de la compra
    descripcion VARCHAR(200),

    CONSTRAINT chk_cuotas_valid CHECK (cuotas_pagadas <= numero_cuotas)
);

CREATE INDEX idx_installments_familia ON installment_purchases(familia_id);
CREATE INDEX idx_installments_activo ON installment_purchases(familia_id, activo)
    WHERE activo = TRUE;
```

### New Table: `installment_payments`

```sql
CREATE TABLE installment_payments (
    id SERIAL PRIMARY KEY,
    installment_purchase_id INTEGER NOT NULL
        REFERENCES installment_purchases(id) ON DELETE CASCADE,

    -- Relación con gasto del mes creado
    expense_id INTEGER REFERENCES expenses(id),

    -- Multi-tenant
    familia_id INTEGER NOT NULL REFERENCES familias(id),

    -- Datos del pago
    numero_cuota INTEGER NOT NULL,           -- 1, 2, 3, ...
    monto_pagado DECIMAL(12,2) NOT NULL,
    fecha_pago DATE NOT NULL,

    -- Metadatos
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_installment_number UNIQUE(installment_purchase_id, numero_cuota)
);

CREATE INDEX idx_installment_payments
    ON installment_payments(installment_purchase_id);
```

## Model Changes (models/categories.py)

### New Enum: `CreditCard`

```python
class CardType(str, Enum):
    """Tipos de tarjetas usadas en Uruguay"""
    OCA = "OCA"
    SCOTIA = "Scotia"
    SANTANDER = "Santander"
    ITAU = "Itaú"
    BBVA = "BBVA"
    BROU = "BROU"
    ANDA = "Anda"
    PREX = "Prex"
    MERCADO_PAGO = "Mercado Pago"
    OTRA = "Otra"
```

## Model Changes (Pydantic)

### New Model: `InstallmentPurchase`

```python
class InstallmentPurchase(BaseModel):
    id: int | None = None
    expense_id: int
    familia_id: int
    nombre_tarjeta: str
    monto_total: float = Field(gt=0)
    numero_cuotas: int = Field(ge=1, le=48)
    cuotas_pagadas: int = 0
    monto_por_cuota: float
    fecha_compra: date
    fecha_primera_cuota: date | None = None
    fecha_ultima_cuota: date | None = None
    activo: bool = True
    completado: bool = False
    descripcion: str
```

### Updated Model: `Expense`

Add new optional field:
```python
installment_id: int | None = None  # FK to installment_purchases
```

## Controller Changes

### New Controller: `InstallmentController`

```python
class InstallmentController(BaseController):
    """Controller para gestión de compras en cuotas"""

    def crear_compra_cuotas(expense, installment_data) -> Result[...]
    def obtener_cuotas_pendientes(familia_id) -> list[InstallmentPurchase]
    def obtener_resumen_mes(familia_id, month, year) -> dict
    def pagar_cuota(installment_purchase_id) -> Result[...]
    def obtener_historial(installment_purchase_id) -> list[InstallmentPayment]
```

## View Changes

### Updated: `ExpensesView` (`views/pages/expenses_view.py`)

**New form fields when "Tarjeta de crédito" is selected:**
- Tarjeta (text input with autocomplete)
- Número de cuotas (dropdown/stepper)
- Fecha de primera cuota (date picker, default: next month)

### New View: `InstallmentsSummaryView` (`views/pages/installments_view.py`)

Displays in the main dashboard:
- Card showing "Cuotas del mes: $X (N compras pendientes)"
- List of each installment with: store, amount, remaining payments, card

## UI Flow

```
Expenses View → "Tarjeta de crédito" selected →
    ↓
    Show: Tarjeta, N° Cuotas, Fecha 1er pago
    ↓
    Save → Creates:
        1. Expense record
        2. InstallmentPurchase record
        3. Monthly Expense records (scheduled)
    ↓
Dashboard → Shows "Pagos del mes" card
    ↓
    User clicks → Pay → Creates payment record
```

## Implementation Tasks

- [x] **T1**: Add `installment_purchases` and `installment_payments` tables (migration via `fleting db make`)
- [x] **T2**: Create `InstallmentPurchase` and `InstallmentPayment` Pydantic models in `models/`
- [x] **T3**: Create `InstallmentRepository` and `InstallmentPaymentRepository` in `repositories/`
- [x] **T4**: Create `InstallmentService` in `services/domain/`
- [x] **T5**: Create `InstallmentController` in `controllers/`
- [ ] **T6**: Update `ExpensesView` to show installment fields when credit card selected
- [ ] **T7**: Create `InstallmentsSummaryView` for dashboard
- [ ] **T8**: Add endpoint for getting pending installments (use in dashboard)
- [ ] **T9**: Add monthly notification about pending payments
- [ ] **T10**: Update `AGENTS.md` and spec files to document new feature
- [x] **T11**: Write tests for installment creation, payment, and summary

## RAG Considerations for Gemma2:2B

### Vectorization Strategy

**Do NOT vectorize individual installments.** Only vectorize the parent purchase:

```python
# ✅ CORRECTO - Vectoriza la compra total
embedding_text = f"Compra en cuotas: {descripcion} - Total: ${monto_total} en {numero_cuotas} cuotas"
metadata = {"is_installment": True, "total_amount": monto_total}

# ❌ INCORRECTO - Esto genera 12 vectores pequeños que confunden al RAG
# for i in range(numero_cuotas):
#     embedding_text = f"Cuota {i+1}: ${monto_por_cuota}"
```

**Why:** When the user asks "¿En qué gasté mucha plata?", the RAG should find the original $12,000 purchase, not 12 small $1,000 entries.

### Gemma2:2B Limitations

1. **No math**: Gemma2 doesn't calculate anything - Python does all calculations
2. **Only receives total**: Receives the pre-computed summary, not raw installment data
3. **Embedding model**: Uses nomic-embed-text for vectorization, Gemma2 only for chat responses

### Metadata Filtering

When querying RAG for expenses:
- Filter out individual installment payments
- Only show parent purchases with `is_installment: True`
- Aggregate installment totals in Python before passing to Gemma2

## Uruguayan Card Billing Cycles

### Cierre de Tarjeta

In Uruguay, purchases are billed according to the card's closing date:

- **Purchase date**: The day you buy
- **Closing date**: The day the card statement closes (varies by bank)
- **Payment date**: Usually 10-15 days after closing

**Example:**
- Buy on May 15 with Scotia card (closes on day 10)
- First installment: July payment (closes June 10, pays July)

**Implementation:** `mes_inicio_pago` field allows user to specify which month the first payment is due, rather than assuming the next month automatically.
