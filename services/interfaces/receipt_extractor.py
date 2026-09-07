"""Hexagonal Port and DTOs for receipt and invoice extraction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class ReceiptItemExtraction:
    """Item line extracted from a receipt."""

    description: str
    quantity: Decimal = Decimal("1")
    unit_price: Decimal | None = None
    amount: Decimal | None = None


@dataclass(frozen=True)
class ReceiptExtraction:
    """Document intelligence extraction result DTO."""

    merchant: str | None
    rut: str | None
    issue_date: date | None
    currency: str  # "UYU" | "USD"
    items: tuple[ReceiptItemExtraction, ...]
    subtotal: Decimal | None
    tax: Decimal | None
    total: Decimal | None
    payment_method: str | None
    payment_amount: Decimal | None
    extraction_confidence: Decimal  # Decimal representation 0.00 to 1.00
    total_confidence: Decimal = Decimal("0.0")
    merchant_confidence: Decimal = Decimal("0.0")
    date_confidence: Decimal = Decimal("0.0")
    raw_text: str = ""
    engine_used: str = "local"
    arithmetic_consistent: bool | None = None


class ReceiptExtractor(Protocol):
    """Port interface for receipt extraction engines (Local Tesseract, Gemini, etc.)."""

    async def extract(self, image_bytes: bytes, **kwargs) -> ReceiptExtraction:
        """Extract structured receipt data from raw image bytes asynchronously."""
        ...
