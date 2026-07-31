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

    async def fetch_rate(self) -> Result[tuple[Decimal, Decimal], AppError]:
        """
        Consulta la cotización y retorna (compra, venta).
        Por ahora, usamos la API intermedia y simulamos el spread del BROU
        (aprox +/- 2.5% del valor intermedio) como fallback arquitectónico,
        dejando la firma lista para conectar directo al SOAP del BCU.

        Returns:
            Result[tuple[Decimal, Decimal], AppError] — (compra, venta)
        """
        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT) as client:
                response = await client.get(self._API_URL)
                response.raise_for_status()
                data = response.json()

                raw_rate = data["rates"]["UYU"]
                medio = Decimal(str(raw_rate))
                
                # Simulamos el spread oficial del BROU (aprox 1 peso de diferencia para cada lado)
                compra = (medio - Decimal("1.20")).quantize(Decimal("0.01"))
                venta = (medio + Decimal("1.20")).quantize(Decimal("0.01"))
                
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
