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

    # Categorías rurales / campo
    AGRO_COMBUSTIBLE = "🚜 Gasoil y Maquinaria"
    AGRO_INSUMOS = "🌱 Semillas y Agroquímicos"
    AGRO_LABORAL = "👥 Jornales y BPS Rural"
    AGRO_LOGISTICA = "🚛 Fletes y Logística"
    AGRO_VETERINARIA = "🐄 Sanidad y Ganado"
    AGRO_MANTENIMIENTO = "🔧 Alambrados y Mejoras"
    AGRO_OTROS = "🌾 Otros Campo"


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
    ExpenseCategory.AGRO_COMBUSTIBLE: [
        "Gasoil",
        "Aceites y lubricantes",
        "Repuestos de maquinaria",
        "Mantenimiento tractor",
        "Otros combustible/maquinaria",
    ],
    ExpenseCategory.AGRO_INSUMOS: [
        "Semillas",
        "Fertilizantes",
        "Herbicidas y agroquímicos",
        "Raciones y forrajes",
        "Otros insumos",
    ],
    ExpenseCategory.AGRO_LABORAL: [
        "Jornales peones",
        "BPS Rural / Aportes",
        "Esquila / Zafrales",
        "Comida personal de campo",
        "Otros laboral rural",
    ],
    ExpenseCategory.AGRO_LOGISTICA: [
        "Flete de ganado",
        "Flete de granos",
        "Guías de campo / DICOSE",
        "Balanzas y peajes",
        "Otros logística",
    ],
    ExpenseCategory.AGRO_VETERINARIA: [
        "Vacunas y específicos",
        "Honorarios veterinarios",
        "Caravanas e identificación",
        "Suplementos minerales",
        "Otros veterinaria",
    ],
    ExpenseCategory.AGRO_MANTENIMIENTO: [
        "Alambrados y postes",
        "Aguadas, bombas y molinos",
        "Caminería y porteras",
        "Taller y herramientas",
        "Otros mejoras",
    ],
    ExpenseCategory.AGRO_OTROS: [
        "Impuestos rurales / Contribución",
        "Seguro de granizo/cosecha",
        "Arrendamiento de campo",
        "Varios campo",
    ],
}


CATEGORIES_HOGAR: list[ExpenseCategory] = [
    ExpenseCategory.ALMACEN,
    ExpenseCategory.VEHICULOS,
    ExpenseCategory.HOGAR,
    ExpenseCategory.SALUD,
    ExpenseCategory.EDUCACION,
    ExpenseCategory.OCIO,
    ExpenseCategory.ROPA,
    ExpenseCategory.OTROS,
]

CATEGORIES_CAMPO: list[ExpenseCategory] = [
    ExpenseCategory.AGRO_COMBUSTIBLE,
    ExpenseCategory.AGRO_INSUMOS,
    ExpenseCategory.AGRO_LABORAL,
    ExpenseCategory.AGRO_LOGISTICA,
    ExpenseCategory.AGRO_VETERINARIA,
    ExpenseCategory.AGRO_MANTENIMIENTO,
    ExpenseCategory.AGRO_OTROS,
]


def get_categories_for_entorno(
    entorno: str | None = "hogar",
) -> list[ExpenseCategory]:
    """Retorna las categorías correspondientes al entorno (hogar, campo o todas)."""
    if entorno == "campo":
        return CATEGORIES_CAMPO
    if entorno in ("consolidado", "all", None):
        return list(ExpenseCategory)
    return CATEGORIES_HOGAR


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
