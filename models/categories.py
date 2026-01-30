"""
Categorías y subcategorías de gastos familiares
"""

from __future__ import annotations

from enum import Enum


class ExpenseCategory(str, Enum):
    """Categorías principales de gastos"""
    ALMACEN = "🛒 Almacén"
    VEHICULOS = "🚗 Vehículos"
    HOGAR = "🏠 Hogar"
    SALUD = "👨‍⚕️ Salud"
    EDUCACION = "📚 Educación"
    OCIO = "🎉 Ocio"
    ROPA = "👕 Ropa"
    OTROS = "💳 Otros"


# Subcategorías por categoría principal
SUBCATEGORIES = {
    ExpenseCategory.ALMACEN: [
        "Supermercado",
        "Verdulería",
        "Carnicería",
        "Panadería",
        "Delivery comida",
        "Kiosco",
        "Otros",
    ],
    ExpenseCategory.VEHICULOS: [
        "Combustible",
        "Mantenimiento",
        "Reparaciones",
        "Seguro",
        "Patente",
        "Estacionamiento",
        "Peajes",
        "Lavado",
        "Otros",
    ],
    ExpenseCategory.HOGAR: [
        "Alquiler",
        "Luz",
        "Agua",
        "Gas",
        "Internet",
        "Teléfono",
        "Expensas",
        "Reparaciones",
        "Otros",
    ],
    ExpenseCategory.SALUD: [
        "Obra social",
        "Medicamentos",
        "Consultas médicas",
        "Odontólogo",
        "Óptica",
        "Kinesiología",
        "Otros",
    ],
    ExpenseCategory.EDUCACION: [
        "Cuota escolar",
        "Útiles",
        "Libros",
        "Cursos",
        "Universidad",
        "Transporte escolar",
        "Otros",
    ],
    ExpenseCategory.OCIO: [
        "Restaurantes",
        "Cine",
        "Streaming",
        "Deportes",
        "Viajes",
        "Regalos",
        "Otros",
    ],
    ExpenseCategory.ROPA: [
        "Ropa adultos",
        "Ropa niños",
        "Calzado",
        "Accesorios",
        "Otros",
    ],
    ExpenseCategory.OTROS: [
        "Impuestos",
        "Seguros",
        "Préstamos",
        "Varios",
    ],
}


class PaymentMethod(str, Enum):
    """Métodos de pago"""
    EFECTIVO = "Efectivo"
    TARJETA_DEBITO = "Tarjeta débito"
    TARJETA_CREDITO = "Tarjeta crédito"
    TRANSFERENCIA = "Transferencia"
    OTRO = "Otro"


class RecurrenceFrequency(str, Enum):
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
