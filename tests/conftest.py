"""
Pytest configuration and fixtures for Fleting tests.

Los tests que requieren BD usan PostgreSQL real (la misma del proyecto).
Cada test opera dentro de una transacción que se revierte al terminar,
asegurando aislamiento sin contaminar datos de producción/desarrollo.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from database.engine import engine


@pytest.fixture(scope="function")
def db_engine():
    """Engine de PostgreSQL real (reutiliza el del proyecto)."""
    return engine


@pytest.fixture(scope="function")
def db_session(db_engine) -> Session:
    """
    Sesión de BD dentro de una transacción que se revierte al finalizar.
    Garantiza aislamiento entre tests sin tocar datos reales.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def setup_test_data(db_session):
    """Asegurar que familia_id=1 y familia_id=2 existen para tests de aislamiento."""
    db_session.execute(text(
        "INSERT INTO familias (id, nombre, email, activo, created_at) "
        "VALUES (999901, 'Test Familia 1', 'test1_fixture@test.com', true, NOW()) "
        "ON CONFLICT (id) DO NOTHING"
    ))
    db_session.execute(text(
        "INSERT INTO familias (id, nombre, email, activo, created_at) "
        "VALUES (999902, 'Test Familia 2', 'test2_fixture@test.com', true, NOW()) "
        "ON CONFLICT (id) DO NOTHING"
    ))
    db_session.flush()
    return {"familia_id_1": 999901, "familia_id_2": 999902}


@pytest.fixture
def family_member_id(db_session) -> int:
    """Crea un family_member real en la sesión de test y retorna su id."""
    result = db_session.execute(text(
        "INSERT INTO family_members (familia_id, nombre, parentesco) "
        "VALUES (1, 'Test Member Fixture', 'otro') RETURNING id"
    ))
    db_session.flush()
    return result.scalar()


@pytest.fixture
def sample_expense_data():
    """Provide sample expense data for tests."""
    from datetime import date

    from models.categories import ExpenseCategory, PaymentMethod
    
    return {
        "familia_id": 1,
        "monto": 150.50,
        "fecha": date.today(),
        "descripcion": "Compra en supermercado",
        "categoria": ExpenseCategory.ALMACEN,
        "subcategoria": "Verduras",
        "metodo_pago": PaymentMethod.EFECTIVO,
        "es_recurrente": False,
        "notas": "Nota de prueba",
    }


@pytest.fixture
def sample_income_data(family_member_id):
    """Provide sample income data for tests."""
    from datetime import date

    from models.income_model import IncomeCategory
    
    return {
        "familia_id": 1,
        "family_member_id": family_member_id,
        "monto": 2500.00,
        "fecha": date.today(),
        "descripcion": "Sueldo mensual",
        "categoria": IncomeCategory.SUELDO,
        "es_recurrente": False,
        "notas": "Pago mensual",
    }


@pytest.fixture
def sample_user_data():
    """Provide sample user data for tests."""
    return {
        "familia_id": 1,
        "username": "testuser",
        "password_hash": "hashed_password_123",
        "nombre_completo": "Usuario de Prueba",
        "activo": True,
    }
