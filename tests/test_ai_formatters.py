"""Tests para format_pesos_ai y format_cotizacion - formato inequivoco para IA y UI."""
from decimal import Decimal

from services.infrastructure.formatters import format_pesos, format_pesos_ai, format_cotizacion


class TestFormatPesosAi:
    def test_small_amount(self):
        assert format_pesos_ai(Decimal("650")) == "$ 650"

    def test_thousands(self):
        assert format_pesos_ai(Decimal("18480")) == "$ 18 480"

    def test_hundred_thousands(self):
        assert format_pesos_ai(Decimal("173720")) == "$ 173 720"

    def test_millions(self):
        assert format_pesos_ai(Decimal("1234567")) == "$ 1 234 567"

    def test_zero(self):
        assert format_pesos_ai(Decimal("0")) == "$ 0"

    def test_rounding(self):
        assert format_pesos_ai(Decimal("770.50")) == "$ 771"

    def test_no_decimal_point(self):
        result = format_pesos_ai(Decimal("173720"))
        assert "." not in result

    def test_space_as_thousand_separator(self):
        result = format_pesos_ai(Decimal("50000"))
        assert "50 000" in result

    def test_different_from_format_pesos(self):
        assert format_pesos(Decimal("173720")) != format_pesos_ai(Decimal("173720"))

    def test_int_input(self):
        assert format_pesos_ai(12990) == "$ 12 990"


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