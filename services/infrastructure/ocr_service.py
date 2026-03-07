"""
Servicio de OCR local con Tesseract.
Extrae texto de imágenes de tickets. No interpreta — solo extrae texto crudo.
La interpretación la hace TicketService con Gemma.
"""
from __future__ import annotations

import logging
from pathlib import Path

from result import Err, Ok, Result

from models.errors import AppError
from models.ticket_model import PartialExpense

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    _TESSERACT_DISPONIBLE = True
except ImportError:
    pytesseract = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment]
    ImageEnhance = None  # type: ignore[assignment]
    ImageFilter = None  # type: ignore[assignment]
    _TESSERACT_DISPONIBLE = False


class OCRService:
    """Extrae texto de imágenes de tickets usando Tesseract (local, sin GPU)."""

    _MIN_CHARS = 20  # Mínimo de chars para considerar OCR exitoso

    def _preprocesar_imagen(self, imagen):
        """
        Mejora la imagen antes de pasarla a Tesseract:
        escala de grises → contraste → nitidez.
        Mejora la tasa de acierto en tickets de papel térmico.

        🇺🇾 Tip Uruguay: los tickets locales suelen tener el RUT del comercio
        al principio o al final. Gemma los ignora bien con el prompt actual.
        Si en el futuro Gemma se confunde con el RUT (ej. lo interpreta como
        monto), se puede recortar márgenes antes de pasar a Tesseract:
            ancho, alto = imagen.size
            imagen = imagen.crop((0, 50, ancho, alto - 50))
        Por ahora NO se recorta — contraste + nitidez es suficiente.
        """
        imagen = imagen.convert("L")                          # Escala de grises
        imagen = ImageEnhance.Contrast(imagen).enhance(2.0)   # Más contraste
        imagen = imagen.filter(ImageFilter.SHARPEN)            # Nitidez
        return imagen

    async def extraer_texto(
        self, imagen_path: str
    ) -> Result[PartialExpense, AppError]:
        """
        Lee una imagen y extrae el texto con Tesseract (lang=spa).
        Retorna un PartialExpense con texto_crudo y confianza_ocr.
        """
        try:
            if not _TESSERACT_DISPONIBLE:
                return Err(AppError(
                    "pytesseract no está instalado. "
                    "Ejecutá: uv add pytesseract pillow"
                ))

            path = Path(imagen_path)
            if not path.exists():
                return Err(AppError(f"Imagen no encontrada: {imagen_path}"))

            imagen = Image.open(path)
            imagen = self._preprocesar_imagen(imagen)

            datos = pytesseract.image_to_data(
                imagen,
                lang="spa",
                output_type=pytesseract.Output.DICT,
            )

            texto_crudo = " ".join(
                w for w in datos["text"] if w.strip()
            )

            # Confianza promedio de palabras con conf > 0
            confs = [c for c in datos["conf"] if c > 0]
            confianza = (
                round(sum(confs) / len(confs) / 100, 2) if confs else 0.0
            )

            if len(texto_crudo) < self._MIN_CHARS:
                logger.warning(
                    "[OCR] Texto muy corto (%d chars) — imagen ilegible",
                    len(texto_crudo),
                )
                confianza = 0.0

            logger.info(
                "[OCR] Extraídos %d chars (confianza=%.2f)",
                len(texto_crudo),
                confianza,
            )

            return Ok(PartialExpense(
                texto_crudo=texto_crudo,
                confianza_ocr=confianza,
                imagen_path=imagen_path,
            ))

        except ImportError:
            return Err(AppError(
                "pytesseract no está instalado. "
                "Ejecutá: uv add pytesseract pillow"
            ))
        except Exception as e:
            logger.error("[OCR] Error procesando imagen: %s", e)
            return Err(AppError(f"Error OCR: {e}"))
