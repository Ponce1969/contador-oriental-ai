"""
Migración inicial - Crear tablas de familia, ingresos y gastos
"""
from sqlalchemy import text

from configs.database_config import DatabaseConfig


def up(db):
    """Crear las tablas iniciales del sistema"""
    
    is_postgres = DatabaseConfig.is_postgresql()
    
    # Tabla de miembros de familia
    if is_postgres:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS family_members (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(200) NOT NULL,
                tipo_ingreso VARCHAR(50) NOT NULL,
                sueldo_mensual NUMERIC(10, 2),
                notas TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS family_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                tipo_ingreso TEXT NOT NULL,
                sueldo_mensual REAL,
                notas TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
    
    # Tabla de ingresos
    if is_postgres:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS incomes (
                id SERIAL PRIMARY KEY,
                family_member_id INTEGER NOT NULL,
                monto NUMERIC(10, 2) NOT NULL,
                fecha DATE NOT NULL,
                categoria VARCHAR(100) NOT NULL,
                descripcion TEXT NOT NULL,
                es_recurrente BOOLEAN DEFAULT FALSE,
                frecuencia_recurrencia VARCHAR(50),
                notas TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (family_member_id) REFERENCES family_members (id)
            )
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS incomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_member_id INTEGER NOT NULL,
                monto REAL NOT NULL,
                fecha DATE NOT NULL,
                categoria TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                es_recurrente BOOLEAN DEFAULT 0,
                frecuencia_recurrencia TEXT,
                notas TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (family_member_id) REFERENCES family_members (id)
            )
        """))
    
    # Tabla de gastos
    if is_postgres:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
                descripcion TEXT NOT NULL,
                monto NUMERIC(10, 2) NOT NULL,
                fecha DATE NOT NULL,
                categoria VARCHAR(100) NOT NULL,
                subcategoria VARCHAR(100),
                metodo_pago VARCHAR(50) NOT NULL,
                es_recurrente BOOLEAN DEFAULT FALSE,
                frecuencia_recurrencia VARCHAR(50),
                notas TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descripcion TEXT NOT NULL,
                monto REAL NOT NULL,
                fecha DATE NOT NULL,
                categoria TEXT NOT NULL,
                subcategoria TEXT,
                metodo_pago TEXT NOT NULL,
                es_recurrente BOOLEAN DEFAULT 0,
                frecuencia_recurrencia TEXT,
                notas TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
    
    print("✅ Tablas creadas exitosamente")


def down(db):
    """Revertir la migración - eliminar tablas"""
    db.execute(text("DROP TABLE IF EXISTS expenses"))
    db.execute(text("DROP TABLE IF EXISTS incomes"))
    db.execute(text("DROP TABLE IF EXISTS family_members"))
    
    print("↩️ Tablas eliminadas")
