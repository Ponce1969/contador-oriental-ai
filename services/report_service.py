"""
Servicio de generación de informes PDF para el Contador Oriental.
Usa fpdf2 con soporte UTF-8 nativo (no requiere fuentes externas).
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime

from fpdf import FPDF
from result import Err, Ok, Result

from models.ai_model import AIContext

logger = logging.getLogger(__name__)

# Colores institucionales (RGB)
_AZUL_HEADER = (33, 90, 168)
_AZUL_CLARO = (220, 232, 255)
_VERDE_CLARO = (212, 237, 218)
_GRIS_TABLA = (240, 240, 240)
_GRIS_OSCURO = (33, 37, 41)
_BLANCO = (255, 255, 255)  # noqa: E501


class ReportService:
    """Genera informes PDF con datos financieros y consejos del Contador Oriental."""

    REPORTS_DIR = "assets/reports"

    def __init__(self) -> None:
        os.makedirs(self.REPORTS_DIR, exist_ok=True)

    def _limpiar_emojis(self, texto: str) -> str:
        """Elimina emojis y caracteres fuera del rango Latin-1 (helvetica)."""
        return re.sub(r"[^\x00-\xFF]", "", texto).strip()

    def _limpiar_markdown(self, texto: str) -> str:
        """Elimina sintaxis Markdown para texto plano en PDF."""
        texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto)
        texto = re.sub(r"\*(.*?)\*", r"\1", texto)
        texto = re.sub(r"#{1,6}\s*", "", texto)
        texto = re.sub(r"`(.*?)`", r"\1", texto)
        return self._limpiar_emojis(texto)

    def generar_informe_pdf(
        self,
        contexto: AIContext,
        consejo_ia: str,
        familia_nombre: str,
        pregunta_usuario: str = "",
        custom_path: str | None = None,
    ) -> Result[str, Exception]:
        """
        Genera un PDF con resumen financiero + tabla de gastos + consejo de la IA.

        Args:
            contexto: AIContext con todos los datos pre-calculados por Python
            consejo_ia: Respuesta del Contador Oriental (puede contener Markdown)
            familia_nombre: Nombre de la familia para el encabezado
            pregunta_usuario: Pregunta original del usuario (opcional)

        Returns:
            Ok(filepath) con la ruta del archivo generado, o Err(exception)
        """
        try:
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=20)
            pdf.add_page()

            self._encabezado(pdf, familia_nombre)
            self._seccion_resumen(pdf, contexto)
            self._seccion_tabla_gastos(pdf, contexto)
            self._seccion_metodos_pago(pdf, contexto)
            self._seccion_consejo(pdf, consejo_ia, pregunta_usuario)
            self._pie_pagina(pdf)

            filename = (
                f"Informe_{familia_nombre.replace(' ', '_')}"
                f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            filepath = custom_path or os.path.join(self.REPORTS_DIR, filename)
            pdf.output(filepath)

            logger.info(f"PDF generado: {filepath}")
            return Ok(filepath)

        except Exception as e:
            logger.error(f"Error generando PDF: {e}")
            return Err(e)

    def _encabezado(self, pdf: FPDF, familia_nombre: str) -> None:
        """Encabezado institucional con título y fecha."""
        r, g, b = _AZUL_HEADER
        pdf.set_fill_color(r, g, b)
        pdf.rect(0, 0, 210, 35, style="F")

        pdf.set_y(8)
        pdf.set_font("helvetica", "B", 18)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, "AUDITOR FAMILIAR", align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("helvetica", "", 10)
        pdf.cell(
            0, 6,
            f"  Informe Mensual  |  Familia: {self._limpiar_emojis(familia_nombre)}  |  "
            f"{datetime.now().strftime('%d/%m/%Y %H:%M')}",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(12)
        pdf.set_text_color(*_GRIS_OSCURO)

    def _seccion_resumen(self, pdf: FPDF, ctx: AIContext) -> None:
        """Bloque de resumen numérico: ingresos, gastos, balance."""
        balance = ctx.ingresos_total - ctx.total_gastos_mes
        balance_color = (39, 174, 96) if balance >= 0 else (192, 57, 43)

        self._titulo_seccion(pdf, "Resumen del Mes", _AZUL_CLARO)

        pdf.set_font("helvetica", "", 11)
        pdf.set_text_color(*_GRIS_OSCURO)

        datos = [
            ("Ingresos totales", f"$ {ctx.ingresos_total:,.0f}"),
            ("Total gastos del mes", f"$ {ctx.total_gastos_mes:,.0f}"),
            ("Miembros del hogar", str(ctx.miembros_count)),
        ]
        for label, valor in datos:
            pdf.cell(95, 8, f"  {label}:", new_x="RIGHT", new_y="TOP")
            pdf.set_font("helvetica", "B", 11)
            pdf.cell(95, 8, valor, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "", 11)

        # Balance con color dinámico
        pdf.cell(95, 8, "  Balance del mes:", new_x="RIGHT", new_y="TOP")
        pdf.set_font("helvetica", "B", 11)
        pdf.set_text_color(*balance_color)
        signo = "+" if balance >= 0 else ""
        pdf.cell(95, 8, f"{signo}$ {balance:,.0f}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*_GRIS_OSCURO)
        pdf.ln(6)

    def _seccion_tabla_gastos(self, pdf: FPDF, ctx: AIContext) -> None:
        """Tabla con desglose de gastos por categoría."""
        if not ctx.resumen_gastos:
            return

        self._titulo_seccion(pdf, "Desglose de Gastos por Categoria", _AZUL_CLARO)

        # Cabecera de tabla
        pdf.set_font("helvetica", "B", 10)
        pdf.set_fill_color(*_GRIS_TABLA)
        pdf.set_text_color(*_GRIS_OSCURO)
        pdf.cell(80, 8, " Categoria", border=1, fill=True)
        pdf.cell(60, 8, " Descripcion", border=1, fill=True)
        pdf.cell(25, 8, "Compras", border=1, fill=True, align="C")
        pdf.cell(25, 8, "Total", border=1, fill=True, align="R")
        pdf.ln()

        pdf.set_font("helvetica", "", 9)
        total_tabla = 0.0
        fill = False

        for categoria, items in ctx.resumen_gastos.items():
            cat_limpia = self._limpiar_emojis(categoria)
            for descripcion, datos in items.items():
                desc_limpia = self._limpiar_emojis(descripcion)
                monto: float = datos["total"]
                cantidad: int = datos["cantidad"]
                total_tabla += monto

                if fill:
                    pdf.set_fill_color(248, 248, 248)
                else:
                    pdf.set_fill_color(*_BLANCO)

                pdf.cell(80, 7, f" {cat_limpia}", border=1, fill=True)
                pdf.cell(60, 7, f" {desc_limpia}", border=1, fill=True)
                pdf.cell(25, 7, str(cantidad), border=1, fill=True, align="C")
                pdf.cell(
                    25, 7, f"${monto:,.0f}", border=1, fill=True, align="R"
                )
                pdf.ln()
                fill = not fill

        # Fila de total
        pdf.set_font("helvetica", "B", 10)
        pdf.set_fill_color(*_GRIS_TABLA)
        pdf.cell(80 + 60 + 25, 8, " TOTAL CONSULTADO", border=1, fill=True)
        pdf.cell(25, 8, f"${total_tabla:,.0f}", border=1, fill=True, align="R")
        pdf.ln(8)

    def _seccion_metodos_pago(self, pdf: FPDF, ctx: AIContext) -> None:
        """Línea con resumen de métodos de pago si está disponible."""
        if not ctx.resumen_metodos_pago:
            return

        pdf.set_font("helvetica", "I", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(
            0, 6,
            f"  Metodos de pago: {self._limpiar_emojis(ctx.resumen_metodos_pago)}",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.set_text_color(*_GRIS_OSCURO)
        pdf.ln(4)

    def _seccion_consejo(
        self, pdf: FPDF, consejo_ia: str, pregunta: str
    ) -> None:
        """Bloque con la pregunta del usuario y el consejo del Contador Oriental."""
        self._titulo_seccion(pdf, "Analisis del Contador Oriental", _VERDE_CLARO)

        if pregunta:
            pdf.set_font("helvetica", "I", 10)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(0, 6, f'  Consulta: "{pregunta}"')
            pdf.ln(3)

        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(*_GRIS_OSCURO)
        consejo_limpio = self._limpiar_markdown(consejo_ia)
        pdf.multi_cell(0, 7, f"  {consejo_limpio}")
        pdf.ln(4)

    def _titulo_seccion(self, pdf: FPDF, titulo: str, color_rgb: tuple) -> None:
        """Renderiza un título de sección con fondo de color."""
        r, g, b = color_rgb
        pdf.set_fill_color(r, g, b)
        pdf.set_font("helvetica", "B", 11)
        pdf.set_text_color(*_GRIS_OSCURO)
        pdf.cell(0, 9, f"  {titulo}", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.ln(2)

    def _pie_pagina(self, pdf: FPDF) -> None:
        """Pie de página con aviso de privacidad."""
        pdf.set_y(-18)
        pdf.set_font("helvetica", "I", 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(
            0, 8,
            "Generado localmente por el Contador Oriental  |  "
            "Sus datos son privados y no salen de su dispositivo.",
            align="C",
        )
