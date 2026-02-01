"""
Tests for core utilities and configuration.
"""


class TestDatabaseConfig:
    """Test cases for database configuration."""

    def test_database_config_class(self):
        """Test database config class exists."""
        from configs.database_config import DatabaseConfig
        assert DatabaseConfig is not None
        assert DatabaseConfig.DB_TYPE == "sqlite"

    def test_get_database_url_sqlite(self):
        """Test getting SQLite database URL."""
        from configs.database_config import DatabaseConfig
        url = DatabaseConfig.get_database_url()
        assert url.startswith("sqlite:///")

    def test_is_postgresql(self):
        """Test is_postgresql check."""
        from configs.database_config import DatabaseConfig
        # Default is sqlite
        assert DatabaseConfig.is_postgresql() is False


class TestSQLAlchemySession:
    """Test cases for SQLAlchemy session management."""

    def test_get_db_session(self):
        """Test getting database session."""
        from core.sqlalchemy_session import get_db_session
        with get_db_session() as session:
            assert session is not None


class TestMappers:
    """Test cases for repository mappers."""

    def test_expense_to_domain(self):
        """Test expense table to domain conversion."""
        from database.tables import ExpenseTable
        from repositories.mappers import to_domain
        from datetime import date

        table_row = ExpenseTable(
            id=1,
            monto=100.00,
            fecha=date.today(),
            descripcion="Test",
            categoria="🛒 Almacén",
            subcategoria=None,
            metodo_pago="Efectivo",
            es_recurrente=False,
            frecuencia=None,
            notas=None,
        )
        expense = to_domain(table_row)
        assert expense.monto == 100.00
        assert expense.descripcion == "Test"

    def test_expense_to_table(self):
        """Test expense domain to table conversion."""
        from models.expense_model import Expense
        from models.categories import ExpenseCategory, PaymentMethod
        from repositories.mappers import to_table
        from datetime import date

        expense = Expense(
            monto=150.00,
            fecha=date.today(),
            descripcion="Test expense",
            categoria=ExpenseCategory.ALMACEN,
            subcategoria="Verduras",
            metodo_pago=PaymentMethod.EFECTIVO,
            es_recurrente=False,
            notas="Nota de prueba",
        )
        table_row = to_table(expense)
        assert table_row.monto == 150.00
        assert table_row.descripcion == "Test expense"
