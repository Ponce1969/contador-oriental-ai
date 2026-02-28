"""
Repository para gestión de gastos familiares
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from database.tables import ExpenseTable
from models.expense_model import Expense
from repositories.base_table_repository import BaseTableRepository
from repositories.mappers import to_domain, to_table


class ExpenseRepository(BaseTableRepository[Expense, ExpenseTable]):
    """Repository para operaciones CRUD de gastos"""
    
    def __init__(self, session: Session, familia_id: int | None = None) -> None:
        super().__init__(session, ExpenseTable, familia_id)

    def _to_domain(self, table_row):
        """Convertir tabla ExpenseTable a dominio Expense"""
        return to_domain(table_row)
    
    def _to_table(self, expense):
        """Convertir dominio Expense a tabla ExpenseTable"""
        return to_table(expense)

    def _update_specific_fields(self, table_row, expense: Expense) -> None:
        """Actualizar campos específicos de gastos."""
        table_row.categoria = expense.categoria.value
        table_row.subcategoria = expense.subcategoria
        table_row.metodo_pago = expense.metodo_pago.value
        table_row.es_recurrente = expense.es_recurrente
        table_row.frecuencia = (
            expense.frecuencia_recurrencia.value
            if expense.frecuencia_recurrencia
            else None
        )

    def get_by_category(self, categoria: str) -> Sequence[Expense]:
        """Obtener gastos por categoría de la familia"""
        query = self.session.query(ExpenseTable).filter(
            ExpenseTable.categoria == categoria
        )
        query = self._filter_by_family(query)
        rows = query.all()
        return [to_domain(row) for row in rows]

    def get_by_month(self, year: int, month: int) -> Sequence[Expense]:
        """Obtener gastos de un mes específico de la familia"""
        from sqlalchemy import extract

        query = self.session.query(ExpenseTable).filter(
            extract('year', ExpenseTable.fecha) == year,
            extract('month', ExpenseTable.fecha) == month
        )
        query = self._filter_by_family(query)
        rows = query.all()
        return [to_domain(row) for row in rows]

    def guardar_embedding(self, expense_id: int, embedding: list[float]) -> None:
        """Persistir el embedding vectorial en el registro del gasto."""
        self.session.query(ExpenseTable).filter(
            ExpenseTable.id == expense_id,
            ExpenseTable.familia_id == self.familia_id,
        ).update({"embedding": embedding})
        self.session.commit()

    def buscar_por_similitud(
        self,
        embedding: list[float],
        umbral_cosine: float = 0.25,
        limite: int = 20,
    ) -> list[tuple[Expense, float]]:
        """
        Buscar gastos semánticamente similares usando distancia cosine pgvector.
        Retorna lista de (Expense, distancia) ordenada por similitud ascendente.
        Solo retorna gastos con embedding != NULL y distancia <= umbral.
        """
        from sqlalchemy import text

        sql = text("""
            SELECT id, (embedding <=> CAST(:emb AS vector)) AS distancia
            FROM expenses
            WHERE familia_id = :fid
              AND embedding IS NOT NULL
              AND (embedding <=> CAST(:emb AS vector)) <= :umbral
            ORDER BY distancia ASC
            LIMIT :limite
        """)
        rows = self.session.execute(sql, {
            "emb": str(embedding),
            "fid": self.familia_id,
            "umbral": umbral_cosine,
            "limite": limite,
        }).fetchall()

        if not rows:
            return []

        ids = [r[0] for r in rows]
        distancias = {r[0]: r[1] for r in rows}

        gastos = self.session.query(ExpenseTable).filter(
            ExpenseTable.id.in_(ids)
        ).all()

        result = [(to_domain(g), distancias[g.id]) for g in gastos]
        result.sort(key=lambda x: x[1])
        return result

