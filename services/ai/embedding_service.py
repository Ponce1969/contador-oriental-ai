"""
EmbeddingService — Genera vectores de texto usando nomic-embed-text via Ollama.
Diseñado para Orange Pi 5 Plus: async, liviano, resiliente a fallos.
"""
from __future__ import annotations

import logging
import os

import httpx
from result import Err, Ok, Result

from models.errors import AppError

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
EMBEDDING_TIMEOUT = 30.0


class EmbeddingService:
    """
    Genera embeddings de 768 dimensiones usando nomic-embed-text vía Ollama.
    100% offline, optimizado para hardware ARM.
    """

    def __init__(
        self,
        ollama_url: str = OLLAMA_URL,
        model: str = EMBEDDING_MODEL,
    ) -> None:
        self.ollama_url = ollama_url
        self.model = model

    async def generar_embedding(self, texto: str) -> Result[list[float], AppError]:
        """
        Convierte texto en un vector de 768 dimensiones.

        Args:
            texto: Texto a vectorizar (limpiar antes de llamar).

        Returns:
            Ok([float, ...]) con 768 dimensiones, o Err si Ollama falla.
        """
        if not texto or not texto.strip():
            return Err(AppError(message="Texto vacío: no se puede generar embedding."))

        texto_limpio = texto.strip()[:8000]

        try:
            async with httpx.AsyncClient(timeout=EMBEDDING_TIMEOUT) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/embeddings",
                    json={"model": self.model, "prompt": texto_limpio},
                )
                if response.status_code == 200:
                    embedding = response.json().get("embedding", [])
                    if not embedding:
                        return Err(
                            AppError(message="Ollama devolvió embedding vacío.")
                        )
                    logger.debug(
                        "Embedding generado: %d dims para '%s...'",
                        len(embedding),
                        texto_limpio[:40],
                    )
                    return Ok(embedding)

                return Err(
                    AppError(
                        message=(
                            f"Ollama error {response.status_code}: "
                            f"{response.text[:200]}"
                        )
                    )
                )
        except httpx.ConnectError:
            logger.warning(
                "[EMBEDDING_FAILED] Ollama no disponible en %s", self.ollama_url
            )
            return Err(
                AppError(
                    message=(
                        f"No se puede conectar con Ollama en {self.ollama_url}. "
                        "Verificar que el servicio esté activo."
                    )
                )
            )
        except Exception as e:
            logger.error("[EMBEDDING_FAILED] Error inesperado: %s", str(e))
            return Err(AppError(message=f"Error generando embedding: {str(e)}"))
