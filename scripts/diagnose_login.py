"""Diagnostic login issue"""
from repositories.user_repository import UserRepository
from services.auth_service import AuthService
from models.user_model import UserLogin

print("=== DIAGNÓSTICO DE LOGIN ===")
print()

# 1. Verificar usuario admin
print("1. Buscando usuario admin...")
repo = UserRepository()
user_result = repo.get_by_username("admin")

if user_result.is_err():
    print(f"❌ Error: {user_result.err_value}")
    exit()

user = user_result.ok_value
print(f"✅ Usuario encontrado: {user.username}")
print(f"   ID: {user.id}")
print(f"   Activo: {user.activo}")
print(f"   Hash: {user.password_hash[:60]}...")
print()

# 2. Verificar contraseña
print("2. Verificando contraseña admin123...")
auth = AuthService(repo)
creds = UserLogin(username="admin", password="admin123")
result = auth.login(creds)

if result.is_ok():
    print("✅ Login exitoso desde AuthService!")
    logged_user = result.ok_value
    print(f"   Usuario: {logged_user.username}")
    print(f"   Nombre: {logged_user.nombre_completo}")
else:
    print(f"❌ Login fallido: {result.err_value}")
    print()
    print("3. Probando verificación directa de hash...")
    import argon2
    ph = argon2.PasswordHasher()
    try:
        if ph.verify(user.password_hash, "admin123"):
            print("✅ Hash verifica correctamente")
        else:
            print("❌ Hash NO verifica")
    except Exception as e:
        print(f"❌ Error en verificación: {e}")

print()
print("=== FIN DEL DIAGNÓSTICO ===")
