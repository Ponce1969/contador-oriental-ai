"""Tests para format_pesos_ai y format_cotizacion - formato inequivoco para IA y UI."""

from datetime import date
from decimal import Decimal

from models.categories import ExpenseCategory, PaymentMethod
from models.expense_model import Expense
from services.ai.expense_formatters import agrupar_gastos
from services.infrastructure.formatters import (
    format_cotizacion,
    format_pesos,
    format_pesos_ai,
)


class TestFormatPesosAi:
    def test_small_amount(self):
        assert format_pesos_ai(Decimal("650")) == "$ 650"

    def test_thousands(self):
        assert format_pesos_ai(Decimal("18480")) == "$ 18480"

    def test_hundred_thousands(self):
        assert format_pesos_ai(Decimal("173720")) == "$ 173720"

    def test_millions(self):
        assert format_pesos_ai(Decimal("1234567")) == "$ 1234567"

    def test_zero(self):
        assert format_pesos_ai(Decimal("0")) == "$ 0"

    def test_rounding(self):
        assert format_pesos_ai(Decimal("770.50")) == "$ 771"

    def test_no_decimal_point(self):
        result = format_pesos_ai(Decimal("173720"))
        assert "." not in result

    def test_no_thousand_separator(self):
        """Sin separador de miles para evitar confusion en IAs."""
        result = format_pesos_ai(Decimal("50000"))
        assert result == "$ 50000"
        assert " " not in result[2:]  # Sin espacios después del "$ "

    def test_different_from_format_pesos(self):
        assert format_pesos(Decimal("173720")) != format_pesos_ai(Decimal("173720"))

    def test_int_input(self):
        assert format_pesos_ai(12990) == "$ 12990"


class TestFormatCotizacion:
    def test_standard_rate(self):
        assert format_cotizacion(Decimal("40.01")) == "$ 40,01"

    def test_trailing_zeros(self):
        assert format_cotizacion(Decimal("40.0100")) == "$ 40,01"

    def test_whole_number(self):
        assert format_cotizacion(Decimal("42")) == "$ 42,00"

    def test_half(self):
        assert format_cotizacion(Decimal("42.5")) == "$ 42,50"

    def test_rounding_up(self):
        assert format_cotizacion(Decimal("42.505")) == "$ 42,51"

    def test_rounding_down(self):
        assert format_cotizacion(Decimal("42.504")) == "$ 42,50"

    def test_large_rate(self):
        assert format_cotizacion(Decimal("1234.56")) == "$ 1.234,56"

    def test_no_more_than_2_decimals(self):
        result = format_cotizacion(Decimal("40.0100"))
        # No debe mostrar 4 decimales
        assert result == "$ 40,01"
        # No debe tener punto como separador decimal
        assert ".01" not in result

    def test_comma_as_decimal_separator(self):
        result = format_cotizacion(Decimal("40.01"))
        assert ",01" in result


class TestFormatPesosCurrency:
    """Tests para format_pesos según moneda: USD con centavos, UYU entero."""

    def test_format_pesos_usd_two_decimals(self):
        """USD debe mostrar 2 decimales."""
        assert format_pesos(Decimal("1250.50"), "USD") == "USD 1.250,50"

    def test_format_pesos_uyu_integer(self):
        """UYU debe redondear al entero sin decimales."""
        assert format_pesos(Decimal("18480.70"), "UYU") == "$ 18.481"

    def test_format_pesos_ai_usd_two_decimals(self):
        """format_pesos_ai USD sin separador de miles y con punto decimal."""
        assert format_pesos_ai(Decimal("1250.50"), "USD") == "USD 1250.50"

    def test_format_pesos_ai_uyu_integer(self):
        """format_pesos_ai UYU redondea al entero."""
        assert format_pesos_ai(Decimal("770.50"), "UYU") == "$ 771"


class TestAgruparGastosCurrency:
    """Tests para agrupar_gastos con múltiples monedas."""

    def _expense(self, monto: str, currency: str, desc: str, cat: ExpenseCategory):
        return Expense(
            monto=Decimal(monto),
            currency=currency,
            fecha=date(2026, 2, 1),
            descripcion=desc,
            categoria=cat,
            metodo_pago=PaymentMethod.EFECTIVO,
        )

    def test_mixed_currency_same_category_stays_separate(self):
        """Misma categoría con distinta moneda produce subtotales separados."""
        gastos = [
            self._expense("1000", "UYU", "transporte local", ExpenseCategory.VEHICULOS),
            self._expense("50", "USD", "transporte taxi", ExpenseCategory.VEHICULOS),
        ]

        resultado = agrupar_gastos(gastos)

        categoria = resultado["🚗 Vehículos"]
        assert len(categoria) == 2
        assert ("Transporte local", "UYU") in categoria
        assert ("Transporte taxi", "USD") in categoria
        assert categoria[("Transporte local", "UYU")]["total"] == Decimal("1000")
        assert categoria[("Transporte taxi", "USD")]["total"] == Decimal("50")
        assert categoria[("Transporte local", "UYU")]["currency"] == "UYU"
        assert categoria[("Transporte taxi", "USD")]["currency"] == "USD"
