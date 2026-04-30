from __future__ import annotations

from decimal import Decimal

from database.tables import ExpenseTable, ShoppingItemTable
from models.expense_model import Expense
from models.shopping_model import ShoppingItem


def to_domain(row: ExpenseTable) -> Expense:
    """Convertir tabla de base de datos a modelo de dominio Expense"""
    from models.categories import ExpenseCategory, PaymentMethod, RecurrenceFrequency

    return Expense(
        id=row.id,
        monto=row.monto,
        fecha=row.fecha,
        descripcion=row.descripcion,
        categoria=ExpenseCategory(row.categoria),
        subcategoria=row.subcategoria,
        metodo_pago=PaymentMethod(row.metodo_pago),
        es_recurrente=row.es_recurrente,
        frecuencia=(RecurrenceFrequency(row.frecuencia) if row.frecuencia else None),
        notas=row.notas,
        installment_purchase_id=row.installment_purchase_id,
        pendiente=row.pendiente,
    )


def to_table(expense: Expense) -> ExpenseTable:
    """Convertir modelo de dominio Expense a tabla de base de datos"""
    return ExpenseTable(
        monto=expense.monto,
        fecha=expense.fecha,
        descripcion=expense.descripcion,
        categoria=expense.categoria.value,
        subcategoria=expense.subcategoria,
        metodo_pago=expense.metodo_pago.value,
        es_recurrente=expense.es_recurrente,
        frecuencia=expense.frecuencia.value if expense.frecuencia else None,
        notas=expense.notas,
    )


# Funciones legacy para compatibilidad con ShoppingItem
def shopping_to_domain(row: ShoppingItemTable) -> ShoppingItem:
    """Convertir tabla antigua a ShoppingItem (legacy)"""
    return ShoppingItem(
        id=row.id,
        name=row.name or "",
        price=Decimal(str(row.price)) if row.price is not None else Decimal("0"),
        category=row.category or "",
        purchased=row.purchased,
        purchase_date=row.purchase_date or row.fecha,
    )


def shopping_to_table(item: ShoppingItem) -> ShoppingItemTable:
    """Convertir ShoppingItem a tabla (legacy)"""
    return ShoppingItemTable(
        name=item.name,
        price=item.price,
        category=item.category,
        purchased=item.purchased,
        purchase_date=item.purchase_date,
    )
