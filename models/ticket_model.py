"""
Modelo temporal de dominio para un ticket OCR antes de ser confirmado
como Expense definitivo. No persiste en BD directamente — es un DTO
que viaja desde OCRService hasta la vista de confirmación.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class PartialExpense:
    """
    Resultado del parseo de un ticket fotográfico.
    Todos los campos son opcionales porque el OCR puede no encontrar todos
    (ticket roto, mala foto, papel térmico decolorado, etc.)
    El usuario completa o corrige lo que falte en la vista de confirmación.
    """
    monto: float | None = None
    fecha: date | None = None
    comercio: str | None = None
    items: list[str] = field(default_factory=list)
    # Viene del cosine search en expenses.embedding
    categoria_sugerida: str | None = None
    confianza_ocr: float = 0.0      # 0.0 = ilegible, 1.0 = perfecto
    texto_crudo: str = ""           # Texto Tesseract sin procesar (auditoría)
    imagen_path: str = ""           # Ruta temporal de la imagen

    @property
    def es_confiable(self) -> bool:
        """True si la confianza OCR es suficiente para pre-llenar el formulario."""
        return self.confianza_ocr >= 0.5

    @property
    def tiene_datos_minimos(self) -> bool:
        """True si el OCR extrajo al menos monto o comercio."""
        return self.monto is not None or self.comercio is not None
