"""
Tests para el servicio de exportación a formato CSV compatible con Excel.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from models.categories import ExpenseCategory, PaymentMethod
from models.expense_model import Expense
from services.infrastructure.csv_export_service import CsvExportService


def test_generate_csv_string():
    gastos = [
        Expense(
            id=1,
            monto=Decimal("1250.50"),
            currency="UYU",
            fecha=date(2026, 3, 10),
            descripcion="Supermercado Devoto",
            categoria=ExpenseCategory.ALMACEN,
            subcategoria=None,
            metodo_pago=PaymentMethod.TARJETA_DEBITO,
            entorno="hogar",
        ),
        Expense(
            id=2,
            monto=Decimal("5000.00"),
            currency="USD",
            fecha=date(2026, 3, 12),
            descripcion="Pago de Pastoreo",
            categoria=ExpenseCategory.AGRO_ARRENDAMIENTO,
            subcategoria="Pastoreo / Capitalización",
            metodo_pago=PaymentMethod.TRANSFERENCIA,
            entorno="campo",
        ),
    ]

    csv_output = CsvExportService.generate_csv_string(gastos)

    # Debe comenzar con UTF-8 BOM para que Excel en Windows detecte la codificación
    assert csv_output.startswith("\ufeff")

    lines = csv_output.strip().split("\n")
    assert len(lines) == 3  # Header + 2 registros

    header = lines[0].lstrip("\ufeff")
    expected_header = (
        "Fecha,Entorno,Categoría,Subcategoría,Descripción,Moneda,Monto,Método de Pago"
    )
    assert expected_header in header

    # Verificamos fila 1 (sin subcategoría)
    assert "2026-03-10,hogar" in lines[1]
    assert "1250.50" in lines[1]

    # Verificamos fila 2 (con subcategoría y USD)
    assert "2026-03-12,campo" in lines[2]
    assert "Pastoreo / Capitalización" in lines[2]
    assert "USD" in lines[2]
    assert "5000.00" in lines[2]


def test_export_to_file(tmp_path: Path):
    gastos = [
        Expense(
            id=1,
            monto=Decimal("800.00"),
            currency="UYU",
            fecha=date(2026, 3, 5),
            descripcion="Nafta",
            categoria=ExpenseCategory.VEHICULOS,
            subcategoria="Combustible",
            metodo_pago=PaymentMethod.EFECTIVO,
            entorno="hogar",
        )
    ]

    target_file = tmp_path / "subcarpeta" / "export_test.csv"
    saved = CsvExportService.export_to_file(gastos, target_file)

    assert saved.exists()
    raw_bytes = saved.read_bytes()
    # Verifica BOM UTF-8 en bytes
    assert raw_bytes.startswith(b"\xef\xbb\xbf")

    content_str = saved.read_text(encoding="utf-8-sig")
    assert "Combustible" in content_str
    assert "Nafta" in content_str
