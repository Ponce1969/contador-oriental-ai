"""
Servicio de lógica de negocio para ingresos familiares
"""

from __future__ import annotations

from result import Err, Result

from constants.messages import ValidationMessages
from models.errors import DatabaseError, ValidationError
from models.income_model import Income
from repositories.income_repository import IncomeRepository
from services.validators import (
    validate_descripcion_requerida,
    validate_id_requerido,
    validate_monto_positivo,
    validate_recurrente_con_frecuencia,
)


class IncomeService:
    """Servicio para gestión de ingresos con validaciones de negocio"""
    
    def __init__(self, repo: IncomeRepository) -> None:
        self._repo = repo

    def create_income(
        self, income: Income
    ) -> Result[Income, ValidationError | DatabaseError]:
        """Crear un nuevo ingreso con validaciones"""
        for check in (
            validate_monto_positivo(income.monto),
            validate_descripcion_requerida(income.descripcion),
            validate_recurrente_con_frecuencia(
                income.es_recurrente,
                income.frecuencia,
                ValidationMessages.RECURRENTE_SIN_FRECUENCIA_INGRESO,
            ),
        ):
            if check.is_err():
                return check  # type: ignore[return-value]
        if income.family_member_id <= 0:
            return Err(ValidationError(message=ValidationMessages.MIEMBRO_REQUERIDO))  # type: ignore[return-value]
        return self._repo.add(income)

    def list_incomes(self) -> list[Income]:
        """Listar todos los ingresos"""
        incomes = self._repo.get_all()
        return list(incomes)

    def get_income(self, income_id: int) -> Result[Income, DatabaseError]:
        """Obtener un ingreso por ID"""
        return self._repo.get_by_id(income_id)

    def list_by_member(self, member_id: int) -> list[Income]:
        """Listar ingresos de un miembro específico"""
        incomes = self._repo.get_by_member(member_id)
        return list(incomes)

    def list_by_month(self, year: int, month: int) -> list[Income]:
        """Listar ingresos de un mes específico"""
        incomes = self._repo.get_by_month(year, month)
        return list(incomes)

    def delete_income(self, income_id: int) -> Result[None, DatabaseError]:
        """Eliminar un ingreso"""
        return self._repo.delete(income_id)

    def update_income(
        self, income: Income
    ) -> Result[Income, ValidationError | DatabaseError]:
        """Actualizar un ingreso existente con validaciones"""
        for check in (
            validate_id_requerido(income.id, ValidationMessages.ID_REQUERIDO_INGRESO),
            validate_monto_positivo(income.monto),
            validate_descripcion_requerida(income.descripcion),
        ):
            if check.is_err():
                return check  # type: ignore[return-value]
        return self._repo.update(income)

    def get_total_by_month(self, year: int, month: int) -> float:
        """Calcular total de ingresos en un mes"""
        incomes = self.list_by_month(year, month)
        return sum(income.monto for income in incomes)

    def get_total_by_member(self, member_id: int) -> float:
        """Calcular total de ingresos de un miembro"""
        incomes = self.list_by_member(member_id)
        return sum(income.monto for income in incomes)

    def get_summary_by_categories(self) -> dict[str, float]:
        """Obtener resumen de ingresos por categoría"""
        incomes = self.list_incomes()
        summary: dict[str, float] = {}
        
        for income in incomes:
            categoria = income.categoria.value
            summary[categoria] = summary.get(categoria, 0.0) + income.monto
        
        return summary
