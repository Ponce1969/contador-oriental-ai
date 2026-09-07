"""Adapter implementing ReceiptExtractor Protocol for Contador Oriental."""

from __future__ import annotations

import logging
import os
from datetime import date
from decimal import Decimal
from typing import Any

import httpx

from services.interfaces.receipt_extractor import (
    ReceiptExtraction,
    ReceiptExtractor,
    ReceiptItemExtraction,
)

logger = logging.getLogger(__name__)


class MicroserviceReceiptExtractor(ReceiptExtractor):
    """Adapter communicating with FastAPI OCR microservice."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or os.getenv("OCR_API_URL", "http://ocr_api:8551")

    async def extract(self, image_bytes: bytes, **kwargs: Any) -> ReceiptExtraction:
        """Upload image to OCR microservice and return strict ReceiptExtraction DTO."""
        engine = kwargs.get("engine", "auto")
        familia_id = kwargs.get("familia_id", 1)

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                files = {"file": ("receipt.jpg", image_bytes, "image/jpeg")}
                data = {"familia_id": str(familia_id), "engine": engine}
                resp = await client.post(
                    f"{self.base_url}/upload-ocr", files=files, data=data
                )
                resp.raise_for_status()
                payload = resp.json()
        except Exception as err:
            logger.warning("[EXTRACTOR] Error calling OCR API: %s", err)
            payload = {
                "success": False,
                "error": str(err),
                "extraction_confidence": 0.0,
                "texto_crudo": "",
                "engine_used": engine,
            }

        def _to_str(val: Any) -> str | None:
            return str(val) if val is not None else None

        def _to_bool(val: Any) -> bool | None:
            if val is None:
                return None
            return bool(val)

        def _to_decimal(val: Any) -> Decimal | None:
            if val is None:
                return None
            try:
                return Decimal(str(val))
            except Exception:
                return None

        issue_date: date | None = None
        if payload.get("fecha"):
            try:
                issue_date = date.fromisoformat(str(payload["fecha"]))
            except Exception:
                pass

        raw_items = payload.get("items")
        items: list[ReceiptItemExtraction] = []
        if isinstance(raw_items, (list, tuple)):
            for it in raw_items:
                if isinstance(it, str):
                    items.append(ReceiptItemExtraction(description=it))
                elif isinstance(it, dict):
                    desc = str(it.get("description") or it.get("nombre") or "")
                    items.append(
                        ReceiptItemExtraction(
                            description=desc,
                            quantity=_to_decimal(it.get("quantity")) or Decimal("1"),
                            unit_price=_to_decimal(it.get("unit_price")),
                            amount=_to_decimal(it.get("amount")),
                        )
                    )

        try:
            raw_conf = (
                payload.get("extraction_confidence")
                or payload.get("confianza_ocr")
                or 0.0
            )
            conf_float = float(raw_conf)
        except (ValueError, TypeError):
            conf_float = 0.0
        conf_decimal = Decimal(str(round(conf_float, 2)))

        return ReceiptExtraction(
            merchant=_to_str(payload.get("comercio")),
            rut=_to_str(payload.get("rut")),
            issue_date=issue_date,
            currency=str(payload.get("currency") or "UYU"),
            items=tuple(items),
            subtotal=_to_decimal(payload.get("subtotal")),
            tax=_to_decimal(payload.get("tax")),
            total=_to_decimal(payload.get("monto")),
            payment_method=_to_str(payload.get("metodo_pago")),
            payment_amount=_to_decimal(payload.get("payment_amount")),
            extraction_confidence=conf_decimal,
            total_confidence=Decimal(str(payload.get("total_confidence", 0.0))),
            merchant_confidence=Decimal(str(payload.get("merchant_confidence", 0.0))),
            date_confidence=Decimal(str(payload.get("date_confidence", 0.0))),
            raw_text=str(payload.get("texto_crudo") or ""),
            engine_used=str(payload.get("engine_used") or "local"),
            arithmetic_consistent=_to_bool(payload.get("arithmetic_consistent")),
        )
