"""
Migración 002 - Sistema multi-usuario
Agregar tablas de familias y usuarios, y campo familia_id a tablas existentes
"""
from sqlalchemy import text

from configs.database_config import DatabaseConfig


def up(db):
    """Crear sistema multi-usuario"""
    
    is_postgres = DatabaseConfig.is_postgresql()
    
    # Tabla de familias
    if is_postgres:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS familias (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE,
                activo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS familias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT UNIQUE,
                activo BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
    
    # Tabla de usuarios
    if is_postgres:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                familia_id INTEGER NOT NULL,
                username VARCHAR(100) NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                nombre_completo VARCHAR(200),
                activo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                FOREIGN KEY (familia_id) REFERENCES familias (id)
            )
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                familia_id INTEGER NOT NULL,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                nombre_completo TEXT,
                activo BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                FOREIGN KEY (familia_id) REFERENCES familias (id)
            )
        """))
    
    # Agregar familia_id a family_members (solo si no existe)
    if is_postgres:
        db.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='family_members' AND column_name='familia_id'
                ) THEN
                    ALTER TABLE family_members ADD COLUMN familia_id INTEGER DEFAULT 1;
                END IF;
            END $$;
        """))
    else:
        # SQLite no tiene IF NOT EXISTS para columnas, intentar y capturar error
        try:
            db.execute(text("ALTER TABLE family_members ADD COLUMN familia_id INTEGER DEFAULT 1"))
        except:
            pass
    
    # Agregar familia_id a incomes (solo si no existe)
    if is_postgres:
        db.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='incomes' AND column_name='familia_id'
                ) THEN
                    ALTER TABLE incomes ADD COLUMN familia_id INTEGER DEFAULT 1;
                END IF;
            END $$;
        """))
    else:
        try:
            db.execute(text("ALTER TABLE incomes ADD COLUMN familia_id INTEGER DEFAULT 1"))
        except:
            pass
    
    # Agregar familia_id a expenses (solo si no existe)
    if is_postgres:
        db.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='expenses' AND column_name='familia_id'
                ) THEN
                    ALTER TABLE expenses ADD COLUMN familia_id INTEGER DEFAULT 1;
                END IF;
            END $$;
        """))
    else:
        try:
            db.execute(text("ALTER TABLE expenses ADD COLUMN familia_id INTEGER DEFAULT 1"))
        except:
            pass
    
    # Crear familia por defecto para datos existentes (solo si no existe)
    if is_postgres:
        db.execute(text("""
            INSERT INTO familias (id, nombre, email, activo, created_at)
            VALUES (1, 'Familia Principal', 'admin@loquinto.com', TRUE, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO NOTHING
        """))
    else:
        db.execute(text("""
            INSERT OR IGNORE INTO familias (id, nombre, email, activo, created_at)
            VALUES (1, 'Familia Principal', 'admin@loquinto.com', 1, CURRENT_TIMESTAMP)
        """))
    
    # Crear usuario admin por defecto (password: admin123) (solo si no existe)
    # Hash Argon2 de "admin123"
    if is_postgres:
        db.execute(text("""
            INSERT INTO usuarios (
                familia_id, 
                username, 
                password_hash, 
                nombre_completo, 
                activo,
                created_at
            )
            VALUES (
                1, 
                'admin', 
                '$argon2id$v=19$m=65536,t=2,p=2$Vk3bdOscmtMqKykv35PY7w$1twfwGyx1SoxAV+2aLdgVL4R1ohzR5Btk4S4YjE2ohI',
                'Administrador',
                TRUE,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (username) DO NOTHING
        """))
    else:
        db.execute(text("""
            INSERT OR IGNORE INTO usuarios (
                familia_id, 
                username, 
                password_hash, 
                nombre_completo, 
                activo,
                created_at
            )
            VALUES (
                1, 
                'admin', 
                '$argon2id$v=19$m=65536,t=2,p=2$Vk3bdOscmtMqKykv35PY7w$1twfwGyx1SoxAV+2aLdgVL4R1ohzR5Btk4S4YjE2ohI',
                'Administrador',
                1,
                CURRENT_TIMESTAMP
            )
        """))
    
    print("✅ Sistema multi-usuario creado exitosamente")
    print("   - Tabla familias")
    print("   - Tabla usuarios")
    print("   - Campo familia_id agregado a todas las tablas")
    print("   - Usuario admin creado (username: admin, password: admin123)")


def down(db):
    """Revertir sistema multi-usuario"""
    
    # Eliminar columnas familia_id (SQLite no soporta DROP COLUMN directamente)
    # Necesitaríamos recrear las tablas, por ahora solo eliminamos las nuevas tablas
    
    db.execute(text("DROP TABLE IF EXISTS usuarios"))
    db.execute(text("DROP TABLE IF EXISTS familias"))
    
    print("↩️ Sistema multi-usuario eliminado")
    print("   NOTA: familia_id permanece en tablas existentes (limitación SQLite)")
