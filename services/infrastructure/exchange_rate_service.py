"""
Servicio de cotización de divisas USD/UYU
Usa exchangerate-api.com (sin API key, httpx nativo).
0 floats: todo Decimal desde la respuesta JSON hasta la UI.
"""
from __future__ import annotations

import json
from decimal import Decimal

import httpx
from result import Err, Ok, Result

from models.errors import AppError


class ExchangeRateService:
    """Consulta la cotización USD/UYU desde exchangerate-api.com"""

    _API_URL = "https://api.exchangerate-api.com/v4/latest/USD"
    _TIMEOUT = 10.0

    async def fetch_rate(self) -> Result[Decimal, AppError]:
        """
        Consulta la API y retorna el rate UYU como Decimal.

        Returns:
            Result[Decimal, AppError] — rate UYU o error descriptivo.
        """
        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
                response = await client.get(self._API_URL)
                response.raise_for_status()
                data = response.json()

                raw_rate = data["rates"]["UYU"]
                rate = Decimal(str(raw_rate))
                return Ok(rate)

        except KeyError as e:
            return Err(
                AppError(message=f"Respuesta inválida de API: falta campo {e}")
            )
        except json.JSONDecodeError as e:
            return Err(
                AppError(message=f"Respuesta inválida de API (no es JSON): {e}")
            )
        except httpx.HTTPStatusError as e:
            return Err(
                AppError(
                    message=f"API exchangerate error {e.response.status_code}"
                )
            )
        except Exception as e:
            return Err(
                AppError(message=f"Error consultando cotización del dólar: {e}")
            )
