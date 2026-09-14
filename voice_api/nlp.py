"""NLP and structured extraction for Uruguayan voice expenses."""

from __future__ import annotations

import json
import logging
import re
from decimal import Decimal, InvalidOperation

import httpx
from voice_api.config import settings

logger = logging.getLogger("uvicorn.error")

_SYSTEM_PROMPT = """Sos un asistente financiero uruguayo de 'Contador Oriental'.
Tu tarea es extraer los datos de un gasto dictado por voz por un usuario uruguayo.

Respondé ÚNICAMENTE un JSON válido con esta estructura exacta (sin markdown):
{{
  "monto": null,
  "currency": "UYU",
  "comercio": null,
  "categoria": null,
  "subcategoria": null,
  "medio_pago": null,
  "notas": null
}}

Reglas estrictas con contexto de Uruguay:
1. "monto": Número decimal puro o null.
   - "quinientos pesos" -> 500.0
   - "dos lucas" o "dos palos" -> 2000.0
   - "media luca" o "quinientos" -> 500.0
   - "una gamba" -> 100.0
   - "tres mil doscientos" -> 3200.0
2. "currency": "UYU" por defecto (pesos, $), o "USD" (dólares, u$s, verdes).
3. "comercio": Nombre del local (ej: "Disco", "Devoto", "Ta-Ta",
   "Tienda Inglesa", "Farmashop", "Ancap", "UTE", "OSE", "Antel") o null.
4. "categoria": Debe ser EXACTAMENTE una de estas opciones con su emoji:
   - "🛒 Almacén" (supermercado, comida, verdulería, carnicería, panadería)
   - "🚗 Vehículos" (nafta, combustible, taller, ómnibus, boleto, peaje)
   - "🏠 Hogar" (alquiler, UTE, OSE, Antel, gastos comunes, reparaciones)
   - "👨‍⚕️ Salud" (farmacia, médico, mutualista, dentista, remedios)
   - "📚 Educación" (colegio, libros, útiles, cuota)
   - "🎉 Ocio" (restaurante, bar, cine, delivery, salidas, pedidos ya)
   - "👕 Ropa" (indumentaria, calzado, shopping)
   - "📦 Otros"
5. "subcategoria": Nombre de subcategoría si se deduce claramente o null.
6. "medio_pago": Tarjeta o medio de pago (ej: "Efectivo", "Débito", "Crédito",
   "Prex", "OCA", "Itaú", "BROU", "Santander", "Visa", "Mastercard") o null.
7. "notas": Texto del audio o descripción corta del concepto comprado.

Texto del audio:
"{texto}"
"""

# Mapeo determinístico de comercios uruguayos comunes y sus categorías
_MERCHANT_MAP: dict[str, tuple[str, str]] = {
    "disco": ("🛒 Almacén", "Supermercado"),
    "devoto": ("🛒 Almacén", "Supermercado"),
    "ta-ta": ("🛒 Almacén", "Supermercado"),
    "tata": ("🛒 Almacén", "Supermercado"),
    "tienda inglesa": ("🛒 Almacén", "Supermercado"),
    "el dorado": ("🛒 Almacén", "Supermercado"),
    "macro mercado": ("🛒 Almacén", "Supermercado"),
    "macromercado": ("🛒 Almacén", "Supermercado"),
    "farmashop": ("👨‍⚕️ Salud", "Farmacia"),
    "san roque": ("👨‍⚕️ Salud", "Farmacia"),
    "ancap": ("🚗 Vehículos", "Combustible"),
    "axion": ("🚗 Vehículos", "Combustible"),
    "disa": ("🚗 Vehículos", "Combustible"),
    "ute": ("🏠 Hogar", "UTE (Luz)"),
    "ose": ("🏠 Hogar", "OSE (Agua)"),
    "antel": ("🏠 Hogar", "Antel (Internet/Tel)"),
    "pedidos ya": ("🎉 Ocio", "Delivery comida"),
    "pedidosya": ("🎉 Ocio", "Delivery comida"),
}

_WORDS_TO_NUM: dict[str, Decimal] = {
    "cero": Decimal("0"),
    "un": Decimal("1"),
    "uno": Decimal("1"),
    "dos": Decimal("2"),
    "tres": Decimal("3"),
    "cuatro": Decimal("4"),
    "cinco": Decimal("5"),
    "seis": Decimal("6"),
    "siete": Decimal("7"),
    "ocho": Decimal("8"),
    "nueve": Decimal("9"),
    "diez": Decimal("10"),
    "cien": Decimal("100"),
    "ciento": Decimal("100"),
    "doscientos": Decimal("200"),
    "trescientos": Decimal("300"),
    "cuatrocientos": Decimal("400"),
    "quinientos": Decimal("500"),
    "seiscientos": Decimal("600"),
    "setecientos": Decimal("700"),
    "ochocientos": Decimal("800"),
    "novecientos": Decimal("900"),
    "mil": Decimal("1000"),
}


def _parse_colloquial_amount(texto: str) -> Decimal | None:
    """Extrae montos numéricos o jerga uruguaya ('dos lucas', 'tres palos')."""
    t = texto.lower()

    # Jerga uruguaya común: lucas / palos (= 1000)
    m_lucas = re.search(r"(\d+(?:[.,]\d+)?|\w+)\s*(?:lucas|palos)", t)
    if m_lucas:
        val_str = m_lucas.group(1)
        if val_str in _WORDS_TO_NUM:
            return _WORDS_TO_NUM[val_str] * Decimal("1000")
        try:
            return Decimal(val_str.replace(",", ".")) * Decimal("1000")
        except (InvalidOperation, ValueError):
            pass

    # Jerga: gamba (= 100)
    m_gamba = re.search(r"(\d+|\w+)?\s*(?:gambas|gamba)", t)
    if m_gamba:
        val_str = m_gamba.group(1)
        mult = _WORDS_TO_NUM.get(val_str, Decimal("1")) if val_str else Decimal("1")
        return mult * Decimal("100")

    # Números explícitos: ej "450 pesos", "$ 1200", "790.50"
    num_pattern = (
        r"(?:\$|uyu|pesos)?\s*([0-9]+(?:[.,][0-9]{1,2})?)\s*"
        r"(?:pesos|dolares|dólares|usd|\$)?"
    )
    m_num = re.search(num_pattern, t)
    if m_num:
        try:
            raw = m_num.group(1).replace(",", ".")
            val = Decimal(raw)
            if Decimal("0") < val < Decimal("10000000"):
                return val
        except (InvalidOperation, ValueError):
            pass

    return None


def extract_expense_regex_fallback(texto: str) -> dict:
    """Extractor heurístico y determinístico de respaldo para gastos uruguayos."""
    if not texto:
        return {}

    t = texto.lower()

    # 1. Moneda
    currency = "UYU"
    if re.search(r"\b(usd|dolar|dólar|dolares|dólares|verdes|u\$s)\b", t):
        currency = "USD"

    # 2. Monto
    monto = _parse_colloquial_amount(texto)

    # 3. Comercio y categoría según catálogo
    comercio = None
    categoria = "📦 Otros"
    subcategoria = None

    for m_key, (cat, subcat) in _MERCHANT_MAP.items():
        if re.search(rf"\b{re.escape(m_key)}\b", t):
            comercio = m_key.title()
            categoria = cat
            subcategoria = subcat
            break

    # Si no hubo comercio pero hay palabras clave de categoría
    if not comercio:
        if re.search(r"\b(carne|verdura|pan|leche|comida|super|almacen|almacén)\b", t):
            categoria = "🛒 Almacén"
        elif re.search(
            r"\b(nafta|combustible|gasoil|taller|mecanico|mecánico|peaje)\b", t
        ):
            categoria = "🚗 Vehículos"
        elif re.search(r"\b(farmacia|remedio|medicamento|medico|médico|dentista)\b", t):
            categoria = "👨‍⚕️ Salud"

    # 4. Medio de pago uruguayo
    medio_pago = None
    pm_patterns = [
        r"\b(efectivo|contado)\b",
        r"\b(debito|débito)\b",
        r"\b(credito|crédito)\b",
        r"\b(oca)\b",
        r"\b(prex)\b",
        r"\b(itau|itaú)\b",
        r"\b(brou)\b",
        r"\b(santander)\b",
        r"\b(scotiabank)\b",
        r"\b(bbva)\b",
        r"\b(mercado pago|mercadopago)\b",
        r"\b(visa)\b",
        r"\b(mastercard|master)\b",
    ]
    for pat in pm_patterns:
        m = re.search(pat, t)
        if m:
            medio_pago = m.group(1).title()
            break

    return {
        "monto": monto,
        "currency": currency,
        "comercio": comercio,
        "categoria": categoria,
        "subcategoria": subcategoria,
        "medio_pago": medio_pago,
        "notas": texto.strip(),
        "confidence": 0.70 if monto is not None else 0.30,
        "engine_used": "regex-uruguay-fallback",
    }


async def parse_expense_with_ollama(texto: str) -> dict | None:
    """Envía la transcripción a Ollama (Gemma 2:2b) para extracción estructurada."""
    if not texto or not texto.strip():
        return None

    prompt = _SYSTEM_PROMPT.format(texto=texto)
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 256,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            raw_response = data.get("response", "").strip()

            # Extraer JSON entre llaves
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if not match:
                logger.warning(
                    "[VOICE_NLP] Ollama no devolvió JSON: %s", raw_response[:80]
                )
                return None

            parsed = json.loads(match.group(0))

            # Convertir monto a Decimal si está presente
            monto_val = parsed.get("monto")
            monto_dec: Decimal | None = None
            if monto_val is not None:
                try:
                    monto_dec = Decimal(str(monto_val))
                except (InvalidOperation, ValueError):
                    pass

            return {
                "monto": monto_dec,
                "currency": parsed.get("currency") or "UYU",
                "comercio": parsed.get("comercio"),
                "categoria": parsed.get("categoria"),
                "subcategoria": parsed.get("subcategoria"),
                "medio_pago": parsed.get("medio_pago"),
                "notas": parsed.get("notas") or texto.strip(),
                "confidence": 0.95 if monto_dec is not None else 0.50,
                "engine_used": f"ollama-{settings.ollama_model}",
            }
    except Exception as e:
        logger.warning("[VOICE_NLP] Error consultando Ollama: %s", e)
        return None
