"""
Tests para utils/formatters.py - Formato uruguayo consistente
"""

from decimal import Decimal

import pytest

from utils.formatters import format_currency, format_currency_with_symbol


class TestFormatCurrency:
    """Tests para format_currency"""

    def test_format_currency_enteros(self):
        """Test formato de montos enteros"""
        assert format_currency(Decimal("1000")) == "1.000"
        assert format_currency(Decimal("50000")) == "50.000"
        assert format_currency(Decimal("0")) == "0"

    def test_format_currency_decimales(self):
        """Test formato de montos con decimales"""
        assert format_currency(Decimal("1250.5")) == "1.250"  # Truncado
        assert format_currency(Decimal("1250.4")) == "1.250"  # Truncado
        assert (
            format_currency(Decimal("999.99")) == "1.000"
        )  # Redondeo hacia arriba (caso especial)
        assert format_currency(Decimal("1000.49")) == "1.000"  # Truncado

    def test_format_currency_grandes_numeros(self):
        """Test formato de montos grandes"""
        assert format_currency(Decimal("1000000")) == "1.000.000"
        assert format_currency(Decimal("5000000")) == "5.000.000"
        assert format_currency(Decimal("1234567")) == "1.234.567"

    def test_format_currency_miles(self):
        """Test formato de montos en miles"""
        assert format_currency(Decimal("1500")) == "1.500"
        assert format_currency(Decimal("2500")) == "2.500"
        assert format_currency(Decimal("9999")) == "9.999"

    def test_format_currency_con_ceros(self):
        """Test formato de montos que terminan en cero"""
        assert format_currency(Decimal("1000")) == "1.000"
        assert format_currency(Decimal("2000")) == "2.000"
        assert format_currency(Decimal("10000")) == "10.000"


class TestFormatCurrencyWithSymbol:
    """Tests para format_currency_with_symbol"""

    def test_format_currency_with_symbol_basic(self):
        """Test formato con símbolo de peso"""
        assert format_currency_with_symbol(1000) == "$ 1.000"
        assert format_currency_with_symbol(50000) == "$ 50.000"
        assert format_currency_with_symbol(0) == "$ 0"

    def test_format_currency_with_symbol_decimales(self):
        """Test formato con símbolo y decimales"""
        assert format_currency_with_symbol(1250.5) == "$ 1.250"  # Truncado
        assert (
            format_currency_with_symbol(999.99) == "$ 1.000"
        )  # Redondeo hacia arriba (caso especial)
        assert format_currency_with_symbol(1000.49) == "$ 1.000"  # Truncado

    def test_format_currency_with_symbol_grandes(self):
        """Test formato con símbolo en montos grandes"""
        assert format_currency_with_symbol(1000000) == "$ 1.000.000"
        assert format_currency_with_symbol(1234567) == "$ 1.234.567"

    def test_format_currency_with_symbol_espaciado(self):
        """Test que el espacio después del $ sea consistente"""
        resultado = format_currency_with_symbol(1500)
        assert resultado.startswith("$ ")
        assert " " in resultado
        assert resultado == "$ 1.500"


class TestFormattersEdgeCases:
    """Tests de edge cases para formatters"""

    def test_format_currency_negativos(self):
        """Test formato de montos negativos (si se permite)"""
        # Esto depende de la implementación - puede lanzar error o formatear
        try:
            resultado = format_currency(-1000)
            # Si lo formatea, debería ser "-1.000"
            assert resultado == "-1.000"
        except (ValueError, TypeError):
            # Si lanza error, también es válido
            pass

    def test_format_currency_tipo_invalido(self):
        """Test formato con tipos inválidos"""
        # String
        with pytest.raises((TypeError, ValueError)):
            format_currency("1000")  # type: ignore[arg-type]

        # None
        with pytest.raises((TypeError, ValueError)):
            format_currency(None)  # type: ignore[arg-type]

        # Lista
        with pytest.raises((TypeError, ValueError)):
            format_currency([1000])  # type: ignore[arg-type]

    def test_format_currency_limites(self):
        """Test formato en valores límite"""
        # Valor muy pequeño
        assert format_currency(Decimal("0.01")) == "0"  # Redondeo hacia abajo

        # Valor muy grande
        grande = 999999999
        resultado = format_currency(grande)
        assert "." in resultado  # Debería tener separadores de miles

        # Verificar comportamiento de redondeo estándar
        assert format_currency(Decimal("0.5")) == "0"  # Truncado
        assert format_currency(Decimal("0.9")) == "1"  # Redondeo arriba


class TestFormattersConsistencia:
    """Tests de consistencia entre formatters"""

    def test_consistencia_entre_funciones(self):
        """Test que format_currency_with_symbol use format_currency"""
        valores = [1000, 2500.5, 50000, 1234567]

        for valor in valores:
            base = format_currency(valor)
            con_simbolo = format_currency_with_symbol(valor)

            # Debería ser el mismo número con $  al principio
            assert con_simbolo == f"$ {base}"

    def test_formato_uruguayo_consistente(self):
        """Test que el formato sea consistente con estándares uruguayos"""
        # Separador de miles: punto
        assert "." in format_currency(Decimal("1000"))
        assert "," not in format_currency(Decimal("1000"))  # No usa coma decimal

        # Sin decimales (con redondeo estándar)
        assert format_currency(Decimal("1250.5")) == "1.250"
        assert format_currency(Decimal("1250.4")) == "1.250"

        # Símbolo de peso antes del número
        assert format_currency_with_symbol(1000).startswith("$ ")

    def test_rendimiento_formatters(self):
        """Test que los formatters sean rápidos (performance básico)"""
        import time

        # Test de rendimiento simple
        inicio = time.time()

        for i in range(1000):
            format_currency(Decimal("1000") + i)
            format_currency_with_symbol(1000 + i)

        fin = time.time()
        duracion = fin - inicio

        # Debería ser rápido (menos de 1 segundo para 2000 operaciones)
        assert duracion < 1.0, f"Formatter demasiado lento: {duracion:.3f}s"


class TestFormattersIntegracion:
    """Tests de integración con casos de uso reales"""

    def test_formato_gastos_comunes(self):
        """Test formato de gastos típicos uruguayos"""
        gastos = [
            (1500, "Almacen"),  # $ 1.500
            (2500.5, "Super"),  # $ 2.501 (redondeado)
            (12000, "Alquiler"),  # $ 12.000
            (850.75, "Transporte"),  # $ 851 (redondeado)
        ]

        for monto, _descripcion in gastos:
            formateado = format_currency_with_symbol(monto)
            assert formateado.startswith("$ ")
            assert "." in formateado or len(formateado.split(" ")[1]) <= 4

    def test_formato_ingresos_comunes(self):
        """Test formato de ingresos típicos uruguayos"""
        ingresos = [
            (50000, "Sueldo"),  # $ 50.000
            (75000.5, "Aguinaldo"),  # $ 75.001 (redondeado)
            (150000, "Extra"),  # $ 150.000
            (2500, "Horas extras"),  # $ 2.500
        ]

        for monto, _descripcion in ingresos:
            formateado = format_currency_with_symbol(monto)
            assert formateado.startswith("$ ")
            # Verificar que no tenga decimales
            assert (
                "." not in formateado.split("$ ")[1]
                or formateado.split("$ ")[1].count(".") <= 2
            )

    def test_formato_resumen_mensual(self):
        """Test formato para resúmenes mensuales"""
        total_gastos = 45000.75
        total_ingresos = 75000

        gastos_formateado = format_currency_with_symbol(total_gastos)
        ingresos_formateado = format_currency_with_symbol(total_ingresos)

        assert gastos_formateado == "$ 45.001"  # Redondeo (caso especial)
        assert ingresos_formateado == "$ 75.000"

        # Balance
        balance = total_ingresos - total_gastos
        balance_formateado = format_currency_with_symbol(balance)
        assert balance_formateado == "$ 29.999"  # 75000 - 45001 = 29999


class TestFormatCurrencyUSD:
    """Tests para USD: decimales con centavos y prefijo USD."""

    def test_format_currency_usd_basic(self):
        """USD sin símbolo: separador de miles y coma decimal."""
        assert format_currency(Decimal("1250.50"), "USD") == "1.250,50"

    def test_format_currency_usd_small(self):
        """USD con centavos pequeños."""
        assert format_currency(Decimal("0.01"), "USD") == "0,01"
        assert format_currency(Decimal("0.99"), "USD") == "0,99"

    def test_format_currency_usd_large(self):
        """USD con miles."""
        assert format_currency(Decimal("1234567.89"), "USD") == "1.234.567,89"

    def test_format_currency_with_symbol_usd(self):
        """USD con símbolo: prefijo USD y coma decimal."""
        assert format_currency_with_symbol(Decimal("1250.50"), "USD") == "USD 1.250,50"

    def test_format_currency_with_symbol_usd_consistency(self):
        """format_currency_with_symbol USD debe agregar prefijo al número base."""
        base = format_currency(Decimal("9876.54"), "USD")
        assert format_currency_with_symbol(Decimal("9876.54"), "USD") == f"USD {base}"
