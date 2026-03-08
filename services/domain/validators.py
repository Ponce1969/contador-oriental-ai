"""
Validadores comunes centralizados para los services.
Evita duplicar las mismas validaciones en ExpenseService,
IncomeService y FamilyMemberService.
"""

from __future__ import annotations

from result import Err, Ok, Result

from constants.messages import ValidationMessages
from models.errors import ValidationError


def validate_monto_positivo(monto: float) -> Result[None, ValidationError]:
    """Valida que el monto sea mayor a 0."""
    if monto <= 0:
        return Err(ValidationError(message=ValidationMessages.MONTO_POSITIVO))
    return Ok(None)


def validate_descripcion_requerida(
    descripcion: str | None,
) -> Result[None, ValidationError]:
    """Valida que la descripción no esté vacía."""
    if not descripcion or descripcion.strip() == "":
        return Err(ValidationError(message=ValidationMessages.DESCRIPCION_REQUERIDA))
    return Ok(None)


def validate_id_requerido(
    id_value: int | None, mensaje: str
) -> Result[None, ValidationError]:
    """Valida que el ID no sea None (para operaciones de update)."""
    if id_value is None:
        return Err(ValidationError(message=mensaje))
    return Ok(None)


def validate_recurrente_con_frecuencia(
    es_recurrente: bool,
    frecuencia: str | None,
    mensaje: str,
) -> Result[None, ValidationError]:
    """Valida que un ítem recurrente tenga frecuencia definida."""
    if es_recurrente and not frecuencia:
        return Err(ValidationError(message=mensaje))
    return Ok(None)
