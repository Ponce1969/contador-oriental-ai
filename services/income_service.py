"""
Servicio de lógica de negocio para ingresos familiares
"""

from __future__ import annotations

from models.errors import DatabaseError, ValidationError
from models.income_model import Income
from repositories.income_repository import IncomeRepository
from result import Err, Result


class IncomeService:
    """Servicio para gestión de ingresos con validaciones de negocio"""
    
    def __init__(self, repo: IncomeRepository) -> None:
        self._repo = repo

    def create_income(
        self, income: Income
    ) -> Result[Income, ValidationError | DatabaseError]:
        """Crear un nuevo ingreso con validaciones"""
        
        # Validación: monto debe ser positivo
        if income.monto <= 0:
            return Err(ValidationError(message="El monto debe ser mayor a 0"))
        
        # Validación: descripción no puede estar vacía
        if not income.descripcion or income.descripcion.strip() == "":
            return Err(ValidationError(message="La descripción es obligatoria"))
        
        # Validación: debe tener un miembro asociado
        if income.family_member_id <= 0:
            return Err(ValidationError(message="Debe seleccionar un miembro de la familia"))
        
        # Validación: si es recurrente, debe tener frecuencia
        if income.es_recurrente and not income.frecuencia:
            return Err(
                ValidationError(
                    message="Los ingresos recurrentes deben tener frecuencia"
                )
            )
        
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
        
        # Validación: debe tener ID
        if income.id is None:
            return Err(ValidationError(message="El ingreso debe tener un ID"))
        
        # Validación: monto debe ser positivo
        if income.monto <= 0:
            return Err(ValidationError(message="El monto debe ser mayor a 0"))
        
        # Validación: descripción no puede estar vacía
        if not income.descripcion or income.descripcion.strip() == "":
            return Err(ValidationError(message="La descripción es obligatoria"))
        
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
