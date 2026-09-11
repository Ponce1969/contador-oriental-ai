"""
Tests para categorías, subcategorías y enriquecimiento de embeddings.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from models.categories import (
    CATEGORIES_CAMPO,
    CATEGORIES_HOGAR,
    ExpenseCategory,
    PaymentMethod,
    get_categories_for_entorno,
    get_subcategories,
)
from models.expense_model import Expense
from services.ai.memory_event_handler import MemoryEventHandler


def test_nuevas_categorias_campo():
    assert ExpenseCategory.AGRO_ARRENDAMIENTO in CATEGORIES_CAMPO
    assert ExpenseCategory.AGRO_COMISIONES_IMPUESTOS in CATEGORIES_CAMPO
    assert ExpenseCategory.AGRO_SERVICIOS in CATEGORIES_CAMPO

    assert ExpenseCategory.AGRO_ARRENDAMIENTO not in CATEGORIES_HOGAR
    assert ExpenseCategory.AGRO_COMISIONES_IMPUESTOS not in CATEGORIES_HOGAR
    assert ExpenseCategory.AGRO_SERVICIOS not in CATEGORIES_HOGAR


def test_get_categories_for_entorno():
    campo_cats = get_categories_for_entorno("campo")
    hogar_cats = get_categories_for_entorno("hogar")

    assert ExpenseCategory.AGRO_ARRENDAMIENTO in campo_cats
    assert ExpenseCategory.AGRO_ARRENDAMIENTO not in hogar_cats


def test_get_subcategories_vehiculos():
    subcats = get_subcategories(ExpenseCategory.VEHICULOS)
    assert "Combustible" in subcats
    assert "Mantenimiento vehículo" in subcats
    assert "Transporte público / Pasajes" in subcats


def test_get_subcategories_hogar():
    subcats = get_subcategories(ExpenseCategory.HOGAR)
    assert "Mantenimiento hogar" in subcats


def test_get_subcategories_campo():
    arrend = get_subcategories(ExpenseCategory.AGRO_ARRENDAMIENTO)
    assert "Arrendamiento agrícola" in arrend
    assert "Pastoreo / Capitalización" in arrend

    impuestos = get_subcategories(ExpenseCategory.AGRO_COMISIONES_IMPUESTOS)
    assert "Impuestos municipales / BPS" in impuestos
    assert "Comisión consignatario / remate" in impuestos

    servicios = get_subcategories(ExpenseCategory.AGRO_SERVICIOS)
    assert "UTE Rural / Bombeo eléctrico" in servicios


def test_get_subcategories_categoria_desconocida():
    assert get_subcategories("Categoría Inexistente") == []


def test_expense_model_subcategoria_validator():
    exp = Expense(
        monto=Decimal("1500"),
        descripcion="Nafta",
        categoria=ExpenseCategory.VEHICULOS,
        subcategoria="  Combustible  ",
        metodo_pago=PaymentMethod.EFECTIVO,
        fecha=date(2026, 3, 1),
    )
    assert exp.subcategoria == "Combustible"

    exp_vacio = Expense(
        monto=Decimal("1500"),
        descripcion="Nafta",
        categoria=ExpenseCategory.VEHICULOS,
        subcategoria="   ",
        metodo_pago=PaymentMethod.EFECTIVO,
        fecha=date(2026, 3, 1),
    )
    assert exp_vacio.subcategoria is None


def test_memory_event_handler_formatear_gasto_con_subcategoria():
    handler = MemoryEventHandler(memory_service=None)  # type: ignore
    data_con = {
        "monto": 2500,
        "descripcion": "Cambio de aceite",
        "categoria": "🚗 Vehículo",
        "subcategoria": "Mantenimiento vehículo",
        "metodo_pago": "Efectivo",
        "fecha": "2026-03-01",
    }
    texto_con = handler._formatear_gasto(data_con)
    assert "(subcategoría: Mantenimiento vehículo)" in texto_con

    data_sin = {
        "monto": 500,
        "descripcion": "Pan",
        "categoria": "🛒 Almacén",
        "metodo_pago": "Efectivo",
        "fecha": "2026-03-01",
    }
    texto_sin = handler._formatear_gasto(data_sin)
    assert "subcategoría" not in texto_sin
