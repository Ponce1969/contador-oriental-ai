"""
Generador de SECRET_KEY y contrase├▒as hasheadas para Contador Oriental.

Uso:
    uv run python generate_secret_key.py              # genera solo SECRET_KEY
    uv run python generate_secret_key.py --password   # genera hash de contrase├▒a
    uv run python generate_secret_key.py --all        # genera todo junto

Mover este script a la carpeta scripts/ luego de usarlo.
"""
from __future__ import annotations

import argparse
import getpass
import secrets
import sys


def generar_secret_key(longitud: int = 32) -> str:
    """Genera una SECRET_KEY criptogr├íficamente segura."""
    return secrets.token_hex(longitud)


def hashear_password(password: str) -> str:
    """Hashea una contrase├▒a con Argon2id (igual que usa la app)."""
    try:
        from argon2 import PasswordHasher
        ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)
        return ph.hash(password)
    except ImportError:
        print("ÔØî argon2-cffi no instalado. Ejecutar: uv sync")
        sys.exit(1)


def solicitar_password() -> str:
    """Solicita contrase├▒a por consola (sin eco) con confirmaci├│n."""
    while True:
        pwd = getpass.getpass("  Ingres├í la contrase├▒a: ")
        if len(pwd) < 8:
            print("  ÔÜá´©Å  M├¡nimo 8 caracteres. Intent├í de nuevo.\n")
            continue
        confirmacion = getpass.getpass("  Confirm├í la contrase├▒a: ")
        if pwd != confirmacion:
            print("  ÔØî Las contrase├▒as no coinciden. Intent├í de nuevo.\n")
            continue
        return pwd


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generador de credenciales para Contador Oriental"
    )
    parser.add_argument(
        "--password", "-p",
        action="store_true",
        help="Generar hash de contrase├▒a Argon2id",
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Generar SECRET_KEY y hash de contrase├▒a",
    )
    parser.add_argument(
        "--key-length",
        type=int,
        default=32,
        help="Longitud de la SECRET_KEY en bytes (default: 32)",
    )
    args = parser.parse_args()

    print("\n­ƒöÉ Contador Oriental ÔÇö Generador de credenciales\n")
    print("=" * 50)

    generar_key = not args.password or args.all
    generar_pwd = args.password or args.all

    if generar_key:
        key = generar_secret_key(args.key_length)
        print("\nÔ£à SECRET_KEY generada:")
        print(f"   SECRET_KEY={key}")
        print("\n   ÔåÆ Copiar esta l├¡nea al archivo .env")

    if generar_pwd:
        print("\n­ƒöæ Hash de contrase├▒a (Argon2id):")
        password = solicitar_password()
        hash_resultado = hashear_password(password)
        print(f"\n   Hash: {hash_resultado}")
        print("\n   ÔåÆ Usar este hash para actualizar directamente en la BD")
        print("   ÔåÆ O pasarlo a create_user() si cre├ís el usuario por c├│digo")

    print("\n" + "=" * 50)
    print("ÔÜá´©Å  NUNCA subir estas credenciales a Git.\n")


if __name__ == "__main__":
    main()
