"""
Migración 005 - Historial mensual de gastos
Crea tabla monthly_expense_snapshots para comparativa mes a mes.
Permite al Contador Oriental detectar inflación vs descontrol de consumo.
"""
from sqlalchemy import text

from configs.database_config import DatabaseConfig


def up(db):
    """Crear tabla de snapshots mensuales"""

    is_postgres = DatabaseConfig.is_postgresql()

    if is_postgres:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS monthly_expense_snapshots (
                id              SERIAL PRIMARY KEY,
                familia_id      INTEGER NOT NULL,
                anio            INTEGER NOT NULL,
                mes             INTEGER NOT NULL,
                categoria       VARCHAR(100) NOT NULL,
                total_dinero    NUMERIC(12, 2) NOT NULL DEFAULT 0,
                cantidad_compras INTEGER NOT NULL DEFAULT 0,
                ticket_promedio NUMERIC(12, 2) NOT NULL DEFAULT 0,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (familia_id, anio, mes, categoria)
            )
        """))
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_familia_periodo
            ON monthly_expense_snapshots (familia_id, anio, mes)
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS monthly_expense_snapshots (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                familia_id       INTEGER NOT NULL,
                anio             INTEGER NOT NULL,
                mes              INTEGER NOT NULL,
                categoria        TEXT NOT NULL,
                total_dinero     REAL NOT NULL DEFAULT 0,
                cantidad_compras INTEGER NOT NULL DEFAULT 0,
                ticket_promedio  REAL NOT NULL DEFAULT 0,
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (familia_id, anio, mes, categoria)
            )
        """))

    print("✅ Tabla monthly_expense_snapshots creada")
    print("   - Índice por familia_id + anio + mes")
    print("   - UNIQUE (familia_id, anio, mes, categoria) — upsert seguro")


def down(db):
    """Eliminar tabla de snapshots mensuales"""
    db.execute(text("DROP TABLE IF EXISTS monthly_expense_snapshots"))
    print("↩️ Tabla monthly_expense_snapshots eliminada")
