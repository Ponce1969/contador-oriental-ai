"""
Controller para gestión de gastos familiares
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from result import Ok, Result

from controllers.base_controller import BaseController
from core.events import Event, EventType
from core.unit_of_work import UnitOfWork
from models.errors import AppError
from models.expense_model import Expense
from repositories.expense_repository import ExpenseRepository
from repositories.monthly_snapshot_repository import MonthlySnapshotRepository
from services.domain.expense_service import ExpenseService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ExpenseController(BaseController):
    """
    Controller para página de gastos.
    Soporta UoW inyectado para transacciones atómicas.
    """

    def __init__(
        self,
        session: Session | None = None,
        familia_id: int | None = None,
        uow: UnitOfWork | None = None,
    ) -> None:
        super().__init__(session=session, familia_id=familia_id, uow=uow)

    def get_title(self) -> str:
        return "Gastos Familiares"

    def add_expense(self, expense: Expense) -> Result[Expense, AppError]:
        """Agregar un nuevo gasto y publicar evento para memoria vectorial."""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            result = service.create_expense(expense)

        if isinstance(result, Ok):
            gasto = result.ok()
            event = Event(
                type=EventType.GASTO_CREADO,
                familia_id=self._familia_id or 0,
                source_id=gasto.id,
                data={
                    "descripcion": gasto.descripcion,
                    "monto": gasto.monto,
                    "categoria": gasto.categoria.value,
                    "subcategoria": gasto.subcategoria,
                    "metodo_pago": gasto.metodo_pago.value,
                    "fecha": str(gasto.fecha),
                    "recurrente": gasto.es_recurrente,
                },
            )
            self._event_system.fire_and_forget(event)
            try:
                with self._get_session() as session:
                    snap_repo = MonthlySnapshotRepository(
                        session, self._familia_id or 0
                    )
                    snap_repo.upsert_mes(gasto.fecha.year, gasto.fecha.month)
            except Exception:
                pass

        return result

    def list_expenses(self) -> list[Expense]:
        """Listar todos los gastos (sin filtro)"""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            return service.list_expenses()

    def list_expenses_by_month(
        self, year: int, month: int, entorno: str | None = None
    ) -> list[Expense]:
        """Listar gastos de un mes específico"""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            return service.list_by_month(year, month, entorno=entorno)

    def list_by_category(self, categoria: str) -> list[Expense]:
        """Listar gastos por categoría"""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            return service.list_by_category(categoria)

    def get_summary_by_categories(
        self,
        year: int | None = None,
        month: int | None = None,
        currency: str | None = None,
        entorno: str | None = None,
    ) -> dict[tuple[str, str], Decimal]:
        """Obtener resumen de gastos por (categoría, moneda) del mes indicado."""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            return service.get_summary_by_categories(
                year=year, month=month, currency=currency, entorno=entorno
            )

    def update_expense(self, expense: Expense) -> Result[Expense, AppError]:
        """Actualizar un gasto existente y resincronizar snapshot."""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            result = service.update_expense(expense)

        if isinstance(result, Ok):
            gasto = result.ok()
            if gasto:
                try:
                    with self._get_session() as session:
                        MonthlySnapshotRepository(
                            session, self._familia_id or 0
                        ).upsert_mes(gasto.fecha.year, gasto.fecha.month)
                except Exception:
                    pass

        return result

    def delete_expense(self, expense_id: int) -> Result[None, AppError]:
        """Eliminar un gasto y resincronizar snapshot."""
        fecha_gasto = None
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            exp_res = repo.get_by_id(expense_id)
            if isinstance(exp_res, Ok):
                exp = exp_res.ok()
                if exp:
                    fecha_gasto = exp.fecha
            service = ExpenseService(repo)
            result = service.delete_expense(expense_id)

        if isinstance(result, Ok) and fecha_gasto:
            try:
                with self._get_session() as session:
                    MonthlySnapshotRepository(
                        session, self._familia_id or 0
                    ).upsert_mes(fecha_gasto.year, fecha_gasto.month)
            except Exception:
                pass

        return result

    def get_total_by_month(
        self,
        year: int,
        month: int,
        currency: str | None = None,
        entorno: str | None = None,
    ) -> dict[str, Decimal]:
        """Obtener total de gastos de un mes específico, agrupado por moneda."""
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            return service.get_total_by_month(
                year, month, currency=currency, entorno=entorno
            )

    def export_expenses_csv(
        self,
        year: int,
        month: int,
        entorno: str | None = None,
        target_path: str | None = None,
    ) -> tuple[str, str | None]:
        """
        Exporta los gastos del mes indicado a formato CSV con BOM UTF-8.
        Retorna una tupla (contenido_csv, ruta_archivo_guardado).
        """
        from pathlib import Path

        from services.infrastructure.csv_export_service import CsvExportService

        expenses = self.list_expenses_by_month(year, month, entorno=entorno)
        csv_text = CsvExportService.generate_csv_string(expenses)

        if not target_path:
            target_path = str(
                Path("assets") / "exports" / f"gastos_{year}_{month:02d}.csv"
            )

        saved = CsvExportService.export_to_file(expenses, target_path)
        saved_path = str(saved) if saved else None
        return csv_text, saved_path
