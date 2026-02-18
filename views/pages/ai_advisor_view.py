"""
Vista de chat con el Contador Oriental
"""

from __future__ import annotations

import flet as ft
from result import Err, Ok

from controllers.ai_controller import AIController
from core.session import SessionManager
from flet_types.flet_types import CorrectElevatedButton, CorrectSnackBar
from models.ai_model import ChatMessage
from views.layouts.main_layout import MainLayout


class AIAdvisorView:
    """Vista de chat con el Contador Oriental"""
    
    def __init__(self, page, router):
        self.page = page
        self.router = router
        
        # Verificar login
        if not SessionManager.is_logged_in(page):
            router.navigate("/login")
            return
        
        # Obtener familia_id de la sesión
        familia_id = SessionManager.get_familia_id(page)
        
        # Controller
        self.controller = AIController(familia_id=familia_id)
        
        # Historial de chat
        self.chat_history: list[ChatMessage] = []
        
        # Campo de pregunta
        self.pregunta_input = ft.TextField(
            label="Pregunta al Contador Oriental",
            hint_text="Ej: ¿Me conviene pagar el súper con débito?",
            multiline=True,
            min_lines=2,
            max_lines=4,
            width=600,
            autofocus=True
        )
        
        # Checkbox para incluir gastos
        self.incluir_gastos_checkbox = ft.Checkbox(
            label="Incluir mis gastos recientes en la consulta",
            value=True
        )
        
        # Columna de chat con fondo gris para contraste
        self.chat_column = ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            height=400,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )
        
        # Indicador de carga elegante con mensaje
        self.progress_ring = ft.ProgressRing(
            width=20,
            height=20,
            stroke_width=2,
            color=ft.Colors.BLUE_700
        )
        
        self.progress_text = ft.Text(
            value="El Contador Oriental está reflexionando...",
            size=13,
            color=ft.Colors.BLUE_700,
            italic=True
        )
        
        self.loading_indicator = ft.Row(
            controls=[
                self.progress_ring,
                self.progress_text
            ],
            spacing=10,
            visible=False
        )
    
    def render(self):
        """Renderizar la vista completa"""
        content = ft.Column(
            controls=[
                ft.Text(
                    value=self.controller.get_title(),
                    size=28,
                    weight=ft.FontWeight.BOLD
                ),
                ft.Text(
                    value=self.controller.get_description(),
                    size=14,
                    color=ft.Colors.GREY_700
                ),
                ft.Divider(),
                
                # Área de chat con fondo gris claro
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                value="💬 Conversación",
                                size=20,
                                weight=ft.FontWeight.BOLD
                            ),
                            self.chat_column,
                        ],
                        spacing=5
                    ),
                    padding=5,
                    bgcolor=ft.Colors.GREY_100,
                    border_radius=10,
                ),
                
                ft.Divider(),
                
                # Formulario de pregunta
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                value="❓ Hacer una pregunta",
                                size=20,
                                weight=ft.FontWeight.BOLD
                            ),
                            self.pregunta_input,
                            self.incluir_gastos_checkbox,
                            ft.Row(
                                controls=[
                                    CorrectElevatedButton(
                                        "🧮 Consultar",
                                        on_click=self._on_consultar
                                    ),
                                    self.loading_indicator,
                                ],
                                spacing=10
                            ),
                        ],
                        spacing=10
                    ),
                    padding=20,
                    bgcolor=ft.Colors.GREEN_50,
                    border=ft.border.all(2, ft.Colors.GREEN_200),
                    border_radius=10,
                ),
                
                # Ejemplos de preguntas
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                value="💡 Ejemplos de preguntas:",
                                size=16,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Text("• ¿Me conviene pagar con débito o crédito?"),
                            ft.Text("• ¿Cómo puedo ahorrar en impuestos?"),
                            ft.Text("• ¿Qué hago con mis ahorros?"),
                            ft.Text("• ¿Puedo deducir el alquiler?"),
                        ],
                        spacing=5
                    ),
                    padding=15,
                    bgcolor=ft.Colors.AMBER_50,
                    border_radius=10,
                ),
            ],
            spacing=20,
            scroll=ft.ScrollMode.AUTO
        )
        
        # Mensaje de bienvenida
        self._agregar_mensaje_bienvenida()
        
        return MainLayout(
            page=self.page,
            content=content,
            router=self.router,
        )
    
    def _agregar_mensaje_bienvenida(self):
        """Agrega mensaje de bienvenida al chat"""
        mensaje = ChatMessage(
            role="assistant",
            content="¡Hola! Soy el Contador Oriental, tu asistente contable. "
                   "Preguntame sobre impuestos, ahorros o cómo optimizar tus gastos en Uruguay."
        )
        self.chat_history.append(mensaje)
        self._render_chat()
    
    def _on_consultar(self, e):
        """Manejar consulta al contador"""
        if not self.pregunta_input.value:
            self._show_error("Por favor escribe una pregunta")
            return
        
        # Guardar pregunta antes de limpiar
        pregunta = self.pregunta_input.value
        
        # Agregar pregunta al historial
        self.chat_history.append(ChatMessage(role="user", content=pregunta))
        self._render_chat()
        
        # Mostrar ProgressRing, limpiar y deshabilitar input
        self.loading_indicator.visible = True
        self.pregunta_input.value = ""
        self.pregunta_input.disabled = True
        self.page.update()
        
        # Consultar al contador en thread separado para no bloquear UI
        incluir_gastos = self.incluir_gastos_checkbox.value or False
        
        def consultar_async():
            result = self.controller.consultar_contador(
                pregunta=pregunta,
                incluir_gastos=incluir_gastos
            )
            
            # Procesar resultado
            match result:
                case Ok(response):
                    self.chat_history.append(
                        ChatMessage(role="assistant", content=response.respuesta)
                    )
                case Err(error):
                    # Mostrar error en el chat también
                    self.chat_history.append(
                        ChatMessage(
                            role="assistant",
                            content=f"❌ Error: {error.message}"
                        )
                    )
                    self._show_error(error.message)
            
            # Ocultar loading
            self.loading_indicator.visible = False
            self.pregunta_input.disabled = False
            self._render_chat()
            self.page.update()
        
        # Ejecutar en thread separado
        import threading
        thread = threading.Thread(target=consultar_async, daemon=True)
        thread.start()
    
    def _render_chat(self):
        """Renderizar chat estilo WhatsApp/Telegram moderno y responsive"""
        self.chat_column.controls.clear()
        
        for mensaje in self.chat_history:
            if mensaje.role == "user":
                # Usuario a la derecha (azul oscuro)
                self.chat_column.controls.append(
                    ft.Row(
                        controls=[
                            ft.Container(expand=True),
                            ft.Container(
                                content=ft.Text(
                                    value=mensaje.content,
                                    size=15,
                                    color=ft.Colors.WHITE,
                                    selectable=True,
                                    no_wrap=False
                                ),
                                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                                bgcolor=ft.Colors.BLUE_700,
                                border_radius=ft.border_radius.only(
                                    top_left=18,
                                    top_right=18,
                                    bottom_left=18,
                                    bottom_right=4
                                ),
                                shadow=ft.BoxShadow(
                                    spread_radius=0,
                                    blur_radius=3,
                                    color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK),
                                    offset=ft.Offset(0, 1)
                                ),
                                margin=ft.margin.only(left=40, bottom=8),
                            ),
                        ]
                    )
                )
            else:
                # Bot a la izquierda (blanco con borde)
                self.chat_column.controls.append(
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Text(
                                            value="🧮",
                                            size=18
                                        ),
                                        ft.Text(
                                            value=mensaje.content,
                                            size=15,
                                            color=ft.Colors.BLACK87,
                                            selectable=True,
                                            no_wrap=False
                                        ),
                                    ],
                                    spacing=5,
                                    tight=True
                                ),
                                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                                bgcolor=ft.Colors.WHITE,
                                border=ft.border.all(1, ft.Colors.GREY_300),
                                border_radius=ft.border_radius.only(
                                    top_left=18,
                                    top_right=18,
                                    bottom_left=4,
                                    bottom_right=18
                                ),
                                shadow=ft.BoxShadow(
                                    spread_radius=0,
                                    blur_radius=3,
                                    color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK),
                                    offset=ft.Offset(0, 1)
                                ),
                                margin=ft.margin.only(right=40, bottom=8),
                                expand=True
                            ),
                            ft.Container(expand=True),
                        ]
                    )
                )
    
    def _show_error(self, msg: str):
        """Mostrar mensaje de error"""
        self.page.snack_bar = CorrectSnackBar(
            content=ft.Text(f"❌ {msg}"),
            open=True,
        )
        self.page.update()
