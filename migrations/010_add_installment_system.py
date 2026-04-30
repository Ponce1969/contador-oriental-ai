"""
Migration: add_installment_system
Created at: 2026-04-28T21:03:53.937247
Adds credit card installment tracking tables.
"""


def up(db):
    # Tabla principal de compras en cuotas
    db.execute("""
        CREATE TABLE IF NOT EXISTS installment_purchases (
            id SERIAL PRIMARY KEY,
            expense_id INTEGER REFERENCES expenses(id),
            familia_id INTEGER NOT NULL REFERENCES familias(id),
            nombre_tarjeta VARCHAR(50) NOT NULL,
            monto_total DECIMAL(12,2) NOT NULL,
            numero_cuotas INTEGER NOT NULL CHECK (numero_cuotas > 0),
            cuotas_pagadas INTEGER NOT NULL DEFAULT 0,
            monto_por_cuota DECIMAL(12,2) NOT NULL,
            fecha_compra DATE NOT NULL,
            mes_inicio_pago DATE,
            fecha_ultima_cuota DATE,
            activo BOOLEAN NOT NULL DEFAULT TRUE,
            completado BOOLEAN NOT NULL DEFAULT FALSE,
            vectorizado BOOLEAN NOT NULL DEFAULT FALSE,
            descripcion VARCHAR(200),
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_cuotas_valid CHECK (cuotas_pagadas <= numero_cuotas)
        )
    """)

    # Tabla de pagos individuales de cada cuota
    db.execute("""
        CREATE TABLE IF NOT EXISTS installment_payments (
            id SERIAL PRIMARY KEY,
            installment_purchase_id INTEGER NOT NULL
                REFERENCES installment_purchases(id) ON DELETE CASCADE,
            expense_id INTEGER REFERENCES expenses(id),
            familia_id INTEGER NOT NULL REFERENCES familias(id),
            numero_cuota INTEGER NOT NULL,
            monto_pagado DECIMAL(12,2) NOT NULL,
            fecha_pago DATE NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_installment_number
                UNIQUE(installment_purchase_id, numero_cuota)
        )
    """)

    # Índices para consultas rápidas
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_installments_familia
            ON installment_purchases(familia_id)
    """)

    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_installments_activo
            ON installment_purchases(familia_id, activo)
            WHERE activo = TRUE
    """)

    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_payments_purchase
            ON installment_payments(installment_purchase_id)
    """)

    # Agregar columna installment_id a expenses (opcional, para trazabilidad)
    db.execute("""
        ALTER TABLE expenses
            ADD COLUMN IF NOT EXISTS installment_purchase_id INTEGER
            REFERENCES installment_purchases(id) ON DELETE SET NULL
    """)


def down(db):
    # Revertir cambios
    db.execute("ALTER TABLE expenses DROP COLUMN IF EXISTS installment_purchase_id")
    db.execute("DROP TABLE IF EXISTS installment_payments")
    db.execute("DROP TABLE IF EXISTS installment_purchases")
