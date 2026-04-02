"""
Datos esenciales — se ejecutan SIEMPRE, en cualquier entorno.
Usa ON CONFLICT DO NOTHING para ser idempotente (seguro de re-ejecutar).

Contiene:
- Familia base del sistema (id=1, para que las FKs funcionen)
- Categorías y métodos de pago no requieren tabla propia (son enums en el código)
"""

from __future__ import annotations

from sqlalchemy import text

from database.engine import get_session


def run(db):
    session = get_session()
    try:
        session.execute(
            text("""
            INSERT INTO familias (id, nombre, email, activo, created_at)
            VALUES (1, 'Familia Principal', 'admin@auditor.local', true, NOW())
            ON CONFLICT (id) DO NOTHING
        """)
        )
        session.commit()
        print("  ✅  essential_data: familia base verificada (id=1).")
    except Exception as e:
        session.rollback()
        print(f"  ❌  essential_data error: {e}")
        raise
    finally:
        session.close()
