import logging

from core.events import Event, EventType, event_system
from core.unit_of_work import UnitOfWork
from repositories.expense_repository import ExpenseRepository
from repositories.memoria_repository import MemoriaRepository
from services.ai.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class HouseholdMemoryHandler:
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self._register_handlers()

    def _register_handlers(self) -> None:
        event_system.subscribe(
            EventType.SHARED_EXPENSE_LINK_CREADO, self.handle_shared_expense_link_creado
        )
        event_system.subscribe(
            EventType.SHARED_EXPENSE_LINK_ELIMINADO,
            self.handle_shared_expense_link_eliminado,
        )
        event_system.subscribe(
            EventType.SETTLEMENT_CREADO, self.handle_settlement_creado
        )

    async def handle_shared_expense_link_creado(self, event: Event) -> None:
        try:
            household_id = event.data["household_id"]
            gasto_id = event.data["gasto_id"]
            familia_id = event.data["familia_id"]

            with UnitOfWork() as uow:
                expense_repo = ExpenseRepository(uow.session, familia_id=familia_id)
                gasto_res = expense_repo.get_by_id(gasto_id)
                if gasto_res.is_err():
                    return
                gasto = gasto_res.unwrap()

                content = (
                    f"El gasto '{gasto.descripcion}' por un monto de "
                    f"{gasto.monto} {gasto.currency} realizado el {gasto.fecha} "
                    f"en la categoría '{gasto.categoria.value}' fue compartido en "
                    f"el hogar {household_id}."
                )

                emb_res = await self.embedding_service.generar_embedding(content)
                if emb_res.is_err():
                    return
                embedding = emb_res.unwrap()

                memoria_repo = MemoriaRepository(uow.session, familia_id=familia_id)
                memoria_repo.guardar_con_household(
                    content=content,
                    embedding=embedding,
                    household_id=household_id,
                    source_type="shared_expense",
                    source_id=gasto_id,
                )
                uow.session.commit()
                logger.info(
                    "[HouseholdMemoryHandler] Vector guardado para gasto compartido %s",
                    gasto_id,
                )
        except Exception as e:
            logger.error(
                "[HouseholdMemoryHandler] Error al procesar "
                "SHARED_EXPENSE_LINK_CREADO: %s",
                e,
            )

    async def handle_shared_expense_link_eliminado(self, event: Event) -> None:
        try:
            household_id = event.data["household_id"]
            gasto_id = event.data["gasto_id"]
            familia_id = event.data["familia_id"]

            with UnitOfWork() as uow:
                memoria_repo = MemoriaRepository(uow.session, familia_id=familia_id)
                memoria_repo.eliminar_household_vector(
                    household_id=household_id,
                    source_type="shared_expense",
                    source_id=gasto_id,
                )
                uow.session.commit()
                logger.info(
                    "[HouseholdMemoryHandler] Vector eliminado para gasto "
                    "compartido %s",
                    gasto_id,
                )
        except Exception as e:
            logger.error(
                "[HouseholdMemoryHandler] Error al procesar "
                "SHARED_EXPENSE_LINK_ELIMINADO: %s",
                e,
            )

    async def handle_settlement_creado(self, event: Event) -> None:
        try:
            household_id = event.data["household_id"]
            payer_id = event.data["payer_familia_id"]
            recipient_id = event.data["recipient_familia_id"]
            monto = event.data["monto"]

            content = (
                f"Se registró un pago/liquidación (settlement) en el hogar "
                f"{household_id}. La familia {payer_id} le pagó {monto} a la "
                f"familia {recipient_id}."
            )

            emb_res = await self.embedding_service.generar_embedding(content)
            if emb_res.is_err():
                return
            embedding = emb_res.unwrap()

            with UnitOfWork() as uow:
                memoria_repo = MemoriaRepository(uow.session, familia_id=payer_id)
                memoria_repo.guardar_con_household(
                    content=content,
                    embedding=embedding,
                    household_id=household_id,
                    source_type="settlement",
                    source_id=0,  # or settlement_id if we pass it
                )
                uow.session.commit()
                logger.info(
                    "[HouseholdMemoryHandler] Vector guardado para settlement %s",
                    household_id,
                )
        except Exception as e:
            logger.error(
                "[HouseholdMemoryHandler] Error al procesar SETTLEMENT_CREADO: %s",
                e,
            )
