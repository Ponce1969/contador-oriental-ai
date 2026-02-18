"""
Servicio de asesoría con IA - Contador Oriental (gemma2:2b)
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from result import Err, Ok, Result

from models.ai_model import AIRequest, AIResponse
from models.errors import AppError

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from models.expense_model import Expense


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
                           "restaurante", "compra", "super"],
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
                with open(ruta, "r", encoding="utf-8") as f:
                    return f.read(), archivo_seleccionado
            except FileNotFoundError:
                return "", None
        
        return "", None
    
    def _formatear_datos_financieros(
        self,
        gastos: list[Expense],
        ingresos_total: float,
        miembros: int
    ) -> str:
        """
        Prepara el bloque de datos financieros para el Prompt de Gemma 2:2b.
        Muestra TODOS los gastos que el controlador filtró, sin límites artificiales.
        
        Args:
            gastos: Lista de gastos filtrados por el controlador
            ingresos_total: Total de ingresos del mes
            miembros: Cantidad de miembros en la familia
            
        Returns:
            String formateado con todos los datos financieros
        """
        lineas: list[str] = [
            "### ESTADO DE LA HACIENDA FAMILIAR ###",
            f"- Miembros en el hogar: {miembros}",
            f"- Ingresos totales del mes: ${ingresos_total:,.0f}",
            f"- Gastos registrados en este contexto: {len(gastos)}",
            "",
            "DETALLE DE MOVIMIENTOS:"
        ]
        
        # Mostrar TODOS los gastos que el controlador filtró
        if not gastos:
            lineas.append("- No hay gastos específicos para mostrar en esta categoría.")
        else:
            for gasto in gastos:
                # Formato claro: Fecha | Categoría | Monto | Descripción
                fecha_str: str = gasto.fecha.strftime('%d/%m')
                categoria_str: str = gasto.categoria.value
                monto_str: str = f"${gasto.monto:,.0f}"
                lineas.append(
                    f"• {fecha_str}: {categoria_str} - {monto_str} ({gasto.descripcion})"
                )
        
        # Cálculo del balance para que la IA no tenga que adivinar
        total_gastos: float = sum(g.monto for g in gastos)
        balance: float = ingresos_total - total_gastos
        
        lineas.append("")
        lineas.append(f"TOTAL GASTOS EN ESTA CONSULTA: ${total_gastos:,.0f}")
        lineas.append(f"BALANCE (Ingresos - Gastos): ${balance:,.0f}")
        
        if miembros > 0:
            gasto_per_capita: float = total_gastos / miembros
            lineas.append(f"GASTO PER CÁPITA: ${gasto_per_capita:,.0f}")
        
        logger.info(
            f"Contexto formateado: {len(gastos)} gastos, "
            f"Total: ${total_gastos:,.0f}, Balance: ${balance:,.0f}"
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
        prompt = f"""Sos el Contador Oriental, experto en Uruguay.

REGLAS:
1. Respuesta breve (máximo 4 líneas)
2. Usar datos del CONTEXTO si están disponibles
3. Hablar en español rioplatense
4. Usar pesos uruguayos ($)

{contexto_legal if contexto_legal else ""}

{gastos_formateados}

PREGUNTA: {pregunta}

RESPUESTA:"""
        
        return prompt
    
    def consultar(
        self,
        request: AIRequest,
        gastos: list[Expense] | None = None,
        ingresos_total: float = 0.0,
        miembros_count: int = 0
    ) -> Result[AIResponse, AppError]:
        """
        Consulta al Contador Oriental
        
        Args:
            request: Datos de la consulta
            gastos: Lista de gastos recientes (opcional)
            
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
            cantidad_gastos = 0
            
            if request.incluir_gastos_recientes and gastos:
                gastos_formateados = self._formatear_datos_financieros(
                    gastos, ingresos_total, miembros_count
                )
                cantidad_gastos = len(gastos)
            
            # 3. Construir prompt
            prompt = self._construir_prompt(
                request.pregunta,
                contexto,
                gastos_formateados
            )
            
            # Log del contexto para debugging
            ai_logger.info("=" * 80)
            ai_logger.info(f"📊 CONTEXTO ENVIADO AL MODELO:")
            ai_logger.info(f"  - Pregunta: {request.pregunta}")
            ai_logger.info(f"  - Incluir gastos: {request.incluir_gastos_recientes}")
            ai_logger.info(f"  - Gastos disponibles: {cantidad_gastos}")
            ai_logger.info(f"  - Contexto legal: {'Sí' if contexto else 'No'}")
            ai_logger.info(f"  - Prompt completo ({len(prompt)} chars):")
            ai_logger.info("-" * 80)
            ai_logger.info(prompt)
            ai_logger.info("=" * 80)
            
            # 4. Llamar a Ollama (gemma2:2b) con manejo robusto de errores
            try:
                import ollama
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
                # Configurar cliente para conectar desde Docker a host
                ai_logger.info("🔌 Conectando con Ollama en host.docker.internal:11434")
                client = ollama.Client(host='http://host.docker.internal:11434')
                
                ai_logger.info("🤖 Generando respuesta con gemma2:2b")
                response = client.generate(
                    model='gemma2:2b',
                    prompt=prompt,
                    options={
                        'temperature': 0.3,  # Contador serio, no inventa números
                        'top_p': 0.9,
                        'num_predict': 200,
                    }
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
                ai_logger.error(f"❌ Error inesperado en Ollama: {type(e).__name__}: {str(e)}")
                return Err(AppError(
                    message=f"Error al consultar al Contador Oriental: {str(e)}"
                ))
            
            # 5. Construir respuesta
            ai_response = AIResponse(
                respuesta=respuesta_texto,
                archivo_usado=archivo,
                gastos_incluidos=cantidad_gastos
            )
            
            return Ok(ai_response)
            
        except Exception as e:
            return Err(AppError(
                message=f"Error en el Contador Oriental: {str(e)}"
            ))
