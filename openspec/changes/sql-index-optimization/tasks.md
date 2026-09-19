# Tareas de Implementación: Optimización de Índices SQL

## Fase 1: Creación de Migración
- [x] Crear archivo de migración `migrations/026_drop_redundant_indexes.py`.
- [x] Implementar `upgrade()` con `DROP INDEX IF EXISTS` para los 10 índices redundantes:
  - `idx_snapshots_familia_periodo`
  - `idx_password_reset_tokens_token`
  - `idx_payments_purchase`
  - `idx_installments_familia`
  - `idx_exchange_rate_date`
  - `idx_ai_usage_lookup`
  - `idx_household_members_household`
  - `idx_invitations_token`
  - `idx_shared_links_household`
  - `idx_settlements_household`
- [x] Implementar `downgrade()` con sentencias `CREATE INDEX IF NOT EXISTS` para garantizar rollback limpio.

## Fase 2: Actualización de Modelos SQLAlchemy
- [x] Revisar y remover declaraciones `index=True` o `Index(...)` redundantes en:
  - `models/monthly_snapshot.py` (o correspondiente)
  - `models/password_reset_token.py`
  - `models/installment.py`
  - `models/exchange_rate.py`
  - `models/ai_usage.py`
  - `models/household.py`
- [x] Asegurar coherencia entre los modelos de SQLAlchemy y la base de datos física.

## Fase 3: Ejecución y Validación
- [x] Ejecutar el runner de migraciones (`python migrate_legacy.py` o script de migración correspondiente).
- [x] Re-ejecutar el auditor `python C:\Users\cerra\codigo\Herraminetas_Sql\audit_pg.py` contra `auditor_familiar` y verificar que el conteo de índices redundantes baje a 0.
- [x] Ejecutar la suite de pruebas del proyecto (`pytest`) para garantizar que todas las consultas y filtros sigan funcionando con el mismo rendimiento y sin fallos.
