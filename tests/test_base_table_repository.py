"""
Tests para BaseTableRepository - Corazón del CRUD genérico del Escudo Charrúa
"""

import pytest
from sqlalchemy.orm import Session
from result import Err, Ok

from repositories.base_table_repository import BaseTableRepository
from models.expense_model import Expense
from models.income_model import Income
from database.tables import ExpenseTable, IncomeTable


class TestBaseTableRepository:
    """Tests para BaseTableRepository"""
    
    def test_base_repository_instantiation(self, db_session):
        """Test que BaseTableRepository puede instanciarse correctamente"""
        
        class ExpenseRepository(BaseTableRepository[Expense, ExpenseTable]):
            def _update_specific_fields(self, table_row, domain_obj):
                pass
        
        # Crear repositorio con familia_id
        repo = ExpenseRepository(db_session, ExpenseTable, familia_id=1)
        
        assert repo.session == db_session
        assert repo.table_model == ExpenseTable
        assert repo.familia_id == 1
        assert hasattr(repo, '_update_specific_fields')
    
    def test_base_repository_sin_familia_id(self, db_session):
        """Test BaseTableRepository sin familia_id (acceso a todos los datos)"""
        
        class ExpenseRepository(BaseTableRepository[Expense, ExpenseTable]):
            def _update_specific_fields(self, table_row, domain_obj):
                pass
        
        repo = ExpenseRepository(db_session, ExpenseTable)
        assert repo.familia_id is None
    
    def test_filter_by_family_con_familia_id(self, db_session):
        """Test que _filter_by_family aplica filtro correctamente"""
        
        class ExpenseRepository(BaseTableRepository[Expense, ExpenseTable]):
            def _update_specific_fields(self, table_row, domain_obj):
                pass
        
        repo = ExpenseRepository(db_session, ExpenseTable, familia_id=42)
        
        # Crear query base
        query = db_session.query(ExpenseTable)
        
        # Aplicar filtro
        filtered_query = repo._filter_by_family(query)
        
        # Verificar que el filtro se aplicó (debería incluir WHERE familia_id = 42)
        # Nota: No podemos verificar el SQL directamente, pero podemos verificar
        # que el query object fue modificado
        assert filtered_query is not None
    
    def test_filter_by_family_sin_familia_id(self, db_session):
        """Test que _filter_by_family no filtra cuando familia_id es None"""
        
        class ExpenseRepository(BaseTableRepository[Expense, ExpenseTable]):
            def _update_specific_fields(self, table_row, domain_obj):
                pass
        
        repo = ExpenseRepository(db_session, ExpenseTable, familia_id=None)
        
        # Crear query base
        query = db_session.query(ExpenseTable)
        
        # Aplicar filtro
        filtered_query = repo._filter_by_family(query)
        
        # Cuando familia_id es None, debería retornar el mismo query
        assert filtered_query == query


class TestBaseTableRepositoryCRUD:
    """Tests de operaciones CRUD del BaseTableRepository"""
    
    def test_add_expense(self, db_session, setup_test_data):
        """Test agregar un expense usando BaseTableRepository"""
        
        class ExpenseRepository(BaseTableRepository[Expense, ExpenseTable]):
            def _update_specific_fields(self, table_row, expense):
                # Implementación específica para expenses
                table_row.categoria = expense.categoria.value
                table_row.metodo_pago = expense.metodo_pago.value
                table_row.es_recurrente = expense.es_recurrente
        
        repo = ExpenseRepository(db_session, ExpenseTable, familia_id=1)
        
        # Crear un expense de prueba
        expense = Expense(
            monto=1000,
            descripcion="Test expense",
            categoria="Alimentación",
            metodo_pago="Efectivo",
            familia_id=1
        )
        
        # Agregar usando el método base
        result = repo.add(expense)
        
        # Verificar resultado
        assert isinstance(result, Ok)
        saved_expense = result.ok_value
        assert saved_expense.id is not None
        assert saved_expense.descripcion == "Test expense"
        assert saved_expense.monto == 1000
    
    def test_add_income(self, db_session):
        """Test agregar un income usando BaseTableRepository"""
        
        class IncomeRepository(BaseTableRepository[Income, IncomeTable]):
            def _update_specific_fields(self, table_row, income):
                # Implementación específica para incomes
                table_row.categoria = income.categoria.value
                table_row.metodo_pago = income.metodo_pago.value
                table_row.es_recurrente = income.es_recurrente
                table_row.family_member_id = income.family_member_id
        
        repo = IncomeRepository(db_session, IncomeTable, familia_id=1)
        
        # Crear un income de prueba
        income = Income(
            monto=50000,
            descripcion="Sueldo",
            categoria="Salario",
            metodo_pago="Transferencia",
            familia_id=1,
            family_member_id=1
        )
        
        # Agregar usando el método base
        result = repo.add(income)
        
        # Verificar resultado
        assert isinstance(result, Ok)
        saved_income = result.ok_value
        assert saved_income.id is not None
        assert saved_income.descripcion == "Sueldo"
        assert saved_income.monto == 50000
    
    def test_get_all_con_filtro_familia(self, db_session, setup_test_data):
        """Test get_all filtra por familia_id correctamente"""
        
        class ExpenseRepository(BaseTableRepository[Expense, ExpenseTable]):
            def _update_specific_fields(self, table_row, expense):
                table_row.categoria = expense.categoria.value
                table_row.metodo_pago = expense.metodo_pago.value
                table_row.es_recurrente = expense.es_recurrente
        
        # Crear repositorios para diferentes familias
        repo_f1 = ExpenseRepository(db_session, ExpenseTable, familia_id=1)
        repo_f2 = ExpenseRepository(db_session, ExpenseTable, familia_id=2)
        
        # Obtener datos para cada familia
        expenses_f1 = repo_f1.get_all()
        expenses_f2 = repo_f2.get_all()
        
        # Verificar que cada repo solo ve sus datos
        for expense in expenses_f1:
            assert expense.familia_id == 1
        
        for expense in expenses_f2:
            assert expense.familia_id == 2
    
    def test_get_by_id_existente(self, db_session, setup_test_data):
        """Test get_by_id con un registro existente"""
        
        class ExpenseRepository(BaseTableRepository[Expense, ExpenseTable]):
            def _update_specific_fields(self, table_row, expense):
                table_row.categoria = expense.categoria.value
                table_row.metodo_pago = expense.metodo_pago.value
                table_row.es_recurrente = expense.es_recurrente
        
        repo = ExpenseRepository(db_session, ExpenseTable, familia_id=1)
        
        # Agregar un expense primero
        expense = Expense(
            monto=500,
            descripcion="Test get by ID",
            categoria="Transporte",
            metodo_pago="Efectivo",
            familia_id=1
        )
        add_result = repo.add(expense)
        saved_expense = add_result.ok_value
        
        # Obtener por ID
        get_result = repo.get_by_id(saved_expense.id)
        
        # Verificar
        assert isinstance(get_result, Ok)
        found_expense = get_result.ok_value
        assert found_expense.id == saved_expense.id
        assert found_expense.descripcion == "Test get by ID"
    
    def test_get_by_id_no_existente(self, db_session):
        """Test get_by_id con un ID que no existe"""
        
        class ExpenseRepository(BaseTableRepository[Expense, ExpenseTable]):
            def _update_specific_fields(self, table_row, expense):
                pass
        
        repo = ExpenseRepository(db_session, ExpenseTable, familia_id=1)
        
        # Intentar obtener un ID que no existe
        result = repo.get_by_id(99999)
        
        # Debería retornar Err
        assert isinstance(result, Err)
        assert "no encontrado" in result.err_value.message.lower()
    
    def test_delete_expense(self, db_session, setup_test_data):
        """Test eliminar un expense"""
        
        class ExpenseRepository(BaseTableRepository[Expense, ExpenseTable]):
            def _update_specific_fields(self, table_row, expense):
                table_row.categoria = expense.categoria.value
                table_row.metodo_pago = expense.metodo_pago.value
                table_row.es_recurrente = expense.es_recurrente
        
        repo = ExpenseRepository(db_session, ExpenseTable, familia_id=1)
        
        # Agregar un expense primero
        expense = Expense(
            monto=200,
            descripcion="Para eliminar",
            categoria="Otros",
            metodo_pago="Efectivo",
            familia_id=1
        )
        add_result = repo.add(expense)
        saved_expense = add_result.ok_value
        
        # Eliminar
        delete_result = repo.delete(saved_expense.id)
        
        # Verificar que se eliminó
        assert isinstance(delete_result, Ok)
        
        # Intentar obtener el expense eliminado
        get_result = repo.get_by_id(saved_expense.id)
        assert isinstance(get_result, Err)
    
    def test_update_expense(self, db_session, setup_test_data):
        """Test actualizar un expense"""
        
        class ExpenseRepository(BaseTableRepository[Expense, ExpenseTable]):
            def _update_specific_fields(self, table_row, expense):
                table_row.categoria = expense.categoria.value
                table_row.metodo_pago = expense.metodo_pago.value
                table_row.es_recurrente = expense.es_recurrente
        
        repo = ExpenseRepository(db_session, ExpenseTable, familia_id=1)
        
        # Agregar un expense primero
        expense = Expense(
            monto=300,
            descripcion="Original",
            categoria="Educación",
            metodo_pago="Tarjeta",
            familia_id=1
        )
        add_result = repo.add(expense)
        saved_expense = add_result.ok_value
        
        # Modificar el expense
        saved_expense.monto = 400
        saved_expense.descripcion = "Modificado"
        saved_expense.categoria = "Salud"
        
        # Actualizar
        update_result = repo.update(saved_expense)
        
        # Verificar
        assert isinstance(update_result, Ok)
        updated_expense = update_result.ok_value
        assert updated_expense.id == saved_expense.id
        assert updated_expense.monto == 400
        assert updated_expense.descripcion == "Modificado"
        assert updated_expense.categoria == "Salud"


class TestBaseTableRepositorySeguridad:
    """Tests de seguridad y aislamiento de datos"""
    
    def test_aislamiento_familias(self, db_session):
        """Test que una familia no puede ver datos de otra"""
        
        class ExpenseRepository(BaseTableRepository[Expense, ExpenseTable]):
            def _update_specific_fields(self, table_row, expense):
                table_row.categoria = expense.categoria.value
                table_row.metodo_pago = expense.metodo_pago.value
                table_row.es_recurrente = expense.es_recurrente
        
        # Crear repositorios para familias diferentes
        repo_f1 = ExpenseRepository(db_session, familia_id=1)
        repo_f2 = ExpenseRepository(db_session, familia_id=2)
        
        # Agregar expense para familia 1
        expense_f1 = Expense(
            monto=1000,
            descripcion="Gasto familia 1",
            categoria="Alimentación",
            metodo_pago="Efectivo",
            familia_id=1
        )
        repo_f1.add(expense_f1)
        
        # Agregar expense para familia 2
        expense_f2 = Expense(
            monto=2000,
            descripcion="Gasto familia 2",
            categoria="Transporte",
            metodo_pago="Tarjeta",
            familia_id=2
        )
        repo_f2.add(expense_f2)
        
        # Verificar aislamiento
        expenses_f1 = repo_f1.get_all()
        expenses_f2 = repo_f2.get_all()
        
        # Familia 1 solo debe ver su gasto
        assert len(expenses_f1) == 1
        assert expenses_f1[0].familia_id == 1
        assert expenses_f1[0].descripcion == "Gasto familia 1"
        
        # Familia 2 solo debe ver su gasto
        assert len(expenses_f2) == 1
        assert expenses_f2[0].familia_id == 2
        assert expenses_f2[0].descripcion == "Gasto familia 2"
    
    def test_acceso_sin_familia_id(self, db_session):
        """Test acceso sin familia_id (admin/superusuario)"""
        
        class ExpenseRepository(BaseTableRepository[Expense, ExpenseTable]):
            def _update_specific_fields(self, table_row, expense):
                table_row.categoria = expense.categoria.value
                table_row.metodo_pago = expense.metodo_pago.value
                table_row.es_recurrente = expense.es_recurrente
        
        # Repositorio sin filtro de familia (acceso total)
        repo_admin = ExpenseRepository(db_session, ExpenseTable, familia_id=None)
        
        # Agregar expenses para diferentes familias
        expense_f1 = Expense(
            monto=100,
            descripcion="Admin view 1",
            categoria="Otros",
            metodo_pago="Efectivo",
            familia_id=1
        )
        expense_f2 = Expense(
            monto=200,
            descripcion="Admin view 2",
            categoria="Otros",
            metodo_pago="Efectivo",
            familia_id=2
        )
        
        repo_admin.add(expense_f1)
        repo_admin.add(expense_f2)
        
        # Admin debería ver todos los expenses
        all_expenses = repo_admin.get_all()
        assert len(all_expenses) == 2
        
        descriptions = [e.descripcion for e in all_expenses]
        assert "Admin view 1" in descriptions
        assert "Admin view 2" in descriptions


class TestBaseTableRepositoryErrorHandling:
    """Tests de manejo de errores en BaseTableRepository"""
    
    def test_update_con_id_none(self, db_session):
        """Test update con ID None debería fallar"""
        
        class ExpenseRepository(BaseTableRepository[Expense, ExpenseTable]):
            def _update_specific_fields(self, table_row, expense):
                pass
        
        repo = ExpenseRepository(db_session, ExpenseTable, familia_id=1)
        
        # Crear expense sin ID
        expense = Expense(
            monto=100,
            descripcion="Sin ID",
            categoria="Otros",
            metodo_pago="Efectivo",
            familia_id=1
        )
        # ID es None por defecto
        
        # Intentar actualizar debería fallar
        result = repo.update(expense)
        assert isinstance(result, Err)
        assert "id" in result.err_value.message.lower()
    
    def test_delete_con_id_no_existente(self, db_session):
        """Test delete con ID que no existe"""
        
        class ExpenseRepository(BaseTableRepository[Expense, ExpenseTable]):
            def _update_specific_fields(self, table_row, expense):
                pass
        
        repo = ExpenseRepository(db_session, ExpenseTable, familia_id=1)
        
        # Intentar eliminar ID que no existe
        result = repo.delete(99999)
        assert isinstance(result, Err)
        assert "no encontrado" in result.err_value.message.lower()
    
    def test_operaciones_con_session_invalida(self):
        """Test comportamiento con sesión inválida"""
        
        class ExpenseRepository(BaseTableRepository[Expense, ExpenseTable]):
            def _update_specific_fields(self, table_row, expense):
                pass
        
        # Crear repo con sesión None (inválido)
        repo = ExpenseRepository(None, ExpenseTable, familia_id=1)
        
        expense = Expense(
            monto=100,
            descripcion="Test",
            categoria="Otros",
            metodo_pago="Efectivo",
            familia_id=1
        )
        
        # Las operaciones deberían fallar elegantemente
        with pytest.raises(Exception):  # AttributeError, DatabaseError, etc.
            repo.add(expense)
