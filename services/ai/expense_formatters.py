"""
ExpenseFormatters — Transformaciones de datos de gastos para el contexto IA.
Funciones puras: sin BD, sin async, sin estado.
"""
from __future__ import annotations

from models.expense_model import Expense


def agrupar_gastos(gastos: list[Expense]) -> dict[str, dict[str, dict]]:
    """
    Agrupa gastos por categoría y descripción para el contexto del Contador.

    Returns:
        {
            "Categoría": {
                "Descripción": {"total": float, "cantidad": int, "metodos": dict}
            }
        }
    """
    resumen: dict[str, dict[str, dict]] = {}
    for gasto in gastos:
        cat = gasto.categoria.value
        desc = gasto.descripcion.strip().capitalize()
        metodo = gasto.metodo_pago.value

        if cat not in resumen:
            resumen[cat] = {}

        if desc not in resumen[cat]:
            resumen[cat][desc] = {"total": 0.0, "cantidad": 0, "metodos": {}}

        resumen[cat][desc]["total"] += gasto.monto
        resumen[cat][desc]["cantidad"] += 1
        metodos = resumen[cat][desc]["metodos"]
        metodos[metodo] = metodos.get(metodo, 0) + 1

    return resumen


def resumir_metodos_pago(gastos: list[Expense]) -> str:
    """
    Genera un resumen de métodos de pago usados.

    Returns:
        String con el conteo por método de pago, ordenado por frecuencia.
        Ejemplo: "Tarjeta débito: 3 compras (60%), Efectivo: 2 compras (40%)"
    """
    if not gastos:
        return ""

    conteo: dict[str, int] = {}
    for gasto in gastos:
        metodo = gasto.metodo_pago.value
        conteo[metodo] = conteo.get(metodo, 0) + 1

    total = sum(conteo.values())
    partes = [
        f"{metodo}: {cant} compras ({cant * 100 // total}%)"
        for metodo, cant in sorted(conteo.items(), key=lambda x: -x[1])
    ]
    return ", ".join(partes)


def filtrar_por_categorias(
    gastos: list[Expense],
    categorias: list[str],
) -> list[Expense]:
    """
    Filtra gastos según las categorías detectadas por QueryAnalyzer.
    Si no hay categorías, retorna todos (consulta general).

    Args:
        gastos: Lista completa de gastos del período
        categorias: Valores exactos de categoría con emojis (de CATEGORY_KEYWORDS)

    Returns:
        Gastos filtrados o lista completa si categorias está vacía
    """
    if not categorias:
        return gastos
    return [g for g in gastos if g.categoria.value in categorias]
