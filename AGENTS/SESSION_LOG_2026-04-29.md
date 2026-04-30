# Session Summary — 28/04/2026

## Goal
Credit card installment tracking system (Uruguay-specific)

## Completed

### Database
- Migration `010_add_installment_system` — 2 tables: `installment_purchases` + `installment_payments`
- FK: `expenses.installment_purchase_id` → `installment_purchases(id) ON DELETE SET NULL`
- SQLAlchemy: `Numeric(12,2)` for all monetary columns
- Indexes: `idx_installments_familia`, `idx_installments_activo`, `idx_payments_purchase`

### Models (Pydantic)
- `models/installment_model.py` — `InstallmentPurchase`, `InstallmentPayment`, `InstallmentSummary`
- `models/expense_model.py` — added `installment_purchase_id: int | None`
- `models/categories.py` — OTROS icon changed from 💳 to 📦

### Architecture (All `Decimal`, zero `float`)
- `models/installment_model.py` — `Decimal` for all monetary fields
- `database/tables.py` — `Numeric(12,2)` → `Mapped[Decimal]`
- `services/infrastructure/formatters.py` — `format_pesos(Decimal) → "$ 18.480"`
- `services/domain/installment_service.py` — ROUND_DOWN primer N-1 cuotas + residuo en última
- `services/ai/memory_event_handler.py` — `_formatear_compra_cuotas()` con `format_pesos`
- `views/pages/expenses_view.py` — import `Decimal`, switch auto/manual, formateo

### Controllers
- `controllers/installment_controller.py` — CRUD + event `COMPRA_CUOTAS_CREADA`
- Updated `controllers/expense_controller.py` — events include installment context

### Events
- `core/events.py` — `EventType.COMPRA_CUOTAS_CREADA`, `EventType.CUOTA_PAGADA`
- `main.py` — `event_system.subscribe(EventType.COMPRA_CUOTAS_CREADA, ...)`

### UI — ExpensesView
- Switch "Cálculo automático" (ON: Total/N, OFF: Cuota×N)
- Monto por cuota auto-calculado (read_only ON) o manual (OFF)
- Label de interés: "Total financiado: $ 1.440 (+$ 445 de interés)" en rojo
- Meses dinámicos desde el actual
- OCR button moved to top right (was FAB covering delete)
- Format uruguayo: `$ 12.990` (sin decimales, punto separador)

### Tests
- `tests/test_installment_service.py` — 6 tests passing

### Key design decisions
- ON DELETE SET NULL (not CASCADE) for expense_id in installment_purchases
- Vectorize TOTAL purchase, not individual cuotas (RAG-safe for Gemma2:2B)
- Gemma2:2B does NO math — all calculations in Python/Decimal
- uruguayan card billing: `mes_inicio_pago` field for closing date flexibility

## Next Steps (for tomorrow)

1. **Dashboard "Awareness"**: Card showing "Cuotas del mes: $ X"
   - File: `views/pages/dashboard_view.py`
   - Method: `InstallmentController.obtener_cuotas_pendientes()`

2. **"Mis Planes" View**: New `views/pages/planes_view.py`
   - Progress bars per compra: ████░░░░ 3/24
   - List of all active installment purchases

3. **Lógica de inicio de mes**: `InstallmentController.generar_gastos_programados()`
   - Auto-creates `expense` with `pendiente=True` for each cuota due this month
   - Triggered on first access of the month

4. **Análisis predictivo**: `InstallmentService.proyectar_meses(familia_id, meses=6)`
   - Projects future cuota payments for AI advice
   - Update `ai_advisor_service.py` prompt with projection context

## Key files changed
- `views/pages/expenses_view.py` — major UI restructure (cuotas section)
- `services/domain/installment_service.py` — Decimal arithmetic + residuo
- `database/tables.py` — Numeric(12,2) + new tables
- `models/installment_model.py` — Decimal models
- `controllers/installment_controller.py` — events + expense_repo passthrough
- `services/ai/memory_event_handler.py` — cuotas formatter
- `services/infrastructure/formatters.py` — new module
- `core/events.py` — new event types
- `main.py` — COMPRA_CUOTAS_CREADA subscription
- `docker-compose.yml` — added ports: 8550:8550
- `migrations/010_add_installment_system.py`
- `tests/test_installment_service.py`

## Docker
- containers: `auditor_familiar_app` (8550), `auditor_familiar_db` (5432)
- model: `contador-oriental` (gemma2:2b + Modelfile)
- rebuild: `docker compose build app && docker compose up -d app`
