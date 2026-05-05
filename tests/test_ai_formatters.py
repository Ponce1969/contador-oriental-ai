"""Tests para format_pesos_ai - formato inequivoco para modelos de IA."""
from decimal import Decimal

from services.infrastructure.formatters import format_pesos, format_pesos_ai


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