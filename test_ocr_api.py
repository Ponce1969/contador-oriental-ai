"""Script de prueba para el microservicio OCR."""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx


async def test_health() -> None:
    """Prueba el endpoint de health."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8551/health")
        print(f"Health check: {response.status_code}")
        print(f"Response: {response.json()}")


async def test_upload_ocr(imagen_path: str) -> None:
    """Prueba el endpoint de OCR."""
    if not Path(imagen_path).exists():
        print(f"❌ Imagen no encontrada: {imagen_path}")
        return

    async with httpx.AsyncClient(timeout=60.0) as client:
        with open(imagen_path, "rb") as f:
            files = {"file": ("ticket.jpg", f, "image/jpeg")}
            data = {"familia_id": "1"}
            response = await client.post(
                "http://localhost:8551/upload-ocr",
                files=files,
                data=data,
            )

        print(f"\nOCR Upload: {response.status_code}")
        print(f"Response: {response.json()}")


async def main() -> None:
    """Ejecuta las pruebas."""
    print("=== Probando OCR API ===\n")

    # 1. Health check
    await test_health()

    # 2. OCR (necesitas una imagen de prueba)
    # Descomenta y ajusta la ruta si tienes una imagen:
    # await test_upload_ocr("ruta/a/tu/ticket.jpg")


if __name__ == "__main__":
    asyncio.run(main())
