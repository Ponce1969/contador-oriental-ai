"""Check if admin user exists and verify password"""
from database.engine import engine
from sqlalchemy import text
from services.auth_service import AuthService
from repositories.user_repository import UserRepository
import argon2

# Check user exists
with engine.connect() as conn:
    result = conn.execute(text('SELECT id, username, password_hash FROM usuarios WHERE username = "admin"'))
    user = row = result.fetchone()
    if user:
        print(f"Usuario encontrado: ID={user[0]}, username={user[1]}")
        print(f"Password hash: {user[2][:50]}...")
    else:
        print("Usuario admin NO encontrado")
        print("Usuarios existentes:")
        result = conn.execute(text('SELECT username FROM usuarios'))
        for row in result:
            print(f"  - {row[0]}")
        exit()

# Verify password
print("\nVerificando contraseña 'admin123':")
repo = UserRepository()
auth = AuthService(repo)

from models.user_model import UserLogin
creds = UserLogin(username="admin", password="admin123")
result = auth.login(creds)

if result.is_ok():
    print("✅ Login exitoso!")
else:
    print(f"❌ Login fallido: {result.err_value}")
    print("\nReseteando contraseña a 'admin123'...")
    
    # Generate new hash
    ph = argon2.PasswordHasher()
    new_hash = ph.hash("admin123")
    print(f"Nuevo hash: {new_hash[:50]}...")
    
    # Update using UserRepository
    update_result = repo.update_password(1, new_hash)
    if update_result.is_ok():
        print("✅ Contraseña actualizada en UserRepository")
    else:
        print(f"❌ Error: {update_result.err_value}")
    
    # Also update directly in DB to be sure
    with engine.connect() as conn:
        conn.execute(
            text('UPDATE usuarios SET password_hash = :hash WHERE username = "admin"'),
            {"hash": new_hash}
        )
        conn.commit()
    
    print("✅ Contraseña actualizada directamente en DB")
    print("Por favor, reinicia la aplicación e intenta login nuevamente.")
