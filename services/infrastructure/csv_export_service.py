"""
Servicio de exportación de gastos e informes contables a formato CSV.
Incluye BOM UTF-8 (\ufeff) para compatibilidad total con Microsoft Excel.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.expense_model import Expense


class CsvExportService:
    """Generador de archivos CSV con formato y codificación amigable para Excel."""

    HEADER = [
        "Fecha",
        "Entorno",
        "Categoría",
        "Subcategoría",
        "Descripción",
        "Moneda",
        "Monto",
        "Método de Pago",
    ]

    @classmethod
    def generate_csv_string(cls, expenses: list[Expense]) -> str:
        """Genera el contenido del CSV como string con UTF-8 BOM."""
        output = io.StringIO()
        output.write("\ufeff")
        writer = csv.writer(output, dialect="excel", lineterminator="\n")
        writer.writerow(cls.HEADER)

        for exp in expenses:
            writer.writerow(
                [
                    exp.fecha.strftime("%Y-%m-%d"),
                    exp.entorno or "general",
                    exp.categoria.value,
                    exp.subcategoria or "",
                    exp.descripcion,
                    exp.currency,
                    f"{exp.monto:.2f}",
                    exp.metodo_pago.value,
                ]
            )

        return output.getvalue()

    @classmethod
    def export_to_file(cls, expenses: list[Expense], target_path: str | Path) -> Path:
        """Guarda la lista de gastos en un archivo CSV con codificación utf-8."""
        path = Path(target_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = cls.generate_csv_string(expenses)
        path.write_text(content, encoding="utf-8")
        return path
