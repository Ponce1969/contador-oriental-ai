"""
Mappers para Income
"""

from __future__ import annotations

from database.tables import IncomeTable
from models.income_model import Income, IncomeCategory, RecurrenceFrequency


def income_to_domain(row: IncomeTable) -> Income:
    """Convertir tabla de base de datos a modelo de dominio Income"""
    return Income(
        id=row.id,
        family_member_id=row.family_member_id,
        monto=row.monto,
        fecha=row.fecha,
        descripcion=row.descripcion,
        categoria=IncomeCategory(row.categoria),
        es_recurrente=row.es_recurrente,
        frecuencia=RecurrenceFrequency(row.frecuencia) if row.frecuencia else None,
        notas=row.notas,
    )


def income_to_table(income: Income) -> IncomeTable:
    """Convertir modelo de dominio Income a tabla de base de datos"""
    return IncomeTable(
        family_member_id=income.family_member_id,
        monto=income.monto,
        fecha=income.fecha,
        descripcion=income.descripcion,
        categoria=income.categoria.value,
        es_recurrente=income.es_recurrente,
        frecuencia=income.frecuencia.value if income.frecuencia else None,
        notas=income.notas,
    )
