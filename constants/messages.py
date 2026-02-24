"""
Mensajes de validación y error centralizados.
Evita strings mágicos duplicados en services y controllers.
"""

from __future__ import annotations


class ValidationMessages:
    MONTO_POSITIVO = "El monto debe ser mayor a 0"
    DESCRIPCION_REQUERIDA = "La descripción es obligatoria"
    ID_REQUERIDO_GASTO = "El gasto debe tener un ID"
    ID_REQUERIDO_INGRESO = "El ingreso debe tener un ID"
    ID_REQUERIDO_MIEMBRO = "El miembro debe tener un ID"
    RECURRENTE_SIN_FRECUENCIA_GASTO = "Los gastos recurrentes deben tener frecuencia"
    RECURRENTE_SIN_FRECUENCIA_INGRESO = (
        "Los ingresos recurrentes deben tener frecuencia"
    )
    MIEMBRO_REQUERIDO = "Debe seleccionar un miembro de la familia"
    NOMBRE_REQUERIDO = "El nombre es obligatorio"
    TIPO_MIEMBRO_INVALIDO = "Tipo de miembro inválido"
    PARENTESCO_REQUERIDO = "Las personas deben tener parentesco"
    ESPECIE_REQUERIDA = "Las mascotas deben tener especie"
