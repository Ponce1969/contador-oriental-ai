"""
Servicio de asesoría con IA - Contador Oriental (arquitectura híbrida)

Orquestador que decide entre Gemma 2:2b (local) y Llama 3 70B (cloud NVIDIA)
basado en la complejidad de la pregunta y la cuota disponible.
"""

from __future__ import annotations

import logging
import os
from decimal import Decimal

from result import Err, Ok, Result

from models.ai_model import AIContext, AIRequest, AIResponse
from models.errors import AppError
from services.ai.model_router import ModelRouter
from services.infrastructure.formatters import format_pesos
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
            score = sum(
                config["peso"]
                for palabra in config["keywords"]
                if palabra in pregunta_lower
            )
            scores[archivo] = score

        archivo_seleccionado = max(scores, key=scores.get)

        if scores[archivo_seleccionado] > 0:
            ruta = os.path.join(self.knowledge_path, archivo_seleccionado)
            try:
                with open(ruta, encoding="utf-8") as f:
                    return f.read(), archivo_seleccionado
            except FileNotFoundError:
                return "", None

        return "", None

    def _formatear_datos_financieros(self, ctx: AIContext) -> str:
        """
        Prepara el bloque de datos financieros para el Prompt de Gemma 2:2b.
        Todos los valores ya vienen calculados en ctx; Gemma solo narra.

        Args:
            ctx: Contexto financiero pre-calculado por Python

        Returns:
            String formateado con el resumen financiero
        """
        balance_mes: Decimal = ctx.ingresos_total - ctx.total_gastos_mes

        lineas: list[str] = [
            "### ESTADO DE LA HACIENDA FAMILIAR ###",
            f"- Miembros en el hogar: {ctx.miembros_count}",
            f"- Ingresos totales {ctx.periodo_label}:"
            f" {format_pesos(ctx.ingresos_total)}",
            f"- TOTAL gastos {ctx.periodo_label} (todas las categorías):"
            f" {format_pesos(ctx.total_gastos_mes)}",
            f"- BALANCE {ctx.periodo_label} (Ingresos - Gastos totales): "
            f"{format_pesos(balance_mes)}",
        ]

        if ctx.cotizacion_dolar:
            # Redondear a 2 decimales para que no muestre 40.0100
            cotizacion_str = f"{ctx.cotizacion_dolar:.2f}"
            lineas.append(
                f"- Cotización del dólar hoy: 1 USD = $ {cotizacion_str}"
            )

        if ctx.resumen_metodos_pago:
            metodos_label = (
                f"- Métodos de pago usados {ctx.periodo_label}:"
                f" {ctx.resumen_metodos_pago}"
            )
            lineas.append(metodos_label)

        if ctx.subtotal_descripcion and ctx.terminos_buscados:
            lineas.append(
                f"- *** RESPUESTA DIRECTA: '{ctx.terminos_buscados}'"
                f" {ctx.periodo_label} = {format_pesos(ctx.subtotal_descripcion)} ***"
            )

        # Proyeccion de cuotas futuras
        if ctx.proyeccion_cuotas:
            lineas.append("")
            lineas.append("PROYECCION DE CUOTAS FUTURAS:")
            for mes, total in ctx.proyeccion_cuotas.items():
                lineas.append(f"  {mes}: {format_pesos(total)}")
            lineas.append(
                "Usa esta proyeccion para advertir si un nuevo gasto "
                "comprometeria meses futuros."
            )

        # ── Empalme: cierre del mes anterior ──────────────────────────
        if ctx.empalme_mes_label:
            balance_empalme = ctx.empalme_ingresos_total - ctx.empalme_total_gastos
            lineas.append("")
            lineas.append(
                f"### CIERRE DEL MES ANTERIOR ({ctx.empalme_mes_label}) ###"
            )
            lineas.append(
                f"- Ingresos: {format_pesos(ctx.empalme_ingresos_total)}"
            )
            lineas.append(
                f"- Total gastos: {format_pesos(ctx.empalme_total_gastos)}"
            )
            lineas.append(
                f"- Balance: {format_pesos(balance_empalme)}"
            )

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
                        f" → {format_pesos(total_cat)}"
                        f" ({cant_cat} transacciones):"
                    )
                    for descripcion, datos in items.items():
                        monto = datos["total"]
                        cantidad = datos["cantidad"]
                        metodos = datos.get("metodos", {})
                        metodo_str = ", ".join(
                            f"{m}({c}x)" for m, c in metodos.items()
                        )
                        if cantidad > 1:
                            lineas.append(
                                f"    - {descripcion}: {format_pesos(monto)}"
                                f" ({cantidad}x, {metodo_str})"
                            )
                        else:
                            lineas.append(
                                f"    - {descripcion}: {format_pesos(monto)}"
                                f" ({metodo_str})"
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

        total_filtrado = Decimal("0")

        if not ctx.resumen_gastos:
            lineas.append("- No hay gastos registrados en este contexto.")
        else:
            for categoria, items in ctx.resumen_gastos.items():
                total_categoria = sum(
                    (Decimal(str(d["total"])) for d in items.values()),
                    Decimal("0"),
                )
                cant_categoria = sum(d["cantidad"] for d in items.values())
                total_filtrado += total_categoria

                lineas.append(
                    f"\n📂 {categoria}"
                    f" → SUBTOTAL: {format_pesos(total_categoria)}"
                    f" ({cant_categoria} transacciones):"
                )
                for descripcion, datos in items.items():
                    monto = datos["total"]
                    cantidad = datos["cantidad"]
                    metodos = datos.get("metodos", {})
                    metodo_str = ", ".join(f"{m}({c}x)" for m, c in metodos.items())
                    if cantidad > 1:
                        lineas.append(
                            f"  - {descripcion}: {format_pesos(monto)} total"
                            f" ({cantidad} transacciones separadas, {metodo_str})"
                        )
                    else:
                        lineas.append(
                            f"  - {descripcion}: {format_pesos(monto)} ({metodo_str})"
                        )

        lineas.append("")
        lineas.append(
            f"SUBTOTAL CONSULTADO: {format_pesos(total_filtrado)}"
            f" ({ctx.total_gastos_count} transacciones)"
        )

        return "\n".join(lineas)

    def _formatear_comparativa(self, ctx: AIContext) -> str:
        """
        Convierte CategoryMetric en hechos contables narrativos para el prompt.
        Python pre-calcula todo; Gemma solo lee y narra.
        """
        if not ctx.comparativa_meses:
            return ""

        lineas: list[str] = [
            "",
            "### COMPARATIVA VS MES ANTERIOR ###",
        ]

        for m in ctx.comparativa_meses:
            vt = m.variacion_total_pct
            vtk = m.variacion_ticket_pct
            diag = m.diagnostico

            if vt is None:
                lineas.append(
                    f"- {m.categoria}: {format_pesos(m.total_actual)} este mes"
                    f" (sin datos del mes anterior para comparar)."
                )
                continue

            signo_t = "+" if vt >= 0 else ""
            signo_tk = "+" if (vtk or 0) >= 0 else ""
            lineas.append(
                f"- {m.categoria}:"
                f" gasto total {signo_t}{vt:.1f}%"
                f" ({format_pesos(m.total_anterior)} ->"
                f" {format_pesos(m.total_actual)}),"
                f" ticket promedio {signo_tk}{vtk:.1f}%"
                f" ({format_pesos(m.ticket_anterior)} ->"
                f" {format_pesos(m.ticket_actual)})."
                f" {diag}"
            )

        return "\n".join(lineas)

    def _construir_prompt(
        self,
        pregunta: str,
        contexto_legal: str,
        gastos_formateados: str,
        memoria_vectorial: str = "",
        cuota_agotada: bool = False,
        modelo: str = "gemma2",
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
        """
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

        seccion_gastos = f"{gastos_formateados}\n" if gastos_formateados else ""

        datos_reales = bool(seccion_gastos or seccion_memoria)
        prioridad = (
            "- PRIORIDAD: Los datos reales del usuario (abajo) mandan sobre cualquier"
            " normativa general. Respondé basándote en esos datos primero.\n"
            if datos_reales
            else ""
        )

        # Aviso cuando la cuota de Llama 3 está agotada y cae a Gemma 2
        aviso_cuota = ""
        if cuota_agotada:
            aviso_cuota = (
                "\nADVERTENCIA: Estás respondiendo con información limitada "
                "(modelo local). Sé conservador y agregá que la respuesta "
                "puede ser menos precisa.\n"
            )

        # Límite de líneas depende del modelo
        max_lineas = "6 líneas" if modelo == "llama3" else "4 líneas"

        prompt = f"""Sos el Contador Oriental, un contador público uruguayo.

TU ROL:
- Leer los datos que te da el sistema y narrarlos en español rioplatense.
- Dar consejos contables basados en la normativa uruguaya si te la preguntan.

REGLAS ESTRICTAS (NO LAS ROMPAS NUNCA):
- NUNCA inventar números. NUNCA hacer cálculos. NUNCA dividir ni derivar valores.
- NUNCA decir "la mitad" o "un tercio" o porcentajes inventados. Solo usá los números exactos que aparecen en los datos.
- Si una cuota es $650 y otra es $240, NO digas "la mitad". Decí "$650 y $240 respectivamente".
- Los totales, balances y sumas YA están calculados por el sistema. Solo leer y narrar.
- Si un dato no aparece explícitamente en los datos, NO lo menciones ni lo calcules.
- Si hay pocos gastos este mes (principio de mes), usá la sección "CIERRE DEL MES ANTERIOR" para dar contexto del cierre del mes pasado.
- La sección "CIERRE DEL MES ANTERIOR" es REFERENCIA: NO la mezcles con los datos del mes actual.

SÍMBOLOS MONETARIOS (estricto):
- Usá $ para Pesos Uruguayos (moneda principal del usuario). Ejemplo: $ 650, $ 890, $ 170.000
- Usá USD para Dólares. NUNCA uses U$S ni $U.
- El total mensual SIEMPRE en $ (pesos).
- Usá USD solo para contextualizar compras grandes o deudas en esa moneda.

TONO: Profesional pero de confianza. Evitá tecnicismos. Si algo está mal, decilo directo.
{aviso_cuota}{prioridad}- Máximo {max_lineas} de respuesta.

{seccion_rag}{seccion_memoria}{seccion_gastos}PREGUNTA: {pregunta}

RESPUESTA:"""

        return prompt

    async def _call_ollama(self, prompt: str) -> dict:
        """
        Llama a Ollama (Gemma 2:2b local) sin streaming.
        Retorna el dict completo con 'response' key.
        """
        from ollama import AsyncClient

        _ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        client = AsyncClient(host=_ollama_url)

        return await client.generate(
            model="contador-oriental",
            prompt=prompt,
            options={"temperature": 0.0, "num_predict": 512},
        )

    async def _call_ollama_stream(self, prompt: str):
        """
        Llama a Ollama (Gemma 2:2b local) con streaming.
        Yield tokens a medida que el modelo los genera.
        """
        from ollama import AsyncClient

        _ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        client = AsyncClient(host=_ollama_url)

        async for part in await client.generate(
            model="contador-oriental",
            prompt=prompt,
            stream=True,
            options={"temperature": 0.0, "num_predict": 512},
        ):
            token: str = part.get("response", "")
            if token:
                yield token

    async def _call_nvidia(self, prompt: str) -> dict:
        """
        Llama a NVIDIA API (Llama 3 70B cloud) sin streaming.
        Retorna el dict con 'response', 'prompt_tokens', 'completion_tokens'.
        """
        return await self.nvidia_client.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=1024,
        )

    async def _call_nvidia_stream(self, prompt: str):
        """
        Llama a NVIDIA API (Llama 3 70B cloud) con streaming.
        Yield tokens a medida que el modelo los genera.
        """
        async for token in self.nvidia_client.generate_stream(
            prompt=prompt,
            temperature=0.1,
            max_tokens=1024,
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
            gastos_formateados = self._formatear_datos_financieros(ctx)
            comparativa_str = self._formatear_comparativa(ctx)
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
        except (ConnectionError, TimeoutError, RuntimeError):
            raise
        except Exception as e:
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
                gastos_formateados = self._formatear_datos_financieros(ctx)
                comparativa_str = self._formatear_comparativa(ctx)
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
            )

            # Log del contexto para debugging
            ai_logger.info("=" * 80)
            ai_logger.info("📊 CONTEXTO ENVIADO AL MODELO:")
            ai_logger.info("  - Modelo: %s", modelo.upper())
            ai_logger.info("  - Pregunta: %s", request.pregunta)
            ai_logger.info(
                "  - Incluir gastos: %s", request.incluir_gastos_recientes
            )
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
                respuesta_texto = await self._consultar_llama3(
                    prompt, ai_logger
                )
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

    async def _consultar_llama3(
        self, prompt: str, ai_logger
    ) -> str:
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
            ai_logger.warning(
                "⚠️ Error inesperado en NVIDIA: %s. Fallback a Gemma 2", e
            )
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
            )
        except Exception as e:
            ai_logger.error("❌ Error inesperado en Ollama: %s:%s", type(e).__name__, str(e))
            raise RuntimeError(
                f"Error al consultar al Contador Oriental: {str(e)}"
            )

        if cuota_agotada:
            aviso = (
                "⚠️ Respuesta con precisión reducida. "
                "La cuota diaria de consultas avanzadas está agotada. "
                "Se renueva a medianoche.\n\n"
            )
            respuesta_texto = aviso + respuesta_texto

        ai_logger.info("✅ Respuesta Gemma 2: %d chars", len(respuesta_texto))
        return respuesta_texto
