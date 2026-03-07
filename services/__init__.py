"""Services package — re-exports para compatibilidad con imports existentes."""

from services.ai.ai_advisor_service import AIAdvisorService
from services.ai.embedding_service import EmbeddingService
from services.ai.ia_memory_service import IAMemoryService
from services.ai.memory_event_handler import MemoryEventHandler
from services.domain.auth_service import AuthService
from services.domain.expense_service import ExpenseService
from services.domain.family_member_service import FamilyMemberService
from services.domain.income_service import IncomeService
from services.domain.registration_service import RegistrationService
from services.domain.shopping_service import ShoppingService
from services.domain.validators import validate_monto_positivo
from services.infrastructure.ocr_service import OCRService
from services.infrastructure.report_service import ReportService
from services.infrastructure.ticket_service import TicketService

__all__ = [
    "AIAdvisorService",
    "EmbeddingService",
    "IAMemoryService",
    "MemoryEventHandler",
    "AuthService",
    "ExpenseService",
    "FamilyMemberService",
    "IncomeService",
    "RegistrationService",
    "ShoppingService",
    "validate_monto_positivo",
    "OCRService",
    "ReportService",
    "TicketService",
]
