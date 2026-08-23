from datetime import date
from decimal import Decimal

from database.tables import ExpenseTable
from models.expense_model import Expense
from models.shopping_model import ShoppingItem


def to_domain(row: ExpenseTable) -> Expense:
    """Convertir tabla de base de datos a modelo de dominio Expense"""
    from models.categories import ExpenseCategory, PaymentMethod, RecurrenceFrequency

    return Expense(
        id=row.id,
        monto=row.monto,
        currency=row.currency or "UYU",
        fecha=row.fecha,
        descripcion=row.descripcion,
        categoria=ExpenseCategory(row.categoria),
        subcategoria=row.subcategoria,
        metodo_pago=PaymentMethod(row.metodo_pago),
        es_recurrente=row.es_recurrente,
        frecuencia=(RecurrenceFrequency(row.frecuencia) if row.frecuencia else None),
        notas=row.notas,
        installment_purchase_id=row.installment_purchase_id,
        pendiente=bool(row.pendiente) if row.pendiente is not None else False,
    )


def to_table(expense: Expense) -> ExpenseTable:
    """Convertir modelo de dominio Expense a tabla de base de datos"""
    return ExpenseTable(
        monto=expense.monto,
        currency=expense.currency,
        fecha=expense.fecha,
        descripcion=expense.descripcion,
        categoria=expense.categoria.value,
        subcategoria=expense.subcategoria,
        metodo_pago=expense.metodo_pago.value,
        es_recurrente=expense.es_recurrente,
        frecuencia=expense.frecuencia.value if expense.frecuencia else None,
        notas=expense.notas,
        installment_purchase_id=expense.installment_purchase_id,
        pendiente=expense.pendiente,
    )


# Funciones legacy para compatibilidad con ShoppingItem
def shopping_to_domain(row: ExpenseTable) -> ShoppingItem:
    """Convertir tabla antigua a ShoppingItem (legacy)"""
    return ShoppingItem(
        id=row.id,
        name=row.descripcion or "",
        price=Decimal(str(row.monto)) if row.monto is not None else Decimal("0"),
        category=row.categoria or "",
        purchased=not row.pendiente if row.pendiente is not None else True,
        purchase_date=row.fecha,
    )


def shopping_to_table(item: ShoppingItem) -> ExpenseTable:
    """Convertir ShoppingItem a tabla (legacy)"""
    return ExpenseTable(
        descripcion=item.name,
        monto=item.price,
        categoria=item.category,
        fecha=item.purchase_date or date.today(),
        pendiente=not item.purchased,
    )
