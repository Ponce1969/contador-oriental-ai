"""
Servicio de asesoría con IA - Contador Oriental (gemma2:2b)
"""

from __future__ import annotations

import logging
import os

from result import Err, Ok, Result

from models.ai_model import AIContext, AIRequest, AIResponse
from models.errors import AppError

logger = logging.getLogger(__name__)


class AIAdvisorService:
    """Servicio para consultar al Contador Oriental"""
    
    def __init__(self, knowledge_path: str = "./knowledge"):
        self.knowledge_path = knowledge_path
        self.mapa_conocimiento = {
            "irpf_familia_uy.md": {
                "keywords": ["irpf", "impuesto", "hijo", "alquiler", "deduccion", 
                           "dgi", "devolucion", "hipoteca"],
                "peso": 2
            },
            "inclusion_financiera_uy.md": {
                "keywords": ["iva", "tarjeta", "debito", "credito", "descuento",
                           "inclusion financiera", "beneficio tarjeta"],
                "peso": 1
            },
            "ahorro_ui_uy.md": {
                "keywords": ["ahorro", "ui", "unidad indexada", "inflacion", 
                           "plazo fijo", "invertir", "banco"],
                "peso": 1
            }
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
                config["peso"] for palabra in config["keywords"]
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
        balance_mes: float = ctx.ingresos_total - ctx.total_gastos_mes
        
        lineas: list[str] = [
            "### ESTADO DE LA HACIENDA FAMILIAR ###",
            f"- Miembros en el hogar: {ctx.miembros_count}",
            f"- Ingresos totales del mes: ${ctx.ingresos_total:,.0f}",
            f"- TOTAL gastos del mes (todas las categorías):"
            f" ${ctx.total_gastos_mes:,.0f}",
            f"- BALANCE DEL MES (Ingresos - Gastos totales): ${balance_mes:,.0f}",
        ]

        if ctx.resumen_metodos_pago:
            lineas.append(
                f"- Métodos de pago usados este mes: {ctx.resumen_metodos_pago}"
            )

        lineas += [
            "",
            "DETALLE DE GASTOS CONSULTADOS:"
        ]
        
        total_filtrado = 0.0
        
        if not ctx.resumen_gastos:
            lineas.append("- No hay gastos registrados en este contexto.")
        else:
            for categoria, items in ctx.resumen_gastos.items():
                total_categoria = sum(d["total"] for d in items.values())
                cant_categoria = sum(d["cantidad"] for d in items.values())
                total_filtrado += total_categoria
                
                lineas.append(
                    f"\n📂 {categoria}"
                    f" → TOTAL: ${total_categoria:,.0f} ({cant_categoria} compras):"
                )
                for descripcion, datos in items.items():
                    monto = datos["total"]
                    cantidad = datos["cantidad"]
                    metodos = datos.get("metodos", {})
                    metodo_str = ", ".join(
                        f"{m}({c}x)" for m, c in metodos.items()
                    )
                    lineas.append(
                        f"  • {descripcion}: ${monto:,.0f}"
                        f" ({cantidad} veces, {metodo_str})"
                    )
        
        lineas.append("")
        lineas.append(
            f"SUBTOTAL CONSULTADO: ${total_filtrado:,.0f}"
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
                    f"- {m.categoria}: ${m.total_actual:,.0f} este mes"
                    f" (sin datos del mes anterior para comparar)."
                )
                continue

            signo_t = "+" if vt >= 0 else ""
            signo_tk = "+" if (vtk or 0) >= 0 else ""
            lineas.append(
                f"- {m.categoria}:"
                f" gasto total {signo_t}{vt:.1f}%"
                f" (${m.total_anterior:,.0f} → ${m.total_actual:,.0f}),"
                f" ticket promedio {signo_tk}{vtk:.1f}%"
                f" (${m.ticket_anterior:,.0f} → ${m.ticket_actual:,.0f})."
                f" {diag}"
            )

        return "\n".join(lineas)

    def _construir_prompt(
        self,
        pregunta: str,
        contexto_legal: str,
        gastos_formateados: str
    ) -> str:
        """
        Construye el prompt optimizado para gemma2:2b
        CRÍTICO: Mantener conciso para evitar que el modelo se pierda
        """
        seccion_rag = (
            f"NORMATIVA URUGUAYA RELEVANTE:\n{contexto_legal}\n"
            if contexto_legal else ""
        )
        
        seccion_gastos = (
            f"{gastos_formateados}\n"
            if gastos_formateados else ""
        )

        datos_reales = bool(seccion_gastos)
        prioridad = (
            "- PRIORIDAD: Los datos reales del usuario (abajo) mandan sobre cualquier"
            " normativa general. Respondé basándote en esos datos primero.\n"
            if datos_reales else ""
        )

        prompt = f"""Sos el Contador Oriental, un contador público uruguayo.

TU ROL:
- Leer los datos que te da el sistema y narrarlos en español rioplatense.
- Dar consejos contables basados en la normativa uruguaya si te la preguntan.
- NUNCA inventar números. NUNCA hacer cálculos. NUNCA dividir ni derivar valores.
- Los totales, balances y sumas YA están calculados por el sistema. Solo leer y narrar.
- Si un dato no aparece explícitamente en los datos, NO lo menciones ni lo calcules.
{prioridad}- Máximo 4 líneas de respuesta.

{seccion_rag}{seccion_gastos}PREGUNTA: {pregunta}

RESPUESTA:"""

        return prompt
    
    async def consultar_stream(
        self,
        request: AIRequest,
        ctx: AIContext | None = None,
    ):
        """
        Versión streaming de consultar().
        Yield tokens a medida que Gemma los genera.
        El caller acumula y actualiza la UI token a token.

        Yields:
            str — fragmento de texto generado por el modelo.

        Raises:
            AppError — si hay error de conexión o de modelo.
        """
        from core.logger import get_logger
        ai_logger = get_logger("AIAdvisor.stream")

        contexto, _ = self._seleccionar_contexto(request.pregunta)

        gastos_formateados = ""
        if request.incluir_gastos_recientes and ctx and ctx.resumen_gastos:
            gastos_formateados = self._formatear_datos_financieros(ctx)
            comparativa_str = self._formatear_comparativa(ctx)
            if comparativa_str:
                gastos_formateados += comparativa_str

        prompt = self._construir_prompt(request.pregunta, contexto, gastos_formateados)

        ai_logger.info("🔴 STREAM iniciado (%s chars prompt)", len(prompt))

        try:
            from ollama import AsyncClient
        except ImportError:
            raise AppError(message="Dependencia 'ollama' no encontrada.")

        client = AsyncClient(host="http://host.docker.internal:11434")
        async for part in await client.generate(
            model="contador-oriental",
            prompt=prompt,
            stream=True,
        ):
            token: str = part.get("response", "")
            if token:
                yield token

        ai_logger.info("✅ STREAM completado")

    async def consultar(
        self,
        request: AIRequest,
        ctx: AIContext | None = None
    ) -> Result[AIResponse, AppError]:
        """
        Consulta al Contador Oriental (asíncrono)
        
        Args:
            request: Datos de la consulta
            ctx: Contexto financiero pre-calculado por Python (opcional)
            
        Returns:
            Result con la respuesta o error
        """
        # Usar nombre distinto para evitar conflicto con logger global
        from core.logger import get_logger
        ai_logger = get_logger("AIAdvisor")
        
        try:
            # 1. Seleccionar contexto legal
            contexto, archivo = self._seleccionar_contexto(request.pregunta)
            
            # 2. Formatear gastos si están disponibles
            gastos_formateados = ""
            
            if request.incluir_gastos_recientes and ctx and ctx.resumen_gastos:
                gastos_formateados = self._formatear_datos_financieros(ctx)
                comparativa_str = self._formatear_comparativa(ctx)
                if comparativa_str:
                    gastos_formateados += comparativa_str

            # 3. Construir prompt
            prompt = self._construir_prompt(
                request.pregunta,
                contexto,
                gastos_formateados,
            )
            
            # Log del contexto para debugging
            ai_logger.info("=" * 80)
            ai_logger.info("📊 CONTEXTO ENVIADO AL MODELO:")
            ai_logger.info(f"  - Pregunta: {request.pregunta}")
            ai_logger.info(f"  - Incluir gastos: {request.incluir_gastos_recientes}")
            ai_logger.info(f"  - Transacciones: {ctx.total_gastos_count if ctx else 0}")
            ai_logger.info(f"  - Contexto legal: {'Sí' if contexto else 'No'}")
            ai_logger.info(f"  - Prompt completo ({len(prompt)} chars):")
            ai_logger.info("-" * 80)
            ai_logger.info(prompt)
            ai_logger.info("=" * 80)
            
            # 4. Llamar a Ollama (gemma2:2b) con cliente asíncrono
            try:
                from ollama import AsyncClient
            except ImportError:
                ai_logger.error(
                    "❌ Librería 'ollama' no encontrada en el entorno. "
                    "Verificar que esté en requirements.txt"
                )
                return Err(AppError(
                    message="El Contador Oriental no puede funcionar: "
                    "dependencia de IA faltante (ollama)."
                ))
            
            try:
                # Cliente asíncrono: no bloquea el event loop mientras Gemma genera
                ai_logger.info("🔌 Conectando con Ollama en host.docker.internal:11434")
                client = AsyncClient(host='http://host.docker.internal:11434')
                
                ai_logger.info("🤖 Generando respuesta con contador-oriental (async)")
                response = await client.generate(
                    model="contador-oriental",
                    prompt=prompt,
                )
                
                respuesta_texto: str = response['response'].strip()
                ai_logger.info(f"✅ Respuesta generada: {len(respuesta_texto)} chars")
                
            except ConnectionError as e:
                ai_logger.error(f"❌ Error de conexión con Ollama: {str(e)}")
                return Err(AppError(
                    message="El Contador Oriental no puede conectarse al servidor "
                    "de IA. Verificar que Ollama esté corriendo en el host."
                ))
            except Exception as e:
                ai_logger.error(
                    f"❌ Error inesperado en Ollama: {type(e).__name__}: {str(e)}"
                )
                return Err(AppError(
                    message=f"Error al consultar al Contador Oriental: {str(e)}"
                ))
            
            # 5. Construir respuesta
            ai_response = AIResponse(
                respuesta=respuesta_texto,
                archivo_usado=archivo,
                gastos_incluidos=ctx.total_gastos_count if ctx else 0
            )
            
            return Ok(ai_response)
            
        except Exception as e:
            return Err(AppError(
                message=f"Error en el Contador Oriental: {str(e)}"
            ))
