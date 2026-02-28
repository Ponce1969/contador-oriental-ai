"""
Tests para BaseTableRepository - Corazón del CRUD genérico del Escudo Charrúa
"""

import pytest
from sqlalchemy.orm import Session
from result import Err, Ok

from repositories.base_table_repository import BaseTableRepository
from repositories.expense_repository import ExpenseRepository
from repositories.income_repository import IncomeRepository
from models.expense_model import Expense
from models.income_model import Income
from models.categories import ExpenseCategory, PaymentMethod
from models.income_model import IncomeCategory
from database.tables import ExpenseTable, IncomeTable
from datetime import date


def _make_expense(
    descripcion="Test expense",
    monto=1000.0,
    familia_id=1,
):
    return Expense(
        monto=monto,
        fecha=date.today(),
        descripcion=descripcion,
        categoria=ExpenseCategory.ALMACEN,
        metodo_pago=PaymentMethod.EFECTIVO,
        es_recurrente=False,
    )


def _make_income(
    descripcion="Sueldo",
    monto=50000.0,
    family_member_id=1,
):
    return Income(
        monto=monto,
        fecha=date.today(),
        descripcion=descripcion,
        categoria=IncomeCategory.SUELDO,
        es_recurrente=False,
        family_member_id=family_member_id,
    )


class TestBaseTableRepository:
    """Tests para BaseTableRepository"""

    def test_base_repository_instantiation(self, db_session):
        """Test que BaseTableRepository puede instanciarse correctamente"""
        repo = ExpenseRepository(db_session, familia_id=1)
        assert repo.session == db_session
        assert repo.table_model == ExpenseTable
        assert repo.familia_id == 1

    def test_base_repository_sin_familia_id(self, db_session):
        """Test BaseTableRepository sin familia_id"""
        repo = ExpenseRepository(db_session)
        assert repo.familia_id is None

    def test_filter_by_family_con_familia_id(self, db_session):
        """Test que _filter_by_family aplica filtro correctamente"""
        repo = ExpenseRepository(db_session, familia_id=42)
        query = db_session.query(ExpenseTable)
        filtered_query = repo._filter_by_family(query)
        assert filtered_query is not None

    def test_filter_by_family_sin_familia_id(self, db_session):
        """Test que _filter_by_family no filtra cuando familia_id es None"""
        repo = ExpenseRepository(db_session, familia_id=None)
        query = db_session.query(ExpenseTable)
        filtered_query = repo._filter_by_family(query)
        assert filtered_query == query


class TestBaseTableRepositoryCRUD:
    """Tests de operaciones CRUD del BaseTableRepository"""

    def test_add_expense(self, db_session, setup_test_data):
        """Test agregar un expense usando ExpenseRepository real"""
        repo = ExpenseRepository(db_session, familia_id=1)
        expense = _make_expense(descripcion="Test expense", monto=1000)
        result = repo.add(expense)
        assert isinstance(result, Ok)
        saved = result.ok_value
        assert saved.id is not None
        assert saved.descripcion == "Test expense"
        assert saved.monto == 1000

    def test_add_income(self, db_session):
        """Test agregar un income usando IncomeRepository real"""
        repo = IncomeRepository(db_session, familia_id=1)
        income = _make_income(descripcion="Sueldo", monto=50000)
        result = repo.add(income)
        assert isinstance(result, Ok)
        saved = result.ok_value
        assert saved.id is not None
        assert saved.descripcion == "Sueldo"
        assert saved.monto == 50000

    def test_get_all_con_filtro_familia(self, db_session, setup_test_data):
        """Test get_all filtra por familia_id correctamente"""
        fid1 = setup_test_data["familia_id_1"]
        fid2 = setup_test_data["familia_id_2"]
        repo_f1 = ExpenseRepository(db_session, familia_id=fid1)
        repo_f2 = ExpenseRepository(db_session, familia_id=fid2)
        repo_f1.add(_make_expense(descripcion="Solo familia 1"))
        repo_f2.add(_make_expense(descripcion="Solo familia 2"))
        desc_f1 = [e.descripcion for e in repo_f1.get_all()]
        desc_f2 = [e.descripcion for e in repo_f2.get_all()]
        assert "Solo familia 1" in desc_f1
        assert "Solo familia 2" not in desc_f1
        assert "Solo familia 2" in desc_f2
        assert "Solo familia 1" not in desc_f2

    def test_get_by_id_existente(self, db_session, setup_test_data):
        """Test get_by_id con un registro existente"""
        repo = ExpenseRepository(db_session, familia_id=1)
        expense = _make_expense(descripcion="Test get by ID", monto=500)
        add_result = repo.add(expense)
        saved = add_result.ok_value
        get_result = repo.get_by_id(saved.id)
        assert isinstance(get_result, Ok)
        assert get_result.ok_value.descripcion == "Test get by ID"

    def test_get_by_id_no_existente(self, db_session):
        """Test get_by_id con un ID que no existe"""
        repo = ExpenseRepository(db_session, familia_id=1)
        result = repo.get_by_id(99999)
        assert isinstance(result, Err)
        assert "no encontrado" in result.err_value.message.lower()

    def test_delete_expense(self, db_session, setup_test_data):
        """Test eliminar un expense"""
        repo = ExpenseRepository(db_session, familia_id=1)
        expense = _make_expense(descripcion="Para eliminar", monto=200)
        saved = repo.add(expense).ok_value
        assert isinstance(repo.delete(saved.id), Ok)
        assert isinstance(repo.get_by_id(saved.id), Err)

    def test_update_expense(self, db_session, setup_test_data):
        """Test actualizar un expense"""
        repo = ExpenseRepository(db_session, familia_id=1)
        expense = _make_expense(descripcion="Original", monto=300)
        saved = repo.add(expense).ok_value
        saved.monto = 400
        saved.descripcion = "Modificado"
        update_result = repo.update(saved)
        assert isinstance(update_result, Ok)
        assert update_result.ok_value.monto == 400
        assert update_result.ok_value.descripcion == "Modificado"


class TestBaseTableRepositorySeguridad:
    """Tests de seguridad y aislamiento de datos"""

    def test_aislamiento_familias(self, db_session):
        """Test que una familia no puede ver datos de otra"""
        repo_f1 = ExpenseRepository(db_session, familia_id=1)
        repo_f2 = ExpenseRepository(db_session, familia_id=2)
        repo_f1.add(_make_expense(descripcion="Gasto familia 1", monto=1000))
        repo_f2.add(_make_expense(descripcion="Gasto familia 2", monto=2000))
        desc_f1 = [e.descripcion for e in repo_f1.get_all()]
        desc_f2 = [e.descripcion for e in repo_f2.get_all()]
        assert "Gasto familia 1" in desc_f1
        assert "Gasto familia 2" not in desc_f1
        assert "Gasto familia 2" in desc_f2
        assert "Gasto familia 1" not in desc_f2

    def test_acceso_sin_familia_id(self, db_session):
        """Test que sin familia_id se ven todos los datos"""
        repo_f1 = ExpenseRepository(db_session, familia_id=1)
        repo_f2 = ExpenseRepository(db_session, familia_id=2)
        repo_f1.add(_make_expense(descripcion="Admin view 1", monto=100))
        repo_f2.add(_make_expense(descripcion="Admin view 2", monto=200))
        repo_admin = ExpenseRepository(db_session, familia_id=None)
        all_expenses = repo_admin.get_all()
        descriptions = [e.descripcion for e in all_expenses]
        assert "Admin view 1" in descriptions
        assert "Admin view 2" in descriptions


class TestBaseTableRepositoryErrorHandling:
    """Tests de manejo de errores en BaseTableRepository"""

    def test_update_con_id_none(self, db_session):
        """Test update con ID None debería fallar"""
        repo = ExpenseRepository(db_session, familia_id=1)
        expense = _make_expense(descripcion="Sin ID", monto=100)
        result = repo.update(expense)
        assert isinstance(result, Err)
        assert "id" in result.err_value.message.lower()

    def test_delete_con_id_no_existente(self, db_session):
        """Test delete con ID que no existe"""
        repo = ExpenseRepository(db_session, familia_id=1)
        result = repo.delete(99999)
        assert isinstance(result, Err)
        assert "no encontrado" in result.err_value.message.lower()

    def test_operaciones_con_session_invalida(self):
        """Test comportamiento con sesión inválida"""
        repo = ExpenseRepository(None, familia_id=1)
        expense = _make_expense(descripcion="Test", monto=100)
        result = repo.add(expense)
        assert isinstance(result, Err)
