# Propuesta: Indexación de Foreign Keys Críticas (Unindexed FKs)

**Fecha:** 2026-09-24  
**Origen:** Auditoría Determinista de Salud PostgreSQL con `mcp_pg_auditor`  
**Proyecto:** Auditor Familiar / Contador Oriental (`flet`)  
**Base de Datos:** PostgreSQL 16 (`auditor_familiar`)

---

## 1. Contexto y Diagnóstico

Durante el diagnóstico de bloqueos y concurrencia realizado sobre la base de datos `auditor_familiar`, se detectaron **10 Foreign Keys sin índice B-Tree secundario que cubra su prefijo izquierdo**.

### Impacto en Producción:
1. **Bloqueos severos en Cascadas y `ON DELETE SET NULL`:**  
   Varios constraints están definidos con `ON DELETE SET NULL`. Sin índice en la tabla hija, borrar o reasignar una entidad padre (ej. `family_members`, `familias`, `expenses`) fuerza un Sequential Scan completo bloqueando la tabla hija con `SHARE ROW EXCLUSIVE`.
2. **Consultas analíticas lentas:**  
   Cruzar actividades económicas por miembro, cuotas por gasto o aportes por miembro se degrada progresivamente a medida que el volumen de transacciones crece.

---

## 2. Foreign Keys No Indizadas Detectadas

| Tabla Hija | Columna FK | Tabla Padre | Acción On Delete | Constraint |
|---|---|---|---|---|
| `economic_activities` | `family_member_id` | `family_members(id)` | RESTRICT/NO ACTION | `economic_activities_family_member_id_fkey` |
| `expenses` | `installment_purchase_id` | `installment_purchases(id)` | `SET NULL` | `expenses_installment_purchase_id_fkey` |
| `household_invitations` | `accepted_by_familia_id` | `familias(id)` | `SET NULL` | `household_invitations_accepted_by_familia_id_fkey` |
| `incomes` | `economic_activity_id` | `economic_activities(id)` | `SET NULL` | `incomes_economic_activity_id_fkey` |
| `incomes` | `family_member_id` | `family_members(id)` | RESTRICT/NO ACTION | `incomes_family_member_id_fkey` |
| `installment_payments` | `expense_id` | `expenses(id)` | RESTRICT/NO ACTION | `installment_payments_expense_id_fkey` |
| `installment_payments` | `familia_id` | `familias(id)` | RESTRICT/NO ACTION | `installment_payments_familia_id_fkey` |
| `installment_purchases` | `expense_id` | `expenses(id)` | RESTRICT/NO ACTION | `installment_purchases_expense_id_fkey` |
| `savings_goal_contributions` | `family_member_id` | `family_members(id)` | `SET NULL` | `savings_goal_contributions_family_member_id_fkey` |
| `usuarios` | `familia_id` | `familias(id)` | RESTRICT/NO ACTION | `usuarios_familia_id_fkey` |

---

## 3. Plan de Remediación

### DDL Concurrente (Zero-Downtime):
```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_economic_activities_family_member_id 
    ON economic_activities (family_member_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_expenses_installment_purchase_id 
    ON expenses (installment_purchase_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_household_invitations_accepted_by_familia_id 
    ON household_invitations (accepted_by_familia_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incomes_economic_activity_id 
    ON incomes (economic_activity_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incomes_family_member_id 
    ON incomes (family_member_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_installment_payments_expense_id 
    ON installment_payments (expense_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_installment_payments_familia_id 
    ON installment_payments (familia_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_installment_purchases_expense_id 
    ON installment_purchases (expense_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_savings_contributions_family_member_id 
    ON savings_goal_contributions (family_member_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_usuarios_familia_id 
    ON usuarios (familia_id);
```

### Tareas:
- [ ] Crear migración Alembic en `migrations/versions/` ejecutando los índices concurrentemente.
- [ ] Actualizar modelos SQLAlchemy (`models/`) agregando `index=True` a las relaciones ForeignKey correspondientes.
- [ ] Validar con `uv run mcp_pg_auditor.py --cli` que el conteo de `Unindexed Foreign Keys` baje a 0.
