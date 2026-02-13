"""
Migración 004 - Agregar soporte para mascotas
Agregar campos tipo_miembro y especie a family_members
"""
from sqlalchemy import text

from configs.database_config import DatabaseConfig


def up(db):
    """Agregar soporte para mascotas en family_members"""
    
    is_postgres = DatabaseConfig.is_postgresql()
    
    # 1. Agregar campo tipo_miembro (persona/mascota)
    if is_postgres:
        db.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='family_members' AND column_name='tipo_miembro'
                ) THEN
                    ALTER TABLE family_members 
                    ADD COLUMN tipo_miembro VARCHAR(20) DEFAULT 'persona';
                END IF;
            END $$;
        """))
    else:
        try:
            db.execute(text("""
                ALTER TABLE family_members 
                ADD COLUMN tipo_miembro TEXT DEFAULT 'persona'
            """))
        except:
            pass
    
    # 2. Agregar campo especie (para mascotas)
    if is_postgres:
        db.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='family_members' AND column_name='especie'
                ) THEN
                    ALTER TABLE family_members 
                    ADD COLUMN especie VARCHAR(50);
                END IF;
            END $$;
        """))
    else:
        try:
            db.execute(text("""
                ALTER TABLE family_members ADD COLUMN especie TEXT
            """))
        except:
            pass
    
    print("✅ Soporte para mascotas agregado exitosamente")
    print("   - family_members: agregado campo tipo_miembro (persona/mascota)")
    print("   - family_members: agregado campo especie (gato/perro/pájaro/otro)")


def down(db):
    """Revertir soporte para mascotas"""
    
    is_postgres = DatabaseConfig.is_postgresql()
    
    if is_postgres:
        db.execute(text("""
            ALTER TABLE family_members 
            DROP COLUMN IF EXISTS tipo_miembro,
            DROP COLUMN IF EXISTS especie
        """))
    
    print("↩️ Soporte para mascotas eliminado")
