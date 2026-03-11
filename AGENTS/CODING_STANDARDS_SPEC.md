# CODING_STANDARDS_SPEC.md - Contador Oriental

## General Principles

- **Python 3.12+** with strict type hints
- Use `from __future__ import annotations` for postponed evaluation
- **Line length**: 88 characters (ruff default)
- **Indentation**: 4 spaces
- **Quotes**: Double quotes (`"`)
- **No comments** unless explicitly requested

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `ExpenseController`, `AppError` |
| Functions/Variables | snake_case | `add_expense`, `familia_id` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| Files | snake_case.py | `expense_controller.py` |

## Import Order (ruff)

1. Standard library (`from __future__ import annotations` first)
2. Third-party packages
3. Local application imports

```python
from __future__ import annotations

import logging
from datetime import date
from collections.abc import Generator

from result import Ok, Err

from controllers.base_controller import BaseController
from models.expense_model import Expense
from services.expense_service import ExpenseService
```

## Type Hints

- Use **strict type hints** everywhere
- Use union syntax (`X | None`) instead of `Optional[X]`
- Use `list[X]`, `dict[K, V]` instead of `List`, `Dict`
- Add return types to all functions: `def foo() -> str:`

```python
def add_expense(self, expense: Expense) -> Result[Expense, AppError]:
    ...

def list_expenses(self) -> list[Expense]:
    ...

def get_summary_by_categories(
    self,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, float]:
    ...
```

## Error Handling

- **Use `Result[T, E]`** from the `result` library (not exceptions)
- Never raise exceptions in services/repositories
- Return `Result[SuccessType, AppError]` or `Result[None, AppError]`

```python
from result import Ok, Err
from models.errors import AppError, DatabaseError, ValidationError

def create_expense(
    self, expense: Expense
) -> Result[Expense, ValidationError | DatabaseError]:
    for check in (validate_monto_positive(expense.monto), ...):
        if check.is_err():
            return check
    return self._repo.add(expense)
```

### Custom Errors

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class AppError:
    message: str

@dataclass(frozen=True)
class DatabaseError(AppError):
    pass

@dataclass(frozen=True)
class ValidationError(AppError):
    pass
```

## Database Layer

- Use **SQLAlchemy** with `BaseTableRepository(ABC, Generic)`
- Controllers use context manager pattern for sessions:

```python
class ExpenseController(BaseController):
    def add_expense(self, expense: Expense) -> Result[Expense, AppError]:
        with self._get_session() as session:
            repo = ExpenseRepository(session, self._familia_id)
            service = ExpenseService(repo)
            return service.create_expense(expense)
```

- Repositories must filter by `familia_id` for multi-tenancy

## Pydantic Models

- Use Pydantic for all input/output validation
- Use `frozen=True` for immutable models
- Use enums for categories

```python
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

class ExpenseCategory(Enum):
    ALMACEN = "Almacén"
    HOGAR = "Hogar"

class Expense(BaseModel):
    monto: float = Field(gt=0)
    descripcion: str = Field(min_length=1)
    fecha: date
    categoria: ExpenseCategory
    es_recurrente: bool = False
```

## Flet UI Guidelines

### Controls
- Use `ft.Button` instead of deprecated `ft.ElevatedButton`
- Use `ft.Button` with style instead of deprecated `ft.OutlinedButton`
- **Card**: Use `bgcolor` on inner Container, not `color` on Card
- Images: Use `src=str` for file paths, `src=bytes` for binary data

### Navigation
- `page.launch_url()` doesn't work in web mode
- Use `ft.Url` with `target=ft.UrlTarget.BLANK` for external links
- For text links: `ft.Text(spans=[ft.TextSpan(text, url=url, ...)])`

### Web Mode Limitations
- **FilePicker does not work**: Use OCR microservice pattern instead
- Generate QR codes as file paths, serve via web server

## Testing Guidelines

- Tests use **real PostgreSQL** with transaction rollback for isolation
- Use fixtures from `tests/conftest.py`
- Mock external services (Ollama) for unit tests

```python
class TestExpenseService:
    @pytest.fixture
    def service(self, db_session):
        from repositories.expense_repository import ExpenseRepository
        repo = ExpenseRepository(db_session, familia_id=1)
        return ExpenseService(repo)

    def test_create_expense_success(self, service, sample_expense_data):
        expense = Expense(**sample_expense_data)
        result = service.create_expense(expense)
        assert isinstance(result, Ok)
```

## Linting Commands

```bash
# Check lint
uv run ruff check .

# Format code
uv run ruff format .

# Type check
uv run ty check .

# Run diagnostic tool
uv run python check_flet.py --compat
```

## FilePicker Limitation

In Flet web mode (Docker), `ft.FilePicker` fails due to JS handshake issues. Always use the OCR microservice pattern:
1. Generate session_id (UUID)
2. Show QR code or URL for external form
3. Poll for result via session_id
