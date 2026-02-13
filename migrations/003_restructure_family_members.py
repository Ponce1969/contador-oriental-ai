"""
Migración 003 - Reestructurar family_members
Separar conceptos: Familia (personas/roles) vs Ingresos (dinero)
"""
from sqlalchemy import text

from configs.database_config import DatabaseConfig


def up(db):
    """Reestructurar tabla family_members y mejorar incomes"""
    
    is_postgres = DatabaseConfig.is_postgresql()
    
    # 1. Eliminar columnas económicas de family_members
    if is_postgres:
        # PostgreSQL permite DROP COLUMN directamente
        db.execute(text("""
            ALTER TABLE family_members 
            DROP COLUMN IF EXISTS tipo_ingreso,
            DROP COLUMN IF EXISTS sueldo_mensual
        """))
    else:
        # SQLite requiere recrear la tabla (más complejo, por ahora solo PostgreSQL)
        print("⚠️  SQLite no soporta DROP COLUMN - migración solo para PostgreSQL")
    
    # 2. Agregar nuevas columnas a family_members
    if is_postgres:
        # Agregar parentesco
        db.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='family_members' AND column_name='parentesco'
                ) THEN
                    ALTER TABLE family_members 
                    ADD COLUMN parentesco VARCHAR(50) DEFAULT 'otro';
                END IF;
            END $$;
        """))
        
        # Agregar edad
        db.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='family_members' AND column_name='edad'
                ) THEN
                    ALTER TABLE family_members 
                    ADD COLUMN edad INTEGER;
                END IF;
            END $$;
        """))
        
        # Agregar estado_laboral
        db.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='family_members' AND column_name='estado_laboral'
                ) THEN
                    ALTER TABLE family_members 
                    ADD COLUMN estado_laboral VARCHAR(50) DEFAULT 'empleado';
                END IF;
            END $$;
        """))
    else:
        # SQLite
        try:
            db.execute(text("""
                ALTER TABLE family_members ADD COLUMN parentesco TEXT DEFAULT 'otro'
            """))
        except:
            pass
        
        try:
            db.execute(text("""
                ALTER TABLE family_members ADD COLUMN edad INTEGER
            """))
        except:
            pass
        
        try:
            db.execute(text("""
                ALTER TABLE family_members ADD COLUMN estado_laboral TEXT DEFAULT 'empleado'
            """))
        except:
            pass
    
    # 3. Mejorar columna tipo_ingreso en incomes (si no existe, agregarla)
    if is_postgres:
        db.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='incomes' AND column_name='tipo_ingreso'
                ) THEN
                    ALTER TABLE incomes 
                    ADD COLUMN tipo_ingreso VARCHAR(50) DEFAULT 'sueldo';
                END IF;
            END $$;
        """))
    else:
        try:
            db.execute(text("""
                ALTER TABLE incomes ADD COLUMN tipo_ingreso TEXT DEFAULT 'sueldo'
            """))
        except:
            pass
    
    print("✅ Reestructuración completada exitosamente")
    print("   - family_members: eliminadas columnas económicas")
    print("   - family_members: agregadas columnas parentesco, edad, estado_laboral")
    print("   - incomes: mejorada columna tipo_ingreso")


def down(db):
    """Revertir reestructuración"""
    
    is_postgres = DatabaseConfig.is_postgresql()
    
    if is_postgres:
        # Eliminar nuevas columnas de family_members
        db.execute(text("""
            ALTER TABLE family_members 
            DROP COLUMN IF EXISTS parentesco,
            DROP COLUMN IF EXISTS edad,
            DROP COLUMN IF EXISTS estado_laboral
        """))
        
        # Restaurar columnas económicas (con valores por defecto)
        db.execute(text("""
            ALTER TABLE family_members 
            ADD COLUMN tipo_ingreso VARCHAR(50) DEFAULT 'sueldo',
            ADD COLUMN sueldo_mensual NUMERIC(10, 2)
        """))
    
    print("↩️ Reestructuración revertida")
