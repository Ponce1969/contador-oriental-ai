"""
Seed: gastos ficticios para pruebas del Contador Oriental
Genera 60+ gastos distribuidos en varios meses para probar RAG y fuzzy matching.
Idempotente: borra solo los gastos con notas='seed_test' antes de insertar.
"""

from __future__ import annotations

from datetime import date

from database.engine import get_session
from database.tables import ExpenseTable


FAMILIA_ID = 3  # Cambiá si tu familia_id es diferente


GASTOS = [
    # ── Febrero 2026 ────────────────────────────────────────────────
    {"fecha": date(2026, 2, 1),  "monto": 2000,  "cat": "🛒 Almacén",    "desc": "compra de carniceria",              "metodo": "Tarjeta débito"},
    {"fecha": date(2026, 2, 3),  "monto": 1500,  "cat": "🛒 Almacén",    "desc": "compra de carne para un asado",     "metodo": "Efectivo"},
    {"fecha": date(2026, 2, 5),  "monto": 800,   "cat": "🛒 Almacén",    "desc": "compra de milanesas y pollo",       "metodo": "Efectivo"},
    {"fecha": date(2026, 2, 7),  "monto": 3000,  "cat": "🛒 Almacén",    "desc": "compras de almacen supermercado",   "metodo": "Tarjeta débito"},
    {"fecha": date(2026, 2, 8),  "monto": 1200,  "cat": "🛒 Almacén",    "desc": "verduras y frutas verduleria",      "metodo": "Efectivo"},
    {"fecha": date(2026, 2, 10), "monto": 4500,  "cat": "🏠 Hogar",      "desc": "compra de articulos para el Hogar", "metodo": "Tarjeta crédito"},
    {"fecha": date(2026, 2, 12), "monto": 900,   "cat": "🛒 Almacén",    "desc": "pan y facturas en panaderia",       "metodo": "Efectivo"},
    {"fecha": date(2026, 2, 14), "monto": 2500,  "cat": "💊 Salud",      "desc": "farmacia medicamentos",             "metodo": "Tarjeta débito"},
    {"fecha": date(2026, 2, 15), "monto": 1800,  "cat": "🚗 Vehículos",  "desc": "nafta combustible shell",           "metodo": "Tarjeta débito"},
    {"fecha": date(2026, 2, 17), "monto": 600,   "cat": "🛒 Almacén",    "desc": "detergente y lavandina limpieza",   "metodo": "Efectivo"},
    {"fecha": date(2026, 2, 18), "monto": 3200,  "cat": "👕 Ropa",       "desc": "compra de ropa deportiva",          "metodo": "Tarjeta crédito"},
    {"fecha": date(2026, 2, 20), "monto": 700,   "cat": "🛒 Almacén",    "desc": "chorizo y morcilla para parrilla",  "metodo": "Efectivo"},
    {"fecha": date(2026, 2, 22), "monto": 1100,  "cat": "📚 Educación",  "desc": "compra en libreria utiles",         "metodo": "Efectivo"},
    {"fecha": date(2026, 2, 24), "monto": 2200,  "cat": "🎉 Ocio",       "desc": "entrada cine y restaurant",         "metodo": "Tarjeta crédito"},
    {"fecha": date(2026, 2, 26), "monto": 980,   "cat": "🛒 Almacén",    "desc": "bife de chorizo y vacio carniceria","metodo": "Efectivo"},

    # ── Enero 2026 ──────────────────────────────────────────────────
    {"fecha": date(2026, 1, 3),  "monto": 1800,  "cat": "🛒 Almacén",    "desc": "compra de carne picada y asado",    "metodo": "Efectivo"},
    {"fecha": date(2026, 1, 5),  "monto": 3500,  "cat": "🛒 Almacén",    "desc": "compras de almacen y supermercado", "metodo": "Tarjeta débito"},
    {"fecha": date(2026, 1, 8),  "monto": 2800,  "cat": "🏠 Hogar",      "desc": "electrodomesticos para el hogar",   "metodo": "Tarjeta crédito"},
    {"fecha": date(2026, 1, 10), "monto": 1200,  "cat": "🛒 Almacén",    "desc": "verduras tomate lechuga cebolla",   "metodo": "Efectivo"},
    {"fecha": date(2026, 1, 12), "monto": 900,   "cat": "💊 Salud",      "desc": "remedios farmacia drogueria",       "metodo": "Tarjeta débito"},
    {"fecha": date(2026, 1, 14), "monto": 2100,  "cat": "🚗 Vehículos",  "desc": "gasoil combustible ancap",          "metodo": "Efectivo"},
    {"fecha": date(2026, 1, 16), "monto": 1500,  "cat": "🛒 Almacén",    "desc": "pollo entero y hamburguesas",       "metodo": "Efectivo"},
    {"fecha": date(2026, 1, 18), "monto": 4200,  "cat": "👕 Ropa",       "desc": "calzado y ropa invierno",           "metodo": "Tarjeta crédito"},
    {"fecha": date(2026, 1, 20), "monto": 650,   "cat": "🛒 Almacén",    "desc": "medialunas y bizcochos panaderia",  "metodo": "Efectivo"},
    {"fecha": date(2026, 1, 22), "monto": 1900,  "cat": "🎉 Ocio",       "desc": "salida restaurante y bar",          "metodo": "Tarjeta crédito"},
    {"fecha": date(2026, 1, 25), "monto": 780,   "cat": "🛒 Almacén",    "desc": "costillas de cerdo carniceria",     "metodo": "Efectivo"},
    {"fecha": date(2026, 1, 28), "monto": 3100,  "cat": "🏠 Hogar",      "desc": "gastos de plomeria y pintura",      "metodo": "Transferencia"},

    # ── Diciembre 2025 ──────────────────────────────────────────────
    {"fecha": date(2025, 12, 2),  "monto": 2400, "cat": "🛒 Almacén",    "desc": "asado de tira y churrasco",        "metodo": "Efectivo"},
    {"fecha": date(2025, 12, 5),  "monto": 4800, "cat": "🏠 Hogar",      "desc": "compra de muebles para el hogar",  "metodo": "Tarjeta crédito"},
    {"fecha": date(2025, 12, 8),  "monto": 1300, "cat": "🛒 Almacén",    "desc": "frutas naranjas manzanas banana",  "metodo": "Efectivo"},
    {"fecha": date(2025, 12, 10), "monto": 2000, "cat": "🚗 Vehículos",  "desc": "nafta ypf y service auto",         "metodo": "Tarjeta débito"},
    {"fecha": date(2025, 12, 12), "monto": 1100, "cat": "💊 Salud",      "desc": "medicamentos y remedios farmacia", "metodo": "Tarjeta débito"},
    {"fecha": date(2025, 12, 15), "monto": 3600, "cat": "🛒 Almacén",    "desc": "supermercado compras mensuales",   "metodo": "Tarjeta débito"},
    {"fecha": date(2025, 12, 18), "monto": 850,  "cat": "🛒 Almacén",    "desc": "milanesas y pollo para la semana", "metodo": "Efectivo"},
    {"fecha": date(2025, 12, 20), "monto": 5200, "cat": "🎉 Ocio",       "desc": "vacaciones y turismo diciembre",   "metodo": "Tarjeta crédito"},
    {"fecha": date(2025, 12, 22), "monto": 1400, "cat": "👕 Ropa",       "desc": "ropa de verano y calzado",         "metodo": "Tarjeta crédito"},
    {"fecha": date(2025, 12, 26), "monto": 950,  "cat": "🛒 Almacén",    "desc": "vacio y picada carniceria",        "metodo": "Efectivo"},
    {"fecha": date(2025, 12, 28), "monto": 1600, "cat": "📚 Educación",  "desc": "libros y material educativo",      "metodo": "Efectivo"},

    # ── Noviembre 2025 ──────────────────────────────────────────────
    {"fecha": date(2025, 11, 3),  "monto": 1750, "cat": "🛒 Almacén",    "desc": "carne para asado del domingo",     "metodo": "Efectivo"},
    {"fecha": date(2025, 11, 6),  "monto": 3200, "cat": "🛒 Almacén",    "desc": "compras en supermercado",          "metodo": "Tarjeta débito"},
    {"fecha": date(2025, 11, 9),  "monto": 2100, "cat": "🏠 Hogar",      "desc": "electricidad arreglos hogar",      "metodo": "Transferencia"},
    {"fecha": date(2025, 11, 12), "monto": 1400, "cat": "🚗 Vehículos",  "desc": "neumaticos y repuestos auto",      "metodo": "Tarjeta crédito"},
    {"fecha": date(2025, 11, 15), "monto": 800,  "cat": "🛒 Almacén",    "desc": "verduleria papas zapallo zanahoria","metodo": "Efectivo"},
    {"fecha": date(2025, 11, 18), "monto": 1200, "cat": "💊 Salud",      "desc": "consulta medica y farmacia",       "metodo": "Tarjeta débito"},
    {"fecha": date(2025, 11, 20), "monto": 680,  "cat": "🛒 Almacén",    "desc": "pan facturas panaderia diaria",    "metodo": "Efectivo"},
    {"fecha": date(2025, 11, 22), "monto": 2800, "cat": "🎉 Ocio",       "desc": "teatro y cena familiar",           "metodo": "Tarjeta crédito"},
    {"fecha": date(2025, 11, 25), "monto": 1050, "cat": "🛒 Almacén",    "desc": "bife angosto y chorizo parrilla",  "metodo": "Efectivo"},
    {"fecha": date(2025, 11, 28), "monto": 3400, "cat": "📚 Educación",  "desc": "cuota educacion mensual colegio",  "metodo": "Transferencia"},
]


def run(db):
    """Seed idempotente: elimina seeds anteriores e inserta frescos."""
    session = get_session()
    try:
        # Eliminar seeds previos de este archivo (idempotente)
        session.query(ExpenseTable).filter(
            ExpenseTable.familia_id == FAMILIA_ID,
            ExpenseTable.notas == "seed_test",
        ).delete()
        session.flush()

        for g in GASTOS:
            row = ExpenseTable(
                familia_id=FAMILIA_ID,
                monto=g["monto"],
                fecha=g["fecha"],
                descripcion=g["desc"],
                categoria=g["cat"],
                metodo_pago=g["metodo"],
                es_recurrente=False,
                notas="seed_test",
            )
            session.add(row)

        session.commit()
        print(f"  ✅ {len(GASTOS)} gastos ficticios insertados para familia_id={FAMILIA_ID}")
    except Exception as e:
        session.rollback()
        print(f"  ❌ Error en seed: {e}")
        raise
    finally:
        session.close()
