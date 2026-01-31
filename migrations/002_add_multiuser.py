"""
Migración 002 - Sistema multi-usuario
Agregar tablas de familias y usuarios, y campo familia_id a tablas existentes
"""
from sqlalchemy import text


def up(db):
    """Crear sistema multi-usuario"""
    
    # Tabla de familias
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
    
    # Agregar familia_id a family_members
    db.execute(text("""
        ALTER TABLE family_members 
        ADD COLUMN familia_id INTEGER DEFAULT 1
    """))
    
    # Agregar familia_id a incomes
    db.execute(text("""
        ALTER TABLE incomes 
        ADD COLUMN familia_id INTEGER DEFAULT 1
    """))
    
    # Agregar familia_id a expenses
    db.execute(text("""
        ALTER TABLE expenses 
        ADD COLUMN familia_id INTEGER DEFAULT 1
    """))
    
    # Crear familia por defecto para datos existentes
    db.execute(text("""
        INSERT INTO familias (id, nombre, email, activo)
        VALUES (1, 'Familia Principal', 'admin@loquinto.com', 1)
    """))
    
    # Crear usuario admin por defecto (password: admin123)
    # Hash Argon2 de "admin123"
    db.execute(text("""
        INSERT INTO usuarios (
            familia_id, 
            username, 
            password_hash, 
            nombre_completo, 
            activo
        )
        VALUES (
            1, 
            'admin', 
            '$argon2id$v=19$m=65536,t=2,p=2$Vk3bdOscmtMqKykv35PY7w$1twfwGyx1SoxAV+2aLdgVL4R1ohzR5Btk4S4YjE2ohI',
            'Administrador',
            1
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
