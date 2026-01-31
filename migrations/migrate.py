"""
Sistema de migraciones - Ejecutar migraciones de base de datos
Inspirado en Django y Alembic
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from database.engine import engine


def create_migrations_table():
    """Crear tabla para registrar migraciones aplicadas"""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS _fleting_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_name TEXT NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()


def get_applied_migrations():
    """Obtener lista de migraciones ya aplicadas"""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT migration_name FROM _fleting_migrations"))
        return {row[0] for row in result}


def get_pending_migrations():
    """Obtener migraciones pendientes de aplicar"""
    migrations_dir = Path(__file__).parent
    applied = get_applied_migrations()
    
    # Buscar archivos de migración (001_*.py, 002_*.py, etc.)
    migration_files = sorted([
        f.stem for f in migrations_dir.glob("[0-9][0-9][0-9]_*.py")
    ])
    
    return [m for m in migration_files if m not in applied]


def apply_migration(migration_name: str):
    """Aplicar una migración específica"""
    # Importar el módulo de migración
    migration_module = __import__(f"migrations.{migration_name}", fromlist=["up"])
    
    with engine.connect() as conn:
        # Ejecutar función up()
        migration_module.up(conn)
        
        # Registrar migración aplicada
        conn.execute(
            text("INSERT INTO _fleting_migrations (migration_name) VALUES (:name)"),
            {"name": migration_name}
        )
        conn.commit()
        
        print(f"✅ Applied migration: {migration_name}")


def rollback_last_migration():
    """Revertir la última migración aplicada"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT migration_name FROM _fleting_migrations 
            ORDER BY applied_at DESC LIMIT 1
        """))
        row = result.fetchone()
        
        if not row:
            print("No migrations to rollback")
            return
        
        migration_name = row[0]
        
        # Importar el módulo de migración
        migration_module = __import__(f"migrations.{migration_name}", fromlist=["down"])
        
        # Ejecutar función down()
        migration_module.down(conn)
        
        # Eliminar registro de migración
        conn.execute(
            text("DELETE FROM _fleting_migrations WHERE migration_name = :name"),
            {"name": migration_name}
        )
        conn.commit()
        
        print(f"↩️ Rolled back migration: {migration_name}")


def migrate():
    """Ejecutar todas las migraciones pendientes"""
    create_migrations_table()
    
    pending = get_pending_migrations()
    
    if not pending:
        print("✅ Database is up to date")
        return
    
    print(f"📦 Found {len(pending)} pending migration(s)")
    
    for migration in pending:
        apply_migration(migration)
    
    print("✅ All migrations applied successfully")


def status():
    """Mostrar estado de las migraciones"""
    create_migrations_table()
    
    applied = get_applied_migrations()
    pending = get_pending_migrations()
    
    print("\n📦 Database migration status\n")
    
    if applied:
        print("Applied migrations:")
        for m in sorted(applied):
            print(f"  ✔ {m}")
    
    if pending:
        print("\nPending migrations:")
        for m in pending:
            print(f"  ⏳ {m}")
    
    if not pending:
        print("\n✅ Database is up to date")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python migrate.py [migrate|rollback|status]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "migrate":
        migrate()
    elif command == "rollback":
        rollback_last_migration()
    elif command == "status":
        status()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: migrate, rollback, status")
        sys.exit(1)
