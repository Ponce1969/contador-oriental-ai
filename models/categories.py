"""
Categorías y subcategorías de gastos familiares
"""

from __future__ import annotations

from enum import StrEnum


class ExpenseCategory(StrEnum):
    """Categorías principales de gastos"""

    ALMACEN = "🛒 Almacén"
    VEHICULOS = "🚗 Vehículos"
    HOGAR = "🏠 Hogar"
    SALUD = "👨‍⚕️ Salud"
    EDUCACION = "📚 Educación"
    OCIO = "🎉 Ocio"
    ROPA = "👕 Ropa"
    OTROS = "📦 Otros"


# Subcategorías por categoría principal
SUBCATEGORIES = {
    ExpenseCategory.ALMACEN: [
        "Supermercado",
        "Verdulería",
        "Carnicería",
        "Panadería",
        "Delivery comida",
        "Otros almacén",
    ],
    ExpenseCategory.VEHICULOS: [
        "Combustible",
        "Mantenimiento",
        "Seguro auto",
        "Patente",
        "Estacionamiento",
        "Peajes",
        "Otros vehículos",
    ],
    ExpenseCategory.HOGAR: [
        "Alquiler",
        "Gastos comunes",
        "UTE (Luz)",
        "OSE (Agua)",
        "Antel (Internet/Tel)",
        "Gas",
        "Limpieza",
        "Mantenimiento hogar",
        "Otros hogar",
    ],
    ExpenseCategory.SALUD: [
        "Mutualista",
        "Farmacia",
        "Médico particular",
        "Odontólogo",
        "Óptica",
        "Otros salud",
    ],
    ExpenseCategory.EDUCACION: [
        "Colegio/Cuota",
        "Materiales/Libros",
        "Cursos",
        "Otros educación",
    ],
    ExpenseCategory.OCIO: [
        "Salidas/Restaurantes",
        "Streaming (Netflix, etc)",
        "Vacaciones",
        "Deportes/Gimnasio",
        "Otros ocio",
    ],
    ExpenseCategory.ROPA: [
        "Ropa adultos",
        "Ropa niños",
        "Calzado",
        "Otros ropa",
    ],
    ExpenseCategory.OTROS: [
        "Impuestos",
        "Seguros",
        "Préstamos",
        "Varios",
    ],
}


class PaymentMethod(StrEnum):
    """Métodos de pago"""

    EFECTIVO = "Efectivo"
    TARJETA_DEBITO = "Tarjeta débito"
    TARJETA_CREDITO = "Tarjeta crédito"
    TRANSFERENCIA = "Transferencia"
    OTRO = "Otro"


class RecurrenceFrequency(StrEnum):
    """Frecuencia de gastos recurrentes"""

    DIARIA = "Diaria"
    SEMANAL = "Semanal"
    QUINCENAL = "Quincenal"
    MENSUAL = "Mensual"
    BIMESTRAL = "Bimestral"
    TRIMESTRAL = "Trimestral"
    SEMESTRAL = "Semestral"
    ANUAL = "Anual"


def get_subcategories(category: ExpenseCategory) -> list[str]:
    """Obtener subcategorías de una categoría principal"""
    return SUBCATEGORIES.get(category, [])
