from __future__ import annotations

from decimal import Decimal

from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session

from database.tables import ExpenseTable, FamiliaTable, SharedExpenseLinkTable
from models.household_model import SharedExpenseFeedItem, SharedExpenseLink


class SharedExpenseLinkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self, household_id: int, gasto_id: int, familia_id: int
    ) -> SharedExpenseLink:
        link = SharedExpenseLinkTable(
            household_id=household_id, gasto_id=gasto_id, familia_id=familia_id
        )
        self.session.add(link)
        self.session.flush()
        return SharedExpenseLink(
            id=link.id,
            household_id=link.household_id,
            gasto_id=link.gasto_id,
            familia_id=link.familia_id,
            linked_at=link.linked_at,
        )

    def get_by_gasto_and_household(
        self, gasto_id: int, household_id: int
    ) -> SharedExpenseLink | None:
        stmt = select(SharedExpenseLinkTable).where(
            SharedExpenseLinkTable.gasto_id == gasto_id,
            SharedExpenseLinkTable.household_id == household_id,
        )
        link = self.session.execute(stmt).scalar_one_or_none()
        if not link:
            return None
        return SharedExpenseLink(
            id=link.id,
            household_id=link.household_id,
            gasto_id=link.gasto_id,
            familia_id=link.familia_id,
            linked_at=link.linked_at,
        )

    def delete_by_gasto_and_household(self, gasto_id: int, household_id: int) -> None:
        stmt = delete(SharedExpenseLinkTable).where(
            SharedExpenseLinkTable.gasto_id == gasto_id,
            SharedExpenseLinkTable.household_id == household_id,
        )
        self.session.execute(stmt)

    def delete_all_for_member(self, household_id: int, familia_id: int) -> None:
        stmt = delete(SharedExpenseLinkTable).where(
            SharedExpenseLinkTable.household_id == household_id,
            SharedExpenseLinkTable.familia_id == familia_id,
        )
        self.session.execute(stmt)

    def delete_all_for_household(self, household_id: int) -> None:
        stmt = delete(SharedExpenseLinkTable).where(
            SharedExpenseLinkTable.household_id == household_id,
        )
        self.session.execute(stmt)

    def sum_contributions_per_member(
        self, household_id: int
    ) -> dict[tuple[int, str], Decimal]:
        """Returns dict of (familia_id, currency) -> total_amount, per-currency."""
        stmt = (
            select(
                SharedExpenseLinkTable.familia_id,
                ExpenseTable.currency,
                func.sum(ExpenseTable.monto),
            )
            .join(ExpenseTable, ExpenseTable.id == SharedExpenseLinkTable.gasto_id)
            .where(SharedExpenseLinkTable.household_id == household_id)
            .group_by(SharedExpenseLinkTable.familia_id, ExpenseTable.currency)
        )
        rows = self.session.execute(stmt).all()
        return {
            (r[0], r[1] or "UYU"): Decimal(r[2]) if r[2] else Decimal("0") for r in rows
        }

    def get_feed(
        self,
        household_id: int,
        page: int = 1,
        page_size: int = 50,
        familia_id: int | None = None,
    ) -> tuple[list[SharedExpenseFeedItem], int]:
        """Returns a list of items and the total count."""
        base_stmt = (
            select(SharedExpenseLinkTable, ExpenseTable, FamiliaTable)
            .join(ExpenseTable, ExpenseTable.id == SharedExpenseLinkTable.gasto_id)
            .join(FamiliaTable, FamiliaTable.id == SharedExpenseLinkTable.familia_id)
            .where(SharedExpenseLinkTable.household_id == household_id)
        )

        if familia_id:
            base_stmt = base_stmt.where(SharedExpenseLinkTable.familia_id == familia_id)

        # Count total
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_count = self.session.execute(count_stmt).scalar_one()

        # Fetch page
        paginated_stmt = (
            base_stmt.order_by(desc(ExpenseTable.fecha), desc(ExpenseTable.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = self.session.execute(paginated_stmt).all()

        items = [
            SharedExpenseFeedItem(
                gasto_id=exp.id,
                household_id=link.household_id,
                familia_id=fam.id,
                familia_nombre=fam.nombre,
                monto=exp.monto,
                currency=exp.currency,
                fecha=exp.fecha,
                descripcion=exp.descripcion,
                categoria=exp.categoria,
            )
            for link, exp, fam in rows
        ]

        return items, total_count
