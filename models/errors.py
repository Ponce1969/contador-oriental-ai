from __future__ import annotations

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
