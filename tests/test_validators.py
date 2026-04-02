"""
Tests para validators.py - Primera línea de defensa del Escudo Charrúa
"""

import pytest
from result import Err, Ok

from services.domain.validators import (
    validate_monto_positivo,
    validate_descripcion_requerida,
)


class TestValidateMontoPositivo:
    """Tests para validate_monto_positivo"""

    def test_monto_valido(self):
        """Caso éxito: montos positivos válidos"""
        # Montos enteros positivos
        result = validate_monto_positivo(100)
        assert isinstance(result, Ok)
        assert result.ok_value is None  # Validators retornan Ok(None) en éxito

        # Montos decimales positivos
        result = validate_monto_positivo(99.99)
        assert isinstance(result, Ok)
        assert result.ok_value is None

        # Montos grandes
        result = validate_monto_positivo(1000000)
        assert isinstance(result, Ok)
        assert result.ok_value is None

    def test_monto_cero_rechazado(self):
        """Caso error: monto igual a cero"""
        result = validate_monto_positivo(0)
        assert isinstance(result, Err)
        assert "mayor a 0" in result.err_value.message.lower()

    def test_monto_negativo_rechazado(self):
        """Caso error: montos negativos"""
        result = validate_monto_positivo(-1)
        assert isinstance(result, Err)
        assert "mayor a 0" in result.err_value.message.lower()

        result = validate_monto_positivo(-100.50)
        assert isinstance(result, Err)
        assert "mayor a 0" in result.err_value.message.lower()

    def test_monto_tipo_invalido(self):
        """Caso error: tipos de datos inválidos"""
        # Los validators no manejan tipos inválidos, eso es responsabilidad de la capa superior
        # String - esto lanzará TypeError porque no se puede comparar str <= int
        with pytest.raises(TypeError):
            validate_monto_positivo("100")

        # None - esto lanzará TypeError porque no se puede comparar None <= int
        with pytest.raises(TypeError):
            validate_monto_positivo(None)

        # Lista - esto lanzará TypeError porque no se puede comparar list <= int
        with pytest.raises(TypeError):
            validate_monto_positivo([100])


class TestValidateDescripcionRequerida:
    """Tests para validate_descripcion_requerida"""

    def test_descripcion_valida(self):
        """Caso éxito: descripciones válidas"""
        # Texto normal
        result = validate_descripcion_requerida("Sueldo mensual")
        assert isinstance(result, Ok)
        assert result.ok_value is None  # Validators retornan Ok(None) en éxito

        # Texto con números
        result = validate_descripcion_requerida("Factura 12345")
        assert isinstance(result, Ok)
        assert result.ok_value is None

        # Texto con caracteres especiales
        result = validate_descripcion_requerida("Alquiler $UYU")
        assert isinstance(result, Ok)
        assert result.ok_value is None

        # Texto largo
        result = validate_descripcion_requerida("A" * 500)
        assert isinstance(result, Ok)
        assert result.ok_value is None

    def test_descripcion_vacia_rechazada(self):
        """Caso error: string vacío"""
        result = validate_descripcion_requerida("")
        assert isinstance(result, Err)
        assert "descripción" in result.err_value.message.lower()
        assert "obligatoria" in result.err_value.message.lower()

    def test_descripcion_solo_espacios_rechazada(self):
        """Caso error: solo espacios en blanco"""
        result = validate_descripcion_requerida("   ")
        assert isinstance(result, Err)
        assert "descripción" in result.err_value.message.lower()

        result = validate_descripcion_requerida("\t\t")
        assert isinstance(result, Err)

        result = validate_descripcion_requerida("\n\n")
        assert isinstance(result, Err)

    def test_descripcion_tipo_invalido(self):
        """Caso error: tipos de datos inválidos"""
        # None es manejado correctamente por el validator (not None == True)
        result = validate_descripcion_requerida(None)
        assert isinstance(result, Err)
        assert "descripción" in result.err_value.message.lower()

        # Número - esto lanzará AttributeError porque int no tiene .strip()
        with pytest.raises(AttributeError):
            validate_descripcion_requerida(123)

        # Lista - esto lanzará AttributeError porque list no tiene .strip()
        with pytest.raises(AttributeError):
            validate_descripcion_requerida(["texto"])

        # Diccionario - esto lanzará AttributeError porque dict no tiene .strip()
        with pytest.raises(AttributeError):
            validate_descripcion_requerida({"texto": "valor"})


class TestValidatorsIntegration:
    """Tests de integración entre validators"""

    def test_validacion_combinada_gasto_valido(self):
        """Test de validación combinada para un gasto válido"""
        monto_result = validate_monto_positivo(1500)
        desc_result = validate_descripcion_requerida("Compras supermercado")

        assert monto_result.is_ok()
        assert desc_result.is_ok()

        # Validators retornan Ok(None), los valores originales se mantienen
        assert monto_result.ok_value is None
        assert desc_result.ok_value is None

        # Simular creación de gasto validado con valores originales
        gasto_validado = {
            "monto": 1500,  # Valor original validado
            "descripcion": "Compras supermercado",  # Valor original validado
        }

        assert gasto_validado["monto"] == 1500
        assert gasto_validado["descripcion"] == "Compras supermercado"

    def test_validacion_combinada_falla_monto(self):
        """Test de validación combinada cuando falla el monto"""
        monto_result = validate_monto_positivo(-100)
        desc_result = validate_descripcion_requerida("Alquiler")

        assert monto_result.is_err()
        assert desc_result.is_ok()

        # El sistema debe rechazar por el monto inválido
        assert not monto_result.is_ok()

    def test_validacion_combinada_falla_descripcion(self):
        """Test de validación combinada cuando falla la descripción"""
        monto_result = validate_monto_positivo(5000)
        desc_result = validate_descripcion_requerida("")

        assert monto_result.is_ok()
        assert desc_result.is_err()

        # El sistema debe rechazar por la descripción inválida
        assert not desc_result.is_ok()

    def test_validacion_combinada_falla_ambos(self):
        """Test de validación combinada cuando fallan ambos"""
        monto_result = validate_monto_positivo(0)
        desc_result = validate_descripcion_requerida("   ")

        assert monto_result.is_err()
        assert desc_result.is_err()

        # Ambos deben fallar
        assert not monto_result.is_ok()
        assert not desc_result.is_ok()


class TestValidatorsEdgeCases:
    """Tests de edge cases para validators"""

    def test_monto_limite_inferior(self):
        """Test montos en el límite inferior"""
        # El menor monto positivo válido
        result = validate_monto_positivo(0.01)
        assert isinstance(result, Ok)
        assert result.ok_value is None

    def test_monto_muy_pequeno(self):
        """Test montos muy pequeños pero positivos"""
        result = validate_monto_positivo(0.000001)
        assert isinstance(result, Ok)

    def test_descripcion_unicode(self):
        """Test descripciones con caracteres unicode"""
        # Emojis
        result = validate_descripcion_requerida("Sueldo 🤑")
        assert isinstance(result, Ok)

        # Acentos
        result = validate_descripcion_requerida("Alquiler del mes")
        assert isinstance(result, Ok)

        # Caracteres especiales uruguayos
        result = validate_descripcion_requerida("Gastos en $UYU")
        assert isinstance(result, Ok)
