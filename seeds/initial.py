"""
Orquestador de seeds — punto de entrada del CLI (`fleting db seed`).

Flujo:
  1. Siempre ejecuta essential_data.py  (datos críticos, idempotente)
  2. Solo en APP_ENV=development ejecuta los seeds de prueba (001, 002, 003)
  3. En APP_ENV=production bloquea los seeds de prueba y avisa

Los seeds individuales (001/002/003) tienen además su propia validación
defensiva interna como segunda línea de seguridad.
"""

from __future__ import annotations

import importlib
import os


def _correr_seed(nombre: str, db) -> None:
    """Importa y ejecuta el run() de un seed por nombre de módulo."""
    try:
        modulo = importlib.import_module(f"seeds.{nombre}")
        modulo.run(db)
    except Exception as e:
        print(f"  ❌  Error en seed '{nombre}': {e}")
        raise


def run(db):
    app_env = os.getenv("APP_ENV", "development")

    # --- Capa 1: datos esenciales (siempre, cualquier entorno) ---
    _correr_seed("essential_data", db)

    # --- Capa 2: datos de desarrollo (bloqueado en production) ---
    if app_env == "production":
        print("  ⛔  APP_ENV=production — seeds de desarrollo bloqueados.")
        print("  ℹ️   La BD solo contiene datos esenciales.")
        return

    print(f"  🌱  APP_ENV={app_env} — ejecutando seeds de desarrollo...")
    _correr_seed("001_gastos_ficticios", db)
    _correr_seed("002_memoria_vectorial", db)
    _correr_seed("003_expense_embeddings", db)
