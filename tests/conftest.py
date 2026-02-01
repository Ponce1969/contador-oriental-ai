"""
Pytest configuration and fixtures for Fleting tests.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from database.tables import Base


@pytest.fixture
def temp_db_path():
    """Provide a temporary database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def db_engine(temp_db_path):
    """Create a test database engine with all required tables."""
    engine = create_engine(f"sqlite:///{temp_db_path}")
    
    # Create familias table FIRST (before other tables with FKs)
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS familias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT UNIQUE,
                activo BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                familia_id INTEGER NOT NULL,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                nombre_completo TEXT,
                activo BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                FOREIGN KEY (familia_id) REFERENCES familias (id)
            )
        """))
        conn.execute(text("""
            INSERT INTO familias (id, nombre, email, activo)
            VALUES (1, 'Familia Test', 'test@test.com', 1)
        """))
        conn.commit()
    
    # Create base tables (they have FKs to familias)
    Base.metadata.create_all(engine)
    
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Session:
    """Provide a database session for tests."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


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
def sample_income_data():
    """Provide sample income data for tests."""
    from datetime import date
    from models.income_model import IncomeCategory
    
    return {
        "familia_id": 1,
        "family_member_id": 1,
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
