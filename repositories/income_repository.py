"""
Repository para gestión de ingresos familiares
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from database.tables import IncomeTable
from models.income_model import Income
from repositories.base_table_repository import BaseTableRepository
from repositories.income_mappers import income_to_domain, income_to_table


class IncomeRepository(BaseTableRepository[Income, IncomeTable]):
    """Repository para operaciones CRUD de ingresos"""
    
    def __init__(self, session: Session, familia_id: int | None = None) -> None:
        super().__init__(session, IncomeTable, familia_id)

    def _to_domain(self, table_row):
        """Convertir tabla IncomeTable a dominio Income"""
        return income_to_domain(table_row)
    
    def _to_table(self, income):
        """Convertir dominio Income a tabla IncomeTable"""
        return income_to_table(income)

    def _update_specific_fields(self, table_row, income: Income) -> None:
        """Actualizar campos específicos de ingresos."""
        table_row.categoria = income.categoria.value
        table_row.metodo_pago = income.metodo_pago.value
        table_row.es_recurrente = income.es_recurrente
        table_row.frecuencia = (
            income.frecuencia.value
            if income.frecuencia
            else None
        )
        # Campo específico de ingresos
        table_row.family_member_id = income.family_member_id

    def get_by_member(self, member_id: int) -> Sequence[Income]:
        """Obtener ingresos de un miembro específico de la familia"""
        query = self.session.query(IncomeTable).filter(
            IncomeTable.family_member_id == member_id
        )
        query = self._filter_by_family(query)
        rows = query.all()
        return [income_to_domain(row) for row in rows]

    def get_by_month(self, year: int, month: int) -> Sequence[Income]:
        """Obtener ingresos de un mes específico de la familia"""
        from sqlalchemy import extract
        
        query = self.session.query(IncomeTable).filter(
            extract('year', IncomeTable.fecha) == year,
            extract('month', IncomeTable.fecha) == month
        )
        query = self._filter_by_family(query)
        rows = query.all()
        return [income_to_domain(row) for row in rows]
