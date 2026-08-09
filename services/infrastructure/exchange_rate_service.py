"""
Servicio de cotización de divisas USD/UYU
Usa exchangerate-api.com (sin API key, httpx nativo) para el tipo de cambio
interbancario (mid). Aplica un spread porcentual realista (±2.5%) para obtener
los tipos de compra y venta al público, modelando el spread del BROU.

0 floats: todo Decimal desde la respuesta JSON hasta la UI.
"""

from __future__ import annotations

import json
from decimal import ROUND_HALF_UP, Decimal

import httpx
from result import Err, Ok, Result

from models.errors import AppError

# Spread porcentual: los bancos uruguayos operan típicamente con un margen
# de ~2-3% sobre el interbancario para cada punta (compra/venta).
_SPREAD_PCT = Decimal("0.025")  # 2.5%


class ExchangeRateService:
    """Consulta la cotización USD/UYU desde exchangerate-api.com
    
    Aplica un spread porcentual (2.5% cada lado) sobre el mid interbancario
    para obtener compra y venta realistas. La firma (compra, venta) está lista
    para ser reemplazada por scraping directo del BROU cuando esté disponible.
    """

    _API_URL = "https://api.exchangerate-api.com/v4/latest/USD"
    _TIMEOUT = 10.0

    async def fetch_rate(self) -> Result[tuple[Decimal, Decimal], AppError]:
        """
        Consulta la API y retorna (compra, venta) en pesos uruguayos.

        Returns:
            Result[tuple[Decimal, Decimal], AppError] — (compra, venta)
        """
        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
                response = await client.get(self._API_URL)
                response.raise_for_status()
                data = response.json()

                raw_rate = data["rates"]["UYU"]
                mid = Decimal(str(raw_rate))

                # Spread porcentual realista (~2.5% cada lado, total ~5%)
                spread = (mid * _SPREAD_PCT).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                compra = (mid - spread).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                venta = (mid + spread).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                return Ok((compra, venta))

        except KeyError as e:
            return Err(AppError(message=f"Respuesta inválida de API: falta campo {e}"))
        except json.JSONDecodeError as e:
            return Err(AppError(message=f"Respuesta inválida de API (no es JSON): {e}"))
        except httpx.HTTPStatusError as e:
            return Err(
                AppError(message=f"API exchangerate error {e.response.status_code}")
            )
        except Exception as e:
            return Err(AppError(message=f"Error consultando cotización del dólar: {e}"))
