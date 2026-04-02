"""
Seed: gastos ficticios para pruebas del Contador Oriental
Genera 60+ gastos distribuidos en varios meses para probar RAG y fuzzy matching.
Idempotente: borra solo los gastos con notas='seed_test' antes de insertar.
"""

from __future__ import annotations

import os
from datetime import date

from database.engine import get_session
from database.tables import ExpenseTable
from models.categories import ExpenseCategory as C, PaymentMethod as P


def _get_familia_id(session) -> int:
    """Retorna la familia_id del usuario admin, universal para cualquier entorno."""
    from sqlalchemy import text

    row = session.execute(
        text("SELECT familia_id FROM usuarios WHERE username = 'admin' LIMIT 1")
    ).fetchone()
    if not row:
        raise RuntimeError(
            "Usuario 'admin' no encontrado. Ejecutá las migraciones primero."
        )
    return row[0]


GASTOS = [
    # ── Febrero 2026 ────────────────────────────────────────────────
    {
        "fecha": date(2026, 2, 1),
        "monto": 2000,
        "cat": C.ALMACEN,
        "desc": "compra de carniceria",
        "metodo": P.TARJETA_DEBITO,
    },
    {
        "fecha": date(2026, 2, 3),
        "monto": 1500,
        "cat": C.ALMACEN,
        "desc": "compra de carne para un asado",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2026, 2, 5),
        "monto": 800,
        "cat": C.ALMACEN,
        "desc": "compra de milanesas y pollo",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2026, 2, 7),
        "monto": 3000,
        "cat": C.ALMACEN,
        "desc": "compras de almacen supermercado",
        "metodo": P.TARJETA_DEBITO,
    },
    {
        "fecha": date(2026, 2, 8),
        "monto": 1200,
        "cat": C.ALMACEN,
        "desc": "verduras y frutas verduleria",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2026, 2, 10),
        "monto": 4500,
        "cat": C.HOGAR,
        "desc": "compra de articulos para el Hogar",
        "metodo": P.TARJETA_CREDITO,
    },
    {
        "fecha": date(2026, 2, 12),
        "monto": 900,
        "cat": C.ALMACEN,
        "desc": "pan y facturas en panaderia",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2026, 2, 14),
        "monto": 2500,
        "cat": C.SALUD,
        "desc": "farmacia medicamentos",
        "metodo": P.TARJETA_DEBITO,
    },
    {
        "fecha": date(2026, 2, 15),
        "monto": 1800,
        "cat": C.VEHICULOS,
        "desc": "nafta combustible shell",
        "metodo": P.TARJETA_DEBITO,
    },
    {
        "fecha": date(2026, 2, 17),
        "monto": 600,
        "cat": C.ALMACEN,
        "desc": "detergente y lavandina limpieza",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2026, 2, 18),
        "monto": 3200,
        "cat": C.ROPA,
        "desc": "compra de ropa deportiva",
        "metodo": P.TARJETA_CREDITO,
    },
    {
        "fecha": date(2026, 2, 20),
        "monto": 700,
        "cat": C.ALMACEN,
        "desc": "chorizo y morcilla para parrilla",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2026, 2, 22),
        "monto": 1100,
        "cat": C.EDUCACION,
        "desc": "compra en libreria utiles",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2026, 2, 24),
        "monto": 2200,
        "cat": C.OCIO,
        "desc": "entrada cine y restaurant",
        "metodo": P.TARJETA_CREDITO,
    },
    {
        "fecha": date(2026, 2, 26),
        "monto": 980,
        "cat": C.ALMACEN,
        "desc": "bife de chorizo y vacio carniceria",
        "metodo": P.EFECTIVO,
    },
    # ── Enero 2026 ──────────────────────────────────────────────────
    {
        "fecha": date(2026, 1, 3),
        "monto": 1800,
        "cat": C.ALMACEN,
        "desc": "compra de carne picada y asado",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2026, 1, 5),
        "monto": 3500,
        "cat": C.ALMACEN,
        "desc": "compras de almacen y supermercado",
        "metodo": P.TARJETA_DEBITO,
    },
    {
        "fecha": date(2026, 1, 8),
        "monto": 2800,
        "cat": C.HOGAR,
        "desc": "electrodomesticos para el hogar",
        "metodo": P.TARJETA_CREDITO,
    },
    {
        "fecha": date(2026, 1, 10),
        "monto": 1200,
        "cat": C.ALMACEN,
        "desc": "verduras tomate lechuga cebolla",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2026, 1, 12),
        "monto": 900,
        "cat": C.SALUD,
        "desc": "remedios farmacia drogueria",
        "metodo": P.TARJETA_DEBITO,
    },
    {
        "fecha": date(2026, 1, 14),
        "monto": 2100,
        "cat": C.VEHICULOS,
        "desc": "gasoil combustible ancap",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2026, 1, 16),
        "monto": 1500,
        "cat": C.ALMACEN,
        "desc": "pollo entero y hamburguesas",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2026, 1, 18),
        "monto": 4200,
        "cat": C.ROPA,
        "desc": "calzado y ropa invierno",
        "metodo": P.TARJETA_CREDITO,
    },
    {
        "fecha": date(2026, 1, 20),
        "monto": 650,
        "cat": C.ALMACEN,
        "desc": "medialunas y bizcochos panaderia",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2026, 1, 22),
        "monto": 1900,
        "cat": C.OCIO,
        "desc": "salida restaurante y bar",
        "metodo": P.TARJETA_CREDITO,
    },
    {
        "fecha": date(2026, 1, 25),
        "monto": 780,
        "cat": C.ALMACEN,
        "desc": "costillas de cerdo carniceria",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2026, 1, 28),
        "monto": 3100,
        "cat": C.HOGAR,
        "desc": "gastos de plomeria y pintura",
        "metodo": P.TRANSFERENCIA,
    },
    # ── Diciembre 2025 ──────────────────────────────────────────────
    {
        "fecha": date(2025, 12, 2),
        "monto": 2400,
        "cat": C.ALMACEN,
        "desc": "asado de tira y churrasco",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2025, 12, 5),
        "monto": 4800,
        "cat": C.HOGAR,
        "desc": "compra de muebles para el hogar",
        "metodo": P.TARJETA_CREDITO,
    },
    {
        "fecha": date(2025, 12, 8),
        "monto": 1300,
        "cat": C.ALMACEN,
        "desc": "frutas naranjas manzanas banana",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2025, 12, 10),
        "monto": 2000,
        "cat": C.VEHICULOS,
        "desc": "nafta ypf y service auto",
        "metodo": P.TARJETA_DEBITO,
    },
    {
        "fecha": date(2025, 12, 12),
        "monto": 1100,
        "cat": C.SALUD,
        "desc": "medicamentos y remedios farmacia",
        "metodo": P.TARJETA_DEBITO,
    },
    {
        "fecha": date(2025, 12, 15),
        "monto": 3600,
        "cat": C.ALMACEN,
        "desc": "supermercado compras mensuales",
        "metodo": P.TARJETA_DEBITO,
    },
    {
        "fecha": date(2025, 12, 18),
        "monto": 850,
        "cat": C.ALMACEN,
        "desc": "milanesas y pollo para la semana",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2025, 12, 20),
        "monto": 5200,
        "cat": C.OCIO,
        "desc": "vacaciones y turismo diciembre",
        "metodo": P.TARJETA_CREDITO,
    },
    {
        "fecha": date(2025, 12, 22),
        "monto": 1400,
        "cat": C.ROPA,
        "desc": "ropa de verano y calzado",
        "metodo": P.TARJETA_CREDITO,
    },
    {
        "fecha": date(2025, 12, 26),
        "monto": 950,
        "cat": C.ALMACEN,
        "desc": "vacio y picada carniceria",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2025, 12, 28),
        "monto": 1600,
        "cat": C.EDUCACION,
        "desc": "libros y material educativo",
        "metodo": P.EFECTIVO,
    },
    # ── Noviembre 2025 ──────────────────────────────────────────────
    {
        "fecha": date(2025, 11, 3),
        "monto": 1750,
        "cat": C.ALMACEN,
        "desc": "carne para asado del domingo",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2025, 11, 6),
        "monto": 3200,
        "cat": C.ALMACEN,
        "desc": "compras en supermercado",
        "metodo": P.TARJETA_DEBITO,
    },
    {
        "fecha": date(2025, 11, 9),
        "monto": 2100,
        "cat": C.HOGAR,
        "desc": "electricidad arreglos hogar",
        "metodo": P.TRANSFERENCIA,
    },
    {
        "fecha": date(2025, 11, 12),
        "monto": 1400,
        "cat": C.VEHICULOS,
        "desc": "neumaticos y repuestos auto",
        "metodo": P.TARJETA_CREDITO,
    },
    {
        "fecha": date(2025, 11, 15),
        "monto": 800,
        "cat": C.ALMACEN,
        "desc": "verduleria papas zapallo zanahoria",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2025, 11, 18),
        "monto": 1200,
        "cat": C.SALUD,
        "desc": "consulta medica y farmacia",
        "metodo": P.TARJETA_DEBITO,
    },
    {
        "fecha": date(2025, 11, 20),
        "monto": 680,
        "cat": C.ALMACEN,
        "desc": "pan facturas panaderia diaria",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2025, 11, 22),
        "monto": 2800,
        "cat": C.OCIO,
        "desc": "teatro y cena familiar",
        "metodo": P.TARJETA_CREDITO,
    },
    {
        "fecha": date(2025, 11, 25),
        "monto": 1050,
        "cat": C.ALMACEN,
        "desc": "bife angosto y chorizo parrilla",
        "metodo": P.EFECTIVO,
    },
    {
        "fecha": date(2025, 11, 28),
        "monto": 3400,
        "cat": C.EDUCACION,
        "desc": "cuota educacion mensual colegio",
        "metodo": P.TRANSFERENCIA,
    },
]


def run(db):
    """Seed idempotente: elimina seeds anteriores e inserta frescos."""
    if os.getenv("APP_ENV") == "production":
        print("  ⛔ Seeds deshabilitados en APP_ENV=production. Abortando.")
        return
    session = get_session()
    try:
        familia_id = _get_familia_id(session)

        session.query(ExpenseTable).filter(
            ExpenseTable.familia_id == familia_id,
            ExpenseTable.notas == "seed_test",
        ).delete()
        session.flush()

        for g in GASTOS:
            row = ExpenseTable(
                familia_id=familia_id,
                monto=g["monto"],
                fecha=g["fecha"],
                descripcion=g["desc"],
                categoria=g["cat"].value,
                metodo_pago=g["metodo"].value,
                es_recurrente=False,
                notas="seed_test",
            )
            session.add(row)

        session.commit()
        print(
            f"  ✅ {len(GASTOS)} gastos ficticios insertados para familia_id={familia_id}"
        )
    except Exception as e:
        session.rollback()
        print(f"  ❌ Error en seed: {e}")
        raise
    finally:
        session.close()
