"""
NVIDIAClient — Cliente async para NVIDIA API (Llama 3 70B).

Usa httpx AsyncClient con timeout de 60s.
Retorna dict con 'response' y 'usage' compatible con el formato de Ollama.

Raises:
    ConnectionError: Si la API key no está configurada o hay error de conexión.
    TimeoutError: Si la API no responde en el tiempo límite.
    RuntimeError: Si hay un error HTTP inesperado.
"""
from __future__ import annotations

import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)

# Configuración desde environment
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama3-70b-instruct")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")


class NVIDIAClient:
    """Cliente async para NVIDIA API (Llama 3 70B)."""

    def __init__(self) -> None:
        self._base_url = NVIDIA_BASE_URL
        self._model = NVIDIA_MODEL
        self._api_key = NVIDIA_API_KEY

        if not self._api_key:
            logger.warning(
                "[NVIDIA] NVIDIA_API_KEY no configurada. "
                "Las consultas avanzadas no estarán disponibles."
            )

    @property
    def is_configured(self) -> bool:
        """Retorna True si la API key está configurada."""
        return bool(self._api_key)

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> dict:
        """
        Llama a NVIDIA API con el prompt construido.

        Args:
            prompt: El prompt completo del Contador Oriental.
            temperature: Temperatura de muestreo (default 0.1).
            max_tokens: Máximo de tokens de respuesta.

        Returns:
            dict con keys:
                'response': str — texto de respuesta del modelo
                'prompt_tokens': int
                'completion_tokens': int

        Raises:
            ConnectionError: Si la API key no está configurada o hay error de conexión.
            TimeoutError: Si la API no responde en el tiempo límite.
            RuntimeError: Si hay un error HTTP inesperado.
        """
        if not self.is_configured:
            raise ConnectionError(
                "NVIDIA API key no configurada. "
                "Configure NVIDIA_API_KEY en el archivo .env"
            )

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        logger.info(
            "[NVIDIA] Llamando a %s (modelo=%s, %d chars)",
            self._base_url,
            self._model,
            len(prompt),
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                data = response.json()

                # Extraer respuesta y uso de tokens
                content = data["choices"][0]["message"]["content"].strip()
                usage = data.get("usage", {})

                result = {
                    "response": content,
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                }

                logger.info(
                    "[NVIDIA] Respuesta: %d chars, %d+%d tokens",
                    len(content),
                    result["prompt_tokens"],
                    result["completion_tokens"],
                )

                return result

            except httpx.TimeoutException:
                logger.error("[NVIDIA] Timeout (60s) llamando a la API")
                raise TimeoutError(
                    "Timeout al consultar NVIDIA API. "
                    "El servidor no respondió en 60 segundos."
                )
            except httpx.HTTPStatusError as e:
                logger.error(
                    "[NVIDIA] Error HTTP %d: %s", e.response.status_code, str(e)
                )
                raise RuntimeError(
                    f"Error HTTP {e.response.status_code} al consultar NVIDIA API."
                )
            except httpx.ConnectError:
                logger.error("[NVIDIA] Error de conexión a NVIDIA API")
                raise ConnectionError(
                    "No se pudo conectar a NVIDIA API. "
                    "Verifique la conexión a internet."
                )

    async def generate_stream(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ):
        """
        Versión streaming de generate().
        Yield tokens a medida que Llama 3 los genera.

        Yields:
            str — fragmento de texto generado por el modelo.

        Raises:
            ConnectionError: Si la API key no está configurada o hay error de conexión.
            TimeoutError: Si la API no responde en el tiempo límite.
            RuntimeError: Si hay un error HTTP inesperado.
        """
        if not self.is_configured:
            raise ConnectionError(
                "NVIDIA API key no configurada. "
                "Configure NVIDIA_API_KEY en el archivo .env"
            )

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        logger.info(
            "[NVIDIA] Stream iniciado (modelo=%s, %d chars)",
            self._model,
            len(prompt),
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                async with client.stream(
                    "POST", url, json=payload, headers=headers
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk.get("choices", [{}])[0].get(
                                    "delta", {}
                                )
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue

                logger.info("[NVIDIA] Stream completado")

            except httpx.TimeoutException:
                raise TimeoutError("Timeout al consultar NVIDIA API (stream).")
            except httpx.HTTPStatusError as e:
                raise RuntimeError(
                    f"Error HTTP {e.response.status_code} al consultar NVIDIA API."
                )
            except httpx.ConnectError:
                raise ConnectionError("No se pudo conectar a NVIDIA API.")