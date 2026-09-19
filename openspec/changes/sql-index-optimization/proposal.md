# Propuesta de Optimización: Eliminación de Índices Redundantes en PostgreSQL

**Fecha:** 2026-09-18  
**Origen:** Auditoría de Índices y Almacenamiento con `PostgresHealthAuditor`  
**Proyecto:** Auditor Familiar / Contador Oriental (`flet`)  
**Base de Datos:** PostgreSQL (`auditor_familiar`)

---

## 1. Contexto y Diagnóstico

Durante el diagnóstico de rendimiento de almacenamiento y balance Lectura/Escritura (Read/Write) realizado sobre la base de datos `auditor_familiar`, se identificaron **10 índices B-Tree redundantes**.

### Problemas identificados a bajo nivel:
1. **Doble índice por restricción UNIQUE + índice explícito:**  
   En PostgreSQL, declarar un constraint `UNIQUE` crea automáticamente un índice B-Tree subyacente. Declarar adicionalmente un `CREATE INDEX` sobre la misma columna genera dos árboles idénticos para el mismo dato.
2. **Índices de prefijo cubiertos por índices compuestos:**  
   Un índice simple `(A)` o compuesto `(A, B)` es técnicamente redundante cuando ya existe un índice `(A, B, C)`. En PostgreSQL, el árbol B-Tree evalúa de izquierda a derecha; por lo tanto, cualquier consulta que filtre por el prefijo izquierdo ya queda cubierta por el índice más amplio.
3. **Penalización en escrituras y WAL (Write-Ahead Logging):**  
   Cada instrucción `INSERT`, `UPDATE` o `DELETE` sobre las tablas afectadas obliga al motor a insertar/actualizar punteros en múltiples árboles de índices simultáneamente, aumentando el volumen de WAL y la presión sobre el `autovacuum`.

---

## 2. Índices Redundantes Detectados

| Tabla | Índice Redundante | Índice Cubridor / Existente | Motivo de Redundancia |
|---|---|---|---|
| `monthly_expense_snapshots` | `idx_snapshots_familia_periodo` `(familia_id, anio, mes)` | `monthly_expense_snapshots_familia_id_anio_mes_categoria_key` `(familia_id, anio, mes, categoria)` | Prefijo cubierto por constraint UNIQUE |
| `password_reset_tokens` | `idx_password_reset_tokens_token` `(token)` | `password_reset_tokens_token_key` `(token)` | Duplicado exacto de constraint UNIQUE |
| `installment_payments` | `idx_payments_purchase` `(installment_purchase_id)` | `uq_installment_number` `(installment_purchase_id, numero_cuota)` | Prefijo cubierto por constraint UNIQUE |
| `installment_purchases` | `idx_installments_familia` `(familia_id)` | `idx_installments_activo` `(familia_id, estado)` | Prefijo cubierto por índice compuesto |
| `exchange_rates` | `idx_exchange_rate_date` `(date DESC)` | `uq_exchange_rate_date` `(date)` | Duplicado de constraint UNIQUE |
| `ai_usage` | `idx_ai_usage_lookup` `(familia_id, date)` | `uq_ai_usage_daily` `(familia_id, date, request_type)` | Prefijo cubierto por constraint UNIQUE |
| `household_members` | `idx_household_members_household` `(household_id)` | `uq_household_member` `(household_id, user_id)` | Prefijo cubierto por constraint UNIQUE |
| `household_invitations` | `idx_invitations_token` `(token)` | `household_invitations_token_key` `(token)` | Duplicado exacto de constraint UNIQUE |
| `shared_expense_links` | `idx_shared_links_household` `(household_id)` | `uq_household_gasto_link` `(household_id, gasto_id)` | Prefijo cubierto por constraint UNIQUE |
| `household_settlements` | `idx_settlements_household` `(household_id)` | `idx_settlements_fecha` `(household_id, fecha)` | Prefijo cubierto por índice compuesto |

---

## 3. Alcance de la Refactorización

1. **Migración de Base de Datos (`026_drop_redundant_indexes.py`):**
   - Ejecución de sentencias `DROP INDEX IF EXISTS` para los 10 índices redundantes.
   - Definición de función reversa `downgrade` recreando los índices en caso de rollback.

2. **Alineación de Modelos SQLAlchemy (`models/`):**
   - Eliminar `index=True` o definiciones de `Index(...)` superfluas en los modelos para evitar que futuras migraciones o `create_all()` vuelvan a generarlos.

3. **Verificación y Auditoría Post-Migración:**
   - Re-ejecutar `audit_pg.py` desde `Herraminetas_Sql` confirmando 0 índices redundantes detectados.
   - Ejecutar la suite de tests unitarios del proyecto para asegurar que no hay regresiones funcionales.
