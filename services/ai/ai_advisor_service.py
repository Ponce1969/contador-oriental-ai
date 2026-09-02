"""
Servicio de asesoría con IA - Contador Oriental (arquitectura híbrida)

Orquestador que decide entre Gemma 2:2b (local) y Llama 3 70B (cloud NVIDIA)
basado en la complejidad de la pregunta y la cuota disponible.
"""

from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Any

from result import Err, Ok, Result

from models.ai_model import AIContext, AIRequest, AIResponse
from models.errors import AppError
from services.ai.model_router import ModelRouter
from services.infrastructure.formatters import format_pesos_ai
from services.infrastructure.nvidia_client import NVIDIAClient

logger = logging.getLogger(__name__)


class AIAdvisorService:
    """
    Servicio para consultar al Contador Oriental.

    Arquitectura híbrida:
    - Gemma 2:2b (Ollama local) para consultas simples y fallback
    - Llama 3 70B (NVIDIA cloud) para consultas complejas/normativas
    - ModelRouter decide qué modelo usar
    - QuotaManager controla cuotas diarias de Llama 3
    """

    def __init__(
        self,
        model_router: ModelRouter | None = None,
        nvidia_client: NVIDIAClient | None = None,
        knowledge_path: str = "./knowledge",
    ):
        self.router = model_router or ModelRouter()
        self.nvidia_client = nvidia_client or NVIDIAClient()
        self.knowledge_path = knowledge_path
        self.mapa_conocimiento = {
            "irpf_familia_uy.md": {
                "keywords": [
                    "irpf",
                    "impuesto",
                    "hijo",
                    "alquiler",
                    "deduccion",
                    "dgi",
                    "devolucion",
                    "hipoteca",
                ],
                "peso": 2,
            },
            "inclusion_financiera_uy.md": {
                "keywords": [
                    "iva",
                    "tarjeta",
                    "debito",
                    "credito",
                    "descuento",
                    "inclusion financiera",
                    "beneficio tarjeta",
                ],
                "peso": 1,
            },
            "ahorro_ui_uy.md": {
                "keywords": [
                    "ahorro",
                    "ui",
                    "unidad indexada",
                    "inflacion",
                    "plazo fijo",
                    "invertir",
                    "banco",
                ],
                "peso": 1,
            },
            "sucive_patentes_uy.md": {
                "keywords": [
                    "patente",
                    "sucive",
                    "vencimiento",
                    "automotor",
                    "vehiculo",
                    "descuento",
                    "rodado",
                    "cuota patente",
                ],
                "peso": 2,
            },
            "iva_general_uy.md": {
                "keywords": [
                    "iva",
                    "tasa basica",
                    "tasa minima",
                    "exento",
                    "22%",
                    "10%",
                    "puntos iva",
                    "factura",
                    "precio con iva",
                ],
                "peso": 2,
            },
            "bps_aportes_uy.md": {
                "keywords": [
                    "bps",
                    "aportes",
                    "jubilacion",
                    "fonasa",
                    "monotributo",
                    "servicio domestico",
                    "unipersonal",
                    "planilla",
                    "empleado",
                    "empleador",
                ],
                "peso": 2,
            },
            "iass_pasividades_uy.md": {
                "keywords": [
                    "iass",
                    "pasividad",
                    "pasividades",
                    "jubilacion",
                    "jubilado",
                    "pension",
                    "pensiones",
                    "retiro",
                    "9 bpc",
                    "multicaixa",
                ],
                "peso": 3,
            },
            "aguinaldo_vacacional_uy.md": {
                "keywords": [
                    "aguinaldo",
                    "sueldo anual complementario",
                    "sac",
                    "junio",
                    "diciembre",
                    "vacacional",
                    "salario vacacional",
                    "licencia",
                    "12.840",
                    "16.101",
                ],
                "peso": 3,
            },
            "independientes_regimenes_uy.md": {
                "keywords": [
                    "literal e",
                    "pequeña empresa",
                    "monotributo",
                    "mides",
                    "cjppu",
                    "caja profesional",
                    "servicios personales",
                    "anticipo irpf",
                    "305.000 ui",
                    "183.000 ui",
                ],
                "peso": 3,
            },
        }

    def _seleccionar_contexto(self, pregunta: str) -> tuple[str, str | None]:
        """
        Selecciona el archivo de conocimiento más relevante

        Returns:
            (contenido_archivo, nombre_archivo)
        """
        pregunta_lower = pregunta.lower()
        scores = {}

        for archivo, config in self.mapa_conocimiento.items():
            kws = config.get("keywords") if isinstance(config, dict) else []
            keywords_list = kws if isinstance(kws, list) else []
            raw_peso = config.get("peso", 1) if isinstance(config, dict) else 1
            peso: int = int(raw_peso) if isinstance(raw_peso, (int, float, str)) else 1
            score = sum(
                peso for palabra in keywords_list if str(palabra) in pregunta_lower
            )
            scores[archivo] = score

        archivo_seleccionado = max(scores, key=lambda k: scores[k])

        if scores[archivo_seleccionado] > 0:
            ruta = os.path.join(self.knowledge_path, archivo_seleccionado)
            try:
                with open(ruta, encoding="utf-8") as f:
                    return f.read(), archivo_seleccionado
            except FileNotFoundError:
                return "", None

        return "", None

    @staticmethod
    def _es_pregunta_laboral(pregunta: str) -> bool:
        """Determina si la consulta involucra sueldos, aportes o beneficios."""
        if not pregunta:
            return True
        p = pregunta.lower()
        keywords = (
            "sueldo",
            "sueldos",
            "salario",
            "salarios",
            "aguinaldo",
            "aguinaldos",
            "sac",
            "vacacional",
            "vacacionales",
            "vacacion",
            "vacaciones",
            "licencia",
            "jubilacion",
            "jubilación",
            "pension",
            "pensión",
            "pasividad",
            "pasivo",
            "pasivos",
            "bps",
            "fonasa",
            "montepio",
            "montepío",
            "frl",
            "irpf",
            "retencion",
            "retención",
            "iass",
            "nominal",
            "liquido",
            "líquido",
            "en mano",
            "cobro",
            "cobros",
            "cobrar",
            "diciembre",
            "junio",
            "despido",
            "aportes",
            "laboral",
            "laborales",
            "trabajo",
            "empleo",
            "empleado",
            "patronal",
            "dependiente",
            "independiente",
            "unipersonal",
            "servicios personales",
            "honorario",
            "honorarios",
        )
        return any(k in p for k in keywords)

    @staticmethod
    def _es_pregunta_cuotas(pregunta: str) -> bool:
        """Determina si la consulta requiere la proyección de cuotas futuras."""
        if not pregunta:
            return True
        p = pregunta.lower()
        keywords = (
            "cuota",
            "cuotas",
            "tarjeta",
            "tarjetas",
            "credito",
            "crédito",
            "meses que vienen",
            "proximo mes",
            "próximo mes",
            "proximos meses",
            "próximos meses",
            "futuro",
            "futuros",
            "proyeccion",
            "proyección",
            "financiamiento",
            "puedo comprar",
            "puedo gastar",
            "endeud",
            "deuda",
            "financiar",
        )
        return any(k in p for k in keywords)

    @staticmethod
    def _es_pregunta_comparativa(pregunta: str) -> bool:
        """Determina si la consulta pide comparar con meses anteriores."""
        if not pregunta:
            return True
        p = pregunta.lower()
        keywords = (
            "comparar",
            "comparativa",
            "vs",
            "respecto",
            "mes pasado",
            "mes anterior",
            "aumento",
            "aumentó",
            "subio",
            "subió",
            "bajo",
            "bajó",
            "diferencia",
            "variacion",
            "variación",
            "mas que",
            "más que",
            "menos que",
            "evolucion",
            "evolución",
            "como vengo",
            "cómo vengo",
            "analisis",
            "análisis",
            "tendencia",
            "resumen general",
        )
        return any(k in p for k in keywords)

    @staticmethod
    def _es_pregunta_memoria(pregunta: str) -> bool:
        """Determina si la consulta requiere contexto histórico RAG de pgvector."""
        if not pregunta:
            return True
        p = pregunta.lower()
        keywords = (
            "recuerdo",
            "recuerdas",
            "acordas",
            "acordás",
            "historico",
            "histórico",
            "historial",
            "alguna vez",
            "cuando fue",
            "cuándo fue",
            "cuando compre",
            "cuándo compré",
            "arreglo",
            "auto",
            "pasado",
        )
        return any(k in p for k in keywords)

    @staticmethod
    def _es_pregunta_historica_o_rango(pregunta: str) -> bool:
        """Determina si la consulta refiere a meses anteriores o históricos."""
        if not pregunta:
            return False
        p = pregunta.lower()
        keywords = (
            "mes anterior",
            "mes pasado",
            "historico",
            "histórico",
            "historial",
            "anterior",
            "pasado",
            "año pasado",
        )
        return any(k in p for k in keywords)

    @staticmethod
    def _es_pregunta_metas(pregunta: str) -> bool:
        """Determina si la consulta involucra metas de ahorro o alcancías del hogar."""
        if not pregunta:
            return True
        p = pregunta.lower()
        keywords = (
            "meta",
            "metas",
            "ahorro",
            "ahorros",
            "ahorrar",
            "alcancia",
            "alcancía",
            "chanchito",
            "objetivo",
            "objetivos",
            "viaje",
            "vacacion",
            "vacaciones",
            "fondo",
            "llegamos",
            "cuanto falta",
            "cuánto falta",
        )
        return any(k in p for k in keywords)

    def _formatear_datos_financieros(self, ctx: AIContext, pregunta: str = "") -> str:
        """
        Prepara el bloque de datos financieros para el Prompt del Asesor.
        Todos los valores ya vienen calculados en ctx; el modelo solo narra.

        Args:
            ctx: Contexto financiero pre-calculado por Python
            pregunta: Pregunta del usuario para adaptar la granularidad

        Returns:
            String formateado con el resumen financiero
        """
        lineas: list[str] = [
            "### ESTADO DE LA HACIENDA FAMILIAR ###",
            f"- Miembros en el hogar: {ctx.miembros_count}",
            f"- Ingresos totales {ctx.periodo_label}:",
        ]
        ingresos_dict = ctx.ingresos_por_moneda or (
            {"UYU": ctx.ingresos_total}
            if ctx.ingresos_total > Decimal("0")
            else {"UYU": Decimal("0")}
        )
        for ccy in sorted(ingresos_dict.keys()):
            ingresos_str = format_pesos_ai(ingresos_dict[ccy], currency=ccy)
            lineas.append(f"  * {ccy}: {ingresos_str}")

        lineas.append(f"- TOTAL gastos {ctx.periodo_label} (todas las categorías):")
        gastos_dict = ctx.gastos_por_moneda or (
            {"UYU": ctx.total_gastos_mes}
            if ctx.total_gastos_mes > Decimal("0")
            else {"UYU": Decimal("0")}
        )
        for ccy in sorted(gastos_dict.keys()):
            gastos_str = format_pesos_ai(gastos_dict[ccy], currency=ccy)
            lineas.append(f"  * {ccy}: {gastos_str}")

        lineas.append(f"- BALANCE {ctx.periodo_label} (Ingresos - Gastos) por moneda:")
        all_ccy = set(ingresos_dict.keys()) | set(gastos_dict.keys())
        if not all_ccy:
            all_ccy = {"UYU"}
        for ccy in sorted(all_ccy):
            ingresos_val = ingresos_dict.get(ccy, Decimal("0"))
            gastos_val = gastos_dict.get(ccy, Decimal("0"))
            balance_mes = ingresos_val - gastos_val
            balance_str = format_pesos_ai(balance_mes, currency=ccy)
            lineas.append(f"  * {ccy}: {balance_str}")

        if ctx.cotizacion_dolar:
            # Formato inequivoco para IA: coma decimal, sin punto
            cotizacion_2d = ctx.cotizacion_dolar.quantize(Decimal("0.01"))
            entero = int(cotizacion_2d)
            decimal_part = int((cotizacion_2d - entero) * 100)
            entero_str = f"{entero:,}".replace(",", " ")
            cotizacion_str = f"{entero_str},{decimal_part:02d}"
            lineas.append(f"- Cotización del dólar hoy: 1 USD = $ {cotizacion_str}")

        if ctx.resumen_metodos_pago:
            metodos_label = (
                f"- Métodos de pago usados {ctx.periodo_label}:"
                f" {ctx.resumen_metodos_pago}"
            )
            lineas.append(metodos_label)

        if ctx.subtotal_descripcion and ctx.terminos_buscados:
            subtotal_str = (
                f"- *** RESPUESTA DIRECTA: '{ctx.terminos_buscados}'"
                f" {ctx.periodo_label}"
                f" = {format_pesos_ai(ctx.subtotal_descripcion)} ***"
            )
            lineas.append(subtotal_str)

        # Proyección de cuotas futuras solo si la consulta es relevante
        if ctx.proyeccion_cuotas and self._es_pregunta_cuotas(pregunta):
            lineas.append("")
            lineas.append("PROYECCION DE CUOTAS FUTURAS:")
            for mes, total in ctx.proyeccion_cuotas.items():
                lineas.append(f"  {mes}: {format_pesos_ai(total)}")
            lineas.append(
                "Usa esta proyeccion para advertir si un nuevo gasto "
                "comprometeria meses futuros."
            )

        # ── Empalme: cierre de mes anterior (solo si no hay gastos o son históricos)
        if ctx.empalme_mes_label and (
            self._es_pregunta_historica_o_rango(pregunta) or ctx.total_gastos_count == 0
        ):
            balance_empalme = ctx.empalme_ingresos_total - ctx.empalme_total_gastos
            lineas.append("")
            lineas.append(f"### CIERRE DEL MES ANTERIOR ({ctx.empalme_mes_label}) ###")
            lineas.append(f"- Ingresos: {format_pesos_ai(ctx.empalme_ingresos_total)}")
            lineas.append(
                f"- Total gastos: {format_pesos_ai(ctx.empalme_total_gastos)}"
            )
            lineas.append(f"- Balance: {format_pesos_ai(balance_empalme)}")

            if ctx.empalme_gastos:
                lineas.append("DETALLE DE GASTOS DEL MES ANTERIOR:")
                for categoria, items in ctx.empalme_gastos.items():
                    total_cat = sum(
                        (Decimal(str(d["total"])) for d in items.values()),
                        Decimal("0"),
                    )
                    cant_cat = sum(d["cantidad"] for d in items.values())
                    lineas.append(
                        f"  📂 {categoria}"
                        f" → {format_pesos_ai(total_cat)}"
                        f" ({cant_cat} transacciones):"
                    )
                    for (descripcion, ccy), datos in items.items():
                        monto = Decimal(str(datos["total"]))
                        cantidad = datos["cantidad"]
                        metodos = datos.get("metodos", {})
                        metodo_str = ", ".join(f"{m}({c}x)" for m, c in metodos.items())
                        monto_str = format_pesos_ai(monto, currency=ccy)
                        if cantidad > 1:
                            lineas.append(
                                f"    - {descripcion}: {monto_str}"
                                f" ({cantidad}x, {metodo_str})"
                            )
                        else:
                            lineas.append(
                                f"    - {descripcion}: {monto_str} ({metodo_str})"
                            )

            lineas.append(
                "NOTA: Estos datos son del mes anterior ("
                f"{ctx.empalme_mes_label}). Los datos del mes en curso"
                " están arriba."
            )

        lineas += [
            "",
            "DETALLE DE GASTOS CONSULTADOS (cada línea = una transacción real):",
        ]

        total_filtrado: dict[str, Decimal] = {}

        if not ctx.resumen_gastos:
            lineas.append("- No hay gastos registrados en este contexto.")
        else:
            for categoria, items in ctx.resumen_gastos.items():
                total_categoria: dict[str, Decimal] = {}
                cant_categoria: dict[str, int] = {}
                for (_, ccy), datos in items.items():
                    monto = Decimal(str(datos["total"]))

                    cantidad = datos["cantidad"]
                    metodos = datos.get("metodos", {})
                    total_categoria[ccy] = (
                        total_categoria.get(ccy, Decimal("0")) + monto
                    )
                    cant_categoria[ccy] = cant_categoria.get(ccy, 0) + cantidad
                    total_filtrado[ccy] = total_filtrado.get(ccy, Decimal("0")) + monto

                lineas.append(f"\n📂 {categoria}")
                for ccy in sorted(total_categoria.keys()):
                    lineas.append(
                        f"  → SUBTOTAL {ccy}:"
                        f" {format_pesos_ai(total_categoria[ccy], currency=ccy)}"
                        f" ({cant_categoria[ccy]} transacciones)"
                    )
                for (descripcion, ccy), datos in items.items():
                    monto = Decimal(str(datos["total"]))
                    cantidad = datos["cantidad"]
                    metodos = datos.get("metodos", {})
                    metodo_str = ", ".join(f"{m}({c}x)" for m, c in metodos.items())
                    monto_str = format_pesos_ai(monto, currency=ccy)
                    if cantidad > 1:
                        lineas.append(
                            f"  - {descripcion}: {monto_str} total"
                            f" ({cantidad} transacciones separadas, {metodo_str})"
                        )
                    else:
                        lineas.append(f"  - {descripcion}: {monto_str} ({metodo_str})")

        lineas.append("")
        lineas.append("SUBTOTAL CONSULTADO:")
        for ccy in sorted(total_filtrado.keys()):
            total_str = format_pesos_ai(total_filtrado[ccy], currency=ccy)
            lineas.append(f"  * {ccy}: {total_str}")
        lineas.append(f"({ctx.total_gastos_count} transacciones)")

        return "\n".join(lineas)

    def _formatear_datos_laborales(
        self, ctx: AIContext | None, pregunta: str = ""
    ) -> str:
        """
        Formatea los datos de sueldos, beneficios y aguinaldos del hogar
        pre-calculados por Python para el prompt de la IA.
        Solo se inyecta si la pregunta involucra temática laboral o perfiles.
        """
        if not ctx or not ctx.resumen_laboral:
            return ""

        if pregunta and not self._es_pregunta_laboral(pregunta):
            return ""

        return (
            "### CONTEXTO, SUELDOS Y BENEFICIOS LABORALES DEL HOGAR "
            "(PRE-CALCULADO POR PYTHON) ###\n"
            f"{ctx.resumen_laboral}\n"
            "REGLA ESTRICTA PARA LA IA: Utilizar los números laborales y "
            "totales consolidados anteriores de forma textual para responder "
            "sobre sueldos netos, aguinaldos, salario vacacional o cobros a "
            "fin de año. NUNCA inventes cálculos ni discrepes con estos valores.\n\n"
        )

    def _formatear_datos_metas(self, ctx: AIContext | None, pregunta: str = "") -> str:
        """
        Formatea los datos de metas de ahorro y alcancías del hogar.
        Solo se inyecta si hay metas activas y la pregunta es sobre metas/ahorro.
        """
        if not ctx or not ctx.resumen_metas:
            return ""

        if pregunta and not self._es_pregunta_metas(pregunta):
            return ""

        return (
            "### METAS DE AHORRO Y ALCANCÍAS DEL HOGAR "
            "(PRE-CALCULADO POR PYTHON) ###\n"
            f"{ctx.resumen_metas}\n"
            "REGLA ESTRICTA PARA LA IA: Utilizar los números de metas, avances "
            "y montos faltantes anteriores de forma textual. "
            "NUNCA inventes cálculos.\n\n"
        )

    def _es_pregunta_irpf_familiar(self, pregunta: str) -> bool:
        """Determina si la consulta es sobre IRPF, núcleo familiar, alquiler o DGI."""
        keywords = [
            "irpf",
            "nucleo",
            "núcleo",
            "familiar",
            "matrimonio",
            "conyuge",
            "cónyuge",
            "concubino",
            "concubinato",
            "declaracion",
            "declaración",
            "dgi",
            "alquiler",
            "arrendamiento",
            "devolucion",
            "devolución",
            "crédito fiscal",
            "credito fiscal",
        ]
        p_lower = pregunta.lower()
        return any(kw in p_lower for kw in keywords)

    def _formatear_datos_irpf_familiar(
        self, ctx: AIContext | None, pregunta: str = ""
    ) -> str:
        """
        Formatea los datos de optimización de IRPF Núcleo Familiar vs Individual.
        Solo se inyecta si hay resumen precalculado y la pregunta es sobre IRPF/DGI.
        """
        if not ctx or not ctx.resumen_irpf_familiar:
            return ""

        if pregunta and not self._es_pregunta_irpf_familiar(pregunta):
            return ""

        return (
            "### OPTIMIZACIÓN IRPF NÚCLEO FAMILIAR VS INDIVIDUAL "
            "(PRE-CALCULADO POR PYTHON) ###\n"
            f"{ctx.resumen_irpf_familiar}\n"
            "REGLA ESTRICTA PARA LA IA: Utilizar las cifras de IRPF individual, "
            "núcleo familiar, ahorro y créditos por alquiler de forma textual. "
            "NUNCA inventes cálculos ni discrepes con estos valores.\n\n"
        )

    @staticmethod
    def _es_pregunta_calendario_fiscal(pregunta: str) -> bool:
        """Determina si la consulta involucra vencimientos o calendario fiscal."""
        if not pregunta:
            return True
        p = pregunta.lower()
        keywords = (
            "vencimiento",
            "vence",
            "calendario",
            "dgi",
            "bps",
            "cjppu",
            "cuando pago",
            "cuándo pago",
            "cuando tengo que pagar",
            "cuándo tengo que pagar",
            "fecha de pago",
            "fechas de pago",
            "anticipo",
            "cuota",
            "tributo",
            "impuesto",
            "literal e",
        )
        return any(k in p for k in keywords)

    def _formatear_datos_calendario_fiscal(
        self, ctx: AIContext | None, pregunta: str = ""
    ) -> str:
        """
        Formatea los vencimientos del calendario fiscal oficial.
        """
        if not ctx or not ctx.resumen_calendario_fiscal:
            return ""

        if pregunta and not self._es_pregunta_calendario_fiscal(pregunta):
            return ""

        return (
            "### CALENDARIO FISCAL Y VENCIMIENTOS OFICIALES "
            "(PRE-CALCULADO POR PYTHON) ###\n"
            f"{ctx.resumen_calendario_fiscal}\n"
            "REGLA ESTRICTA PARA LA IA: Las fechas y fuentes normativas son oficiales. "
            "Diferenciá claramente si un monto es oficial o estimado. "
            "NUNCA inventes fechas.\n\n"
        )

    def _formatear_comparativa(self, ctx: AIContext, pregunta: str = "") -> str:
        """
        Convierte CategoryMetric en hechos contables narrativos para el prompt.
        Python pre-calcula todo; el modelo solo lee y narra.
        Solo se inyecta si la consulta amerita comparación con meses anteriores.
        """
        if not ctx.comparativa_meses or not self._es_pregunta_comparativa(pregunta):
            return ""

        lineas: list[str] = [
            "",
            "### COMPARATIVA VS MES ANTERIOR ###",
        ]

        for m in ctx.comparativa_meses:
            vt = m.variacion_total_pct
            vtk = m.variacion_ticket_pct
            diag = m.diagnostico

            ccy = getattr(m, "currency", "UYU")
            if vt is None:
                actual_str = format_pesos_ai(m.total_actual, currency=ccy)
                lineas.append(
                    f"- {m.categoria}: {actual_str} este mes"
                    f" (sin datos del mes anterior para comparar)."
                )
                continue

            partes = [f"- {m.categoria}:"]
            if vt is not None:
                signo = "+" if vt > 0 else ""
                partes.append(f"total {signo}{vt:.1f}% vs mes anterior")
            if vtk is not None:
                signo_k = "+" if vtk > 0 else ""
                partes.append(f"gasto promedio por compra {signo_k}{vtk:.1f}%")
            if diag:
                partes.append(f"({diag})")

            lineas.append(" ".join(partes))

        return "\n".join(lineas)

    def _construir_prompt(
        self,
        pregunta: str,
        contexto_legal: str,
        gastos_formateados: str,
        memoria_vectorial: str = "",
        cuota_agotada: bool = False,
        modelo: str = "gemma2",
        ctx: AIContext | None = None,
    ) -> str:
        """
        Construye el prompt optimizado para el modelo seleccionado.

        Args:
            pregunta: La pregunta del usuario.
            contexto_legal: Texto de conocimiento RAG.
            gastos_formateados: Resumen financiero pre-calculado.
            memoria_vectorial: Contexto histórico de pgvector.
            cuota_agotada: Si True, agrega aviso de precisión reducida.
            modelo: 'gemma2' o 'llama3' — ajusta restricciones del prompt.
            ctx: Contexto financiero y laboral completo del hogar.
        """
        # Filtrar memoria vectorial solo si la pregunta pide historial/recuerdos
        if memoria_vectorial and not self._es_pregunta_memoria(pregunta):
            memoria_vectorial = ""

        seccion_rag = (
            f"NORMATIVA URUGUAYA RELEVANTE:\n{contexto_legal}\n"
            if contexto_legal
            else ""
        )

        seccion_memoria = (
            f"CONTEXTO HISTÓRICO (meses anteriores, solo referencia):\n"
            f"{memoria_vectorial}\n"
            f"IMPORTANTE: estos registros históricos son de meses anteriores."
            f" Los datos reales del mes actual están abajo.\n"
            if memoria_vectorial
            else ""
        )

        seccion_laboral = self._formatear_datos_laborales(ctx, pregunta=pregunta)
        seccion_metas = self._formatear_datos_metas(ctx, pregunta=pregunta)
        seccion_irpf = self._formatear_datos_irpf_familiar(ctx, pregunta=pregunta)
        seccion_calendario = self._formatear_datos_calendario_fiscal(
            ctx, pregunta=pregunta
        )
        seccion_gastos = f"{gastos_formateados}\n" if gastos_formateados else ""

        # Aviso cuando la cuota de Llama 3 está agotada y cae a Gemma 2
        aviso_cuota = ""
        if cuota_agotada:
            aviso_cuota = (
                "\nADVERTENCIA: Estás respondiendo con información limitada "
                "(modelo local). Sé conservador y agregá que la respuesta "
                "puede ser menos precisa.\n"
            )

        if modelo == "gemma2":
            p_head = (
                "Sos el Contador Oriental, contador público uruguayo.\n"
                "Respondé DIRECTAMENTE a la PREGUNTA en español rioplatense, "
                "de forma clara, profesional y concisa.\n\n"
                "REGLAS ESTRICTAS:\n"
                "- INSTRUCCIÓN PRINCIPAL: Respondé DIRECTAMENTE a la PREGUNTA.\n"
                "- NUNCA hacer cálculos por tu cuenta. NUNCA inventar números. "
                "Usá los datos provistos.\n"
                "- Los totales y balances YA están calculados. Solo leer y narrar.\n"
                "- Si un dato no aparece explícitamente en los datos, NO lo inventes.\n"
                "- Reportá cada moneda por separado: $ para UYU, USD para USD. "
                "NUNCA conviertas ni sumes monedas distintas.\n"
                "- TONO: Profesional pero cercano y pedagógico."
            )
            return (
                f"{p_head}\n"
                f"{aviso_cuota}\n"
                f"{seccion_rag}{seccion_memoria}{seccion_laboral}{seccion_metas}{seccion_irpf}{seccion_calendario}{seccion_gastos}"
                f"PREGUNTA DEL USUARIO: {pregunta}\n\n"
                f"RESPUESTA DIRECTA:"
            )

        instruccion_enfoque = (
            "- INSTRUCCIÓN PRINCIPAL: Respondé DIRECTAMENTE a la PREGUNTA.\n"
            "- Si la pregunta es sobre normativa, leyes, IRPF, aguinaldo o IASS, "
            "explicá la ley aplicable de forma clara.\n"
            "- Si la pregunta es sobre sueldos, aguinaldos, cobro a fin de año o "
            "vacaciones, utilizá los valores precalculados en la sección laboral.\n"
            "- Si la pregunta es sobre metas de ahorro o alcancías, utilizá los "
            "valores precalculados en la sección de metas.\n"
            "- Si la pregunta es sobre IRPF familiar, núcleo familiar o "
            "crédito de alquiler, utilizá los valores en la sección de IRPF.\n"
            "- Si la pregunta es sobre vencimientos o calendario fiscal, "
            "utilizá las fechas oficiales precalculadas en la sección de calendario.\n"
            "- Solo mencioná gastos o saldo si la pregunta consulta expresamente "
            "sobre su presupuesto o historial.\n"
        )

        prompt = (
            f"Sos el Contador Oriental, contador público uruguayo.\n\n"
            f"TU ROL:\n"
            f"- Responder en español rioplatense de forma clara y profesional.\n"
            f"- Explicar las normas contables y laborales cuando te lo pidan.\n"
            f"- Analizar gastos solo cuando pregunten por su presupuesto.\n\n"
            f"REGLAS ESTRICTAS (NO LAS ROMPAS NUNCA):\n"
            f"{instruccion_enfoque}"
            f"- NUNCA hacer cálculos por tu cuenta. NUNCA inventar números. "
            f"Usá los datos provistos.\n"
            f"- Los totales y balances YA están calculados. Solo leer y narrar.\n"
            f"- Si un dato no aparece explícitamente en los datos, NO lo inventes.\n\n"
            f"SÍMBOLOS MONETARIOS (estricto):\n"
            f"- Reportá cada moneda por separado: $ para UYU, USD para USD.\n"
            f"- NUNCA conviertas ni sumes monedas distintas.\n\n"
            f"TONO: Profesional pero cercano y pedagógico.\n"
            f"{aviso_cuota}\n"
            f"{seccion_rag}{seccion_memoria}{seccion_laboral}{seccion_metas}{seccion_irpf}{seccion_calendario}{seccion_gastos}"
            f"PREGUNTA DEL USUARIO: {pregunta}\n\n"
            f"RESPUESTA DIRECTA:"
        )

        return prompt

    async def _call_ollama(self, prompt: str) -> Any:
        """
        Llama a Ollama (Gemma 2:2b local) sin streaming.
        Retorna el dict completo con 'response' key.
        """
        from ollama import AsyncClient

        _ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        _keep_alive = os.getenv("OLLAMA_KEEP_ALIVE", "24h")
        _threads = int(os.getenv("OLLAMA_NUM_THREADS", "4"))
        client = AsyncClient(host=_ollama_url)

        return await client.generate(
            model="contador-oriental",
            prompt=prompt,
            keep_alive=_keep_alive,
            options={
                "temperature": 0.0,
                "num_predict": 512,
                "num_thread": _threads,
            },
        )

    async def _call_ollama_stream(self, prompt: str):
        """
        Llama a Ollama (Gemma 2:2b local) con streaming.
        Yield tokens a medida que el modelo los genera y registra telemetría de tiempos.
        """
        import time

        from ollama import AsyncClient

        from core.logger import get_logger

        ai_logger = get_logger("AIAdvisor.ollama")
        _ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        _keep_alive = os.getenv("OLLAMA_KEEP_ALIVE", "24h")
        _threads = int(os.getenv("OLLAMA_NUM_THREADS", "4"))
        client = AsyncClient(host=_ollama_url)

        t_start = time.perf_counter()
        t_first_token = None
        token_count = 0

        async for part in await client.generate(
            model="contador-oriental",
            prompt=prompt,
            stream=True,
            keep_alive=_keep_alive,
            options={
                "temperature": 0.0,
                "num_predict": 512,
                "num_thread": _threads,
            },
        ):
            token: str = part.get("response", "")
            if token:
                if t_first_token is None:
                    t_first_token = time.perf_counter()
                    ai_logger.info(
                        "⏱️ Primer token recibido en: %.2fs (Prefill / TTFT)",
                        t_first_token - t_start,
                    )
                token_count += 1
                yield token

            if part.get("done", False):
                t_total = time.perf_counter() - t_start
                p_eval_count = part.get("prompt_eval_count", 0)
                p_eval_dur = part.get("prompt_eval_duration", 0) / 1e9
                eval_count = part.get("eval_count", token_count)
                eval_dur = part.get("eval_duration", 0) / 1e9
                speed = eval_count / eval_dur if eval_dur > 0 else 0

                ai_logger.info(
                    "📊 RESUMEN OLLAMA: Prompt: %d tokens (%.2fs) | "
                    "Generación: %d tokens (%.2fs @ %.1f tok/s) | Tiempo Total: %.2fs",
                    p_eval_count,
                    p_eval_dur,
                    eval_count,
                    eval_dur,
                    speed,
                    t_total,
                )

    async def _call_nvidia(self, prompt: str) -> dict:
        """
        Llama a NVIDIA API (Llama 3 70B cloud) sin streaming.
        Retorna el dict con 'response', 'prompt_tokens', 'completion_tokens'.
        """
        return await self.nvidia_client.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=2048,
        )

    async def _call_nvidia_stream(self, prompt: str):
        """
        Llama a NVIDIA API (Llama 3 70B cloud) con streaming.
        Yield tokens a medida que el modelo los genera.
        """
        async for token in self.nvidia_client.generate_stream(
            prompt=prompt,
            temperature=0.1,
            max_tokens=2048,
        ):
            yield token

    async def consultar_stream(
        self,
        request: AIRequest,
        ctx: AIContext | None = None,
        memoria_vectorial: str = "",
        has_quota: bool = True,
        from_history: bool = False,
        range_months: int = 1,
    ):
        """
        Versión streaming de consultar().
        Yield tokens a medida que el modelo los genera.
        Soporta routing híbrido: Llama 3 (cloud) o Gemma 2 (local).

        Args:
            request: Datos de la consulta.
            ctx: Contexto financiero pre-calculado.
            memoria_vectorial: Contexto RAG de pgvector.
            has_quota: Si la familia tiene cuota de Llama 3 disponible.
            from_history: Si la pregunta viene del botón de Historial.
            range_months: Cantidad de meses que abarca la consulta.

        Yields:
            str — fragmento de texto generado por el modelo.

        Raises:
            AppError — si hay error de conexión o de modelo.
        """
        from core.logger import get_logger

        ai_logger = get_logger("AIAdvisor.stream")

        # 1. Seleccionar contexto legal
        contexto, _ = self._seleccionar_contexto(request.pregunta)

        # 2. Formatear gastos
        gastos_formateados = ""
        if request.incluir_gastos_recientes and ctx:
            gastos_formateados = self._formatear_datos_financieros(
                ctx, pregunta=request.pregunta
            )
            comparativa_str = self._formatear_comparativa(
                ctx, pregunta=request.pregunta
            )
            if comparativa_str:
                gastos_formateados += comparativa_str

        # 3. Routing: decidir qué modelo usar
        modelo = self.router.route(
            pregunta=request.pregunta,
            ctx=ctx,
            has_quota=has_quota,
            from_history=from_history,
            range_months=range_months,
        )
        cuota_agotada = modelo == "gemma2" and not has_quota

        # 4. Construir prompt con flags de modelo
        prompt = self._construir_prompt(
            request.pregunta,
            contexto,
            gastos_formateados,
            memoria_vectorial,
            cuota_agotada=cuota_agotada,
            modelo=modelo,
            ctx=ctx,
        )

        ai_logger.info("=" * 80)
        ai_logger.info("📊 CONTEXTO ENVIADO AL MODELO (STREAM):")
        ai_logger.info("  - Modelo: %s", modelo.upper())
        ai_logger.info("  - Pregunta: %s", request.pregunta)
        ai_logger.info("  - Incluir gastos: %s", request.incluir_gastos_recientes)
        ai_logger.info("  - Transacciones: %d", ctx.total_gastos_count if ctx else 0)
        ai_logger.info("  - Contexto legal: %s", "Sí" if contexto else "No")
        ai_logger.info("  - Cuota agotada: %s", cuota_agotada)
        ai_logger.info("  - Prompt completo (%d chars):", len(prompt))
        ai_logger.info("-" * 80)
        ai_logger.info(prompt)
        ai_logger.info("=" * 80)
        ai_logger.info("🔴 STREAM iniciado (%s chars prompt)", len(prompt))

        # 5. Llamar al modelo seleccionado
        try:
            if modelo == "llama3":
                ai_logger.info("🤖 streaming con Llama 3 70B (NVIDIA)")
                async for token in self._call_nvidia_stream(prompt):
                    yield token
            else:
                ai_logger.info("🤖 streaming con Gemma 2:2b (Ollama)")
                if cuota_agotada:
                    yield "⚠️ Respuesta con precisión reducida. "
                    yield "La cuota diaria de consultas avanzadas está agotada. "
                    yield "Se renueva a medianoche.\n\n"
                async for token in self._call_ollama_stream(prompt):
                    yield token
        except (ConnectionError, TimeoutError, RuntimeError, Exception) as e:
            ai_logger.error("❌ Error en stream: %s", e)
            # Fallback a Ollama si NVIDIA falla
            if modelo == "llama3":
                ai_logger.info("🔄 Fallback a Gemma 2 por error en NVIDIA")
                async for token in self._call_ollama_stream(prompt):
                    yield token
            else:
                raise

        ai_logger.info("✅ STREAM completado (%s)", modelo)

    async def llamada_directa(self, prompt: str) -> str:
        """
        Llama a Gemma 2:2b con un prompt directo, sin contexto financiero.
        Usado por TicketService para parsear texto crudo de tickets OCR.
        Siempre usa el modelo local (no consume cuota cloud).
        Retorna el texto de la respuesta o string vacío si falla.
        """
        try:
            response = await self._call_ollama(prompt)
            return response.get("response", "").strip()
        except ConnectionError as e:
            logger.error(
                "[AI] llamada_directa — Ollama no responde (ConnectionError): %s", e
            )
            return ""
        except TimeoutError as e:
            logger.error("[AI] llamada_directa — Timeout en Ollama: %s", e)
            return ""
        except Exception as e:
            logger.exception("[AI] llamada_directa — Error inesperado: %s", e)
            return ""

    async def consultar(
        self,
        request: AIRequest,
        ctx: AIContext | None = None,
        memoria_vectorial: str = "",
        has_quota: bool = True,
        from_history: bool = False,
        range_months: int = 1,
    ) -> Result[AIResponse, AppError]:
        """
        Consulta al Contador Oriental con routing híbrido.

        El ModelRouter decide si usar Gemma 2:2b (local) o Llama 3 70B (cloud).
        Si la cuota está agotada, cae a Gemma 2 con aviso de precisión reducida.
        Si NVIDIA falla, cae automáticamente a Gemma 2 (fallback).

        Args:
            request: Datos de la consulta.
            ctx: Contexto financiero pre-calculado por Python (opcional).
            memoria_vectorial: Contexto RAG de pgvector (opcional).
            has_quota: Si la familia tiene cuota de Llama 3 disponible.
            from_history: Si la pregunta viene del botón de Historial.
            range_months: Cantidad de meses que abarca la consulta.

        Returns:
            Result con la respuesta o error.
        """
        from core.logger import get_logger

        ai_logger = get_logger("AIAdvisor")

        try:
            # 1. Seleccionar contexto legal
            contexto, archivo = self._seleccionar_contexto(request.pregunta)

            # 2. Formatear gastos si están disponibles
            gastos_formateados = ""

            if request.incluir_gastos_recientes and ctx:
                gastos_formateados = self._formatear_datos_financieros(
                    ctx, pregunta=request.pregunta
                )
                comparativa_str = self._formatear_comparativa(
                    ctx, pregunta=request.pregunta
                )
                if comparativa_str:
                    gastos_formateados += comparativa_str

            # 3. Routing: decidir qué modelo usar
            modelo = self.router.route(
                pregunta=request.pregunta,
                ctx=ctx,
                has_quota=has_quota,
                from_history=from_history,
                range_months=range_months,
            )
            cuota_agotada = modelo == "gemma2" and not has_quota

            # 4. Construir prompt con flags de modelo
            prompt = self._construir_prompt(
                request.pregunta,
                contexto,
                gastos_formateados,
                memoria_vectorial,
                cuota_agotada=cuota_agotada,
                modelo=modelo,
                ctx=ctx,
            )

            # Log del contexto para debugging
            ai_logger.info("=" * 80)
            ai_logger.info("📊 CONTEXTO ENVIADO AL MODELO:")
            ai_logger.info("  - Modelo: %s", modelo.upper())
            ai_logger.info("  - Pregunta: %s", request.pregunta)
            ai_logger.info("  - Incluir gastos: %s", request.incluir_gastos_recientes)
            ai_logger.info(
                "  - Transacciones: %d", ctx.total_gastos_count if ctx else 0
            )
            ai_logger.info("  - Contexto legal: %s", "Sí" if contexto else "No")
            ai_logger.info("  - Cuota agotada: %s", cuota_agotada)
            ai_logger.info("  - Prompt completo (%d chars):", len(prompt))
            ai_logger.info("-" * 80)
            ai_logger.info(prompt)
            ai_logger.info("=" * 80)

            # 5. Llamar al modelo seleccionado
            respuesta_texto = ""

            if modelo == "llama3":
                respuesta_texto = await self._consultar_llama3(prompt, ai_logger)
            else:
                respuesta_texto = await self._consultar_gemma2(
                    prompt, ai_logger, cuota_agotada
                )

            # 6. Construir respuesta
            ai_response = AIResponse(
                respuesta=respuesta_texto,
                archivo_usado=archivo,
                gastos_incluidos=ctx.total_gastos_count if ctx else 0,
            )

            return Ok(ai_response)

        except Exception as e:
            return Err(AppError(message=f"Error en el Contador Oriental: {str(e)}"))

    async def _consultar_llama3(self, prompt: str, ai_logger) -> str:
        """
        Llama a Llama 3 70B via NVIDIA API.
        Si falla, hace fallback automático a Gemma 2:2b.
        """
        ai_logger.info("🤖 Generando respuesta con Llama 3 70B (NVIDIA)")
        try:
            result = await self._call_nvidia(prompt)
            respuesta = result["response"].strip()
            ai_logger.info(
                "✅ Respuesta Llama 3: %d chars (tokens: %d+%d)",
                len(respuesta),
                result.get("prompt_tokens", 0),
                result.get("completion_tokens", 0),
            )
            return respuesta
        except (ConnectionError, TimeoutError, RuntimeError) as e:
            ai_logger.warning("⚠️ NVIDIAClient falló: %s. Fallback a Gemma 2", e)
            return await self._consultar_gemma2(prompt, ai_logger, cuota_agotada=False)
        except Exception as e:
            ai_logger.warning("⚠️ Error inesperado en NVIDIA: %s. Fallback a Gemma 2", e)
            return await self._consultar_gemma2(prompt, ai_logger, cuota_agotada=False)

    async def _consultar_gemma2(
        self, prompt: str, ai_logger, cuota_agotada: bool = False
    ) -> str:
        """
        Llama a Gemma 2:2b via Ollama local.
        Si cuota_agotada, prepone el aviso de precisión reducida.
        """
        ai_logger.info("🤖 Generando respuesta con Gemma 2:2b (Ollama)")
        try:
            response = await self._call_ollama(prompt)
            respuesta_texto: str = response.get("response", "").strip()
        except ConnectionError as e:
            ai_logger.error("❌ Error de conexión con Ollama: %s", str(e))
            raise ConnectionError(
                "El Contador Oriental no puede conectarse al servidor "
                "de IA. Verificar que Ollama esté corriendo en el host."
            ) from e
        except Exception as e:
            ai_logger.error(
                "❌ Error inesperado en Ollama: %s:%s", type(e).__name__, str(e)
            )
            raise RuntimeError(
                f"Error al consultar al Contador Oriental: {str(e)}"
            ) from e

        if cuota_agotada:
            aviso = (
                "⚠️ Respuesta con precisión reducida. "
                "La cuota diaria de consultas avanzadas está agotada. "
                "Se renueva a medianoche.\n\n"
            )
            respuesta_texto = aviso + respuesta_texto

        ai_logger.info("✅ Respuesta Gemma 2: %d chars", len(respuesta_texto))
        return respuesta_texto
