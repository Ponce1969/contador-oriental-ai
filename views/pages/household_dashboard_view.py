import flet as ft
from typing import TYPE_CHECKING
from controllers.household_controller import HouseholdController
from views.layouts.main_layout import MainLayout
from models.errors import AppError
import datetime
from decimal import Decimal

if TYPE_CHECKING:
    from core.router import Router

from core.session import SessionManager

class HouseholdDashboardView:
    def __init__(self, page: ft.Page, router: 'Router'):
        self.page = page
        self.router = router
        
        # Obtener familia_id de la sesión
        familia_id = SessionManager.get_familia_id(page)
        self.controller = HouseholdController(familia_id=familia_id)
        
        self.household = None
        self.members = []
        self.balances = []
        
    def load_data(self):
        res = self.controller.get_current_household()
        if res.is_ok():
            self.household = res.unwrap()
        
        if self.household:
            members_res = self.controller.get_members()
            if members_res.is_ok():
                self.members = members_res.unwrap()
                
            balances_res = self.controller.get_balance()
            if balances_res.is_ok():
                self.balances = balances_res.unwrap()

    def create_household_ui(self):
        nombre_field = ft.TextField(
            label="Ej: Depto Pocitos, Viaje a Rocha...", 
            border_color=ft.Colors.INDIGO_400,
            focused_border_color=ft.Colors.INDIGO_700,
            border_radius=8,
            width=300
        )
        
        def on_create(e):
            if not nombre_field.value:
                return
            res = self.controller.create_household(nombre_field.value)
            if res.is_ok():
                self.page.snack_bar = ft.SnackBar(ft.Text("Hogar creado con éxito", color=ft.Colors.WHITE), bgcolor=ft.Colors.GREEN_600)
                self.page.snack_bar.open = True
                self.page.controls.clear()
                self.page.add(self.render())
                self.page.update()
            else:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Error: {res.unwrap_err()}", color=ft.Colors.WHITE), bgcolor=ft.Colors.RED_600)
                self.page.snack_bar.open = True
            self.page.update()

        token_field = ft.TextField(
            label="Ej: abc123def456", 
            border_color=ft.Colors.TEAL_400,
            focused_border_color=ft.Colors.TEAL_700,
            border_radius=8,
            width=300
        )

        def on_join(e):
            if not token_field.value:
                return
            res = self.controller.accept_invitation(token_field.value.strip())
            if res.is_ok():
                self.page.overlay.append(ft.SnackBar(ft.Text("Te uniste al Hogar con éxito", color=ft.Colors.WHITE), bgcolor=ft.Colors.GREEN_600, open=True))
                self.page.controls.clear()
                self.page.add(self.render())
                self.page.update()
            else:
                self.page.overlay.append(ft.SnackBar(ft.Text(f"Error: {res.unwrap_err()}", color=ft.Colors.WHITE), bgcolor=ft.Colors.RED_600, open=True))
                self.page.update()

        return ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.GROUPS, size=64, color=ft.Colors.INDIGO_500),
                ft.Text("Compartí gastos con otras personas", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_900),
                ft.Text(
                    "¿Te mudaste con un compañero? ¿Te vas de viaje con amigos? ¿Querés dividir las cuentas con tu pareja?\n\n"
                    "Un 'Hogar Compartido' te permite vincular tu cuenta con la cuenta de otros usuarios de Contador Oriental "
                    "para que todos puedan sumar gastos al pozo común y ver automáticamente quién le debe a quién.",
                    size=16, 
                    color=ft.Colors.BLUE_GREY_700,
                    text_align=ft.TextAlign.CENTER,
                    width=600
                ),
                ft.Container(height=20),
                ft.Card(
                    elevation=4,
                    content=ft.Container(
                        bgcolor=ft.Colors.WHITE,
                        padding=30,
                        content=ft.Column([
                            ft.Text("Crear un nuevo Hogar Compartido", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800),
                            ft.Text("Elegí un nombre para el grupo:", color=ft.Colors.BLUE_GREY_600, size=14),
                            ft.Container(height=10),
                            nombre_field,
                            ft.Container(height=10),
                            ft.ElevatedButton(
                                "Crear Hogar y Empezar", 
                                icon=ft.Icons.ADD_HOME_WORK,
                                style=ft.ButtonStyle(
                                    color=ft.Colors.WHITE,
                                    bgcolor=ft.Colors.INDIGO_600,
                                    padding=20,
                                ),
                                on_click=on_create
                            )
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                    )
                ),
                ft.Container(height=20),
                ft.Card(
                    elevation=4,
                    content=ft.Container(
                        bgcolor=ft.Colors.WHITE,
                        padding=30,
                        content=ft.Column([
                            ft.Text("Unirse a un Hogar Existente", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800),
                            ft.Text("Pegá el token de invitación acá:", color=ft.Colors.BLUE_GREY_600, size=14),
                            ft.Container(height=10),
                            token_field,
                            ft.Container(height=10),
                            ft.ElevatedButton(
                                "Unirse al Hogar", 
                                icon=ft.Icons.GROUP_ADD,
                                style=ft.ButtonStyle(
                                    color=ft.Colors.WHITE,
                                    bgcolor=ft.Colors.TEAL_600,
                                    padding=20,
                                ),
                                on_click=on_join
                            )
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                    )
                )
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO),
            expand=True,
            alignment=ft.Alignment(0, 0)
        )

    def render(self) -> ft.Control:
        self.load_data()
        
        if not self.household:
            content = self.create_household_ui()
        else:
            # Simple dashboard
            current_familia_id = SessionManager.get_familia_id(self.page)
            
            destinatario_dropdown = ft.Dropdown(
                label="A quién le pagaste",
                options=[
                    ft.dropdown.Option(key=str(b.familia_id), text=b.familia_nombre)
                    for b in self.balances if b.familia_id != current_familia_id
                ]
            )
            monto_field = ft.TextField(
                label="Monto ($)",
                keyboard_type=ft.KeyboardType.NUMBER
            )
            
            def close_dialog(e):
                settlement_dialog.open = False
                self.page.update()

            def on_settle(e):
                if not destinatario_dropdown.value or not monto_field.value:
                    self.page.overlay.append(ft.SnackBar(ft.Text("Completá ambos campos"), bgcolor=ft.Colors.RED_600, open=True))
                    self.page.update()
                    return
                try:
                    monto = Decimal(monto_field.value)
                    res = self.controller.record_settlement(
                        recipient_familia_id=int(destinatario_dropdown.value),
                        monto=monto,
                        fecha=datetime.date.today()
                    )
                    if res.is_ok():
                        self.page.overlay.append(ft.SnackBar(ft.Text("Pago registrado con éxito"), bgcolor=ft.Colors.GREEN_600, open=True))
                        close_dialog(None)
                        self.page.controls.clear()
                        self.page.add(self.render())
                    else:
                        self.page.overlay.append(ft.SnackBar(ft.Text(f"Error: {res.unwrap_err()}"), bgcolor=ft.Colors.RED_600, open=True))
                except Exception as err:
                    self.page.overlay.append(ft.SnackBar(ft.Text("Monto inválido"), bgcolor=ft.Colors.RED_600, open=True))
                self.page.update()

            settlement_dialog = ft.AlertDialog(
                title=ft.Text("Saldar Deuda"),
                content=ft.Container(
                    bgcolor=ft.Colors.GREEN_50,
                    border=ft.Border(
                        top=ft.BorderSide(2, ft.Colors.GREEN_200),
                        bottom=ft.BorderSide(2, ft.Colors.GREEN_200),
                        left=ft.BorderSide(2, ft.Colors.GREEN_200),
                        right=ft.BorderSide(2, ft.Colors.GREEN_200),
                    ),
                    border_radius=8,
                    padding=20,
                    content=ft.Column([
                        ft.Text("Registrá un pago que le hiciste a otro miembro por fuera de la app."),
                        ft.Container(height=10),
                        destinatario_dropdown,
                        monto_field
                    ], tight=True)
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=close_dialog),
                    ft.ElevatedButton("Confirmar Pago", bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE, on_click=on_settle)
                ]
            )

            def open_dialog(e):
                if settlement_dialog not in self.page.overlay:
                    self.page.overlay.append(settlement_dialog)
                settlement_dialog.open = True
                self.page.update()

            balance_cards = []
            for b in self.balances:
                balance_cards.append(
                    ft.Card(
                        content=ft.Container(
                            padding=10,
                            content=ft.Column([
                                ft.Text(b.familia_nombre, weight=ft.FontWeight.BOLD),
                                ft.Text(f"Aportó: $ {b.total_contributed:.2f}"),
                                ft.Text(f"Balance: $ {b.net_balance:.2f}", 
                                        color=ft.Colors.RED if b.net_balance > 0 else ft.Colors.GREEN)
                            ])
                        )
                    )
                )
                
            def on_leave(e):
                res = self.controller.leave_household()
                if res.is_ok():
                    self.page.overlay.append(ft.SnackBar(ft.Text("Abandonaste el hogar exitosamente."), bgcolor=ft.Colors.GREEN_600, open=True))
                    self.page.controls.clear()
                    self.page.add(self.render())
                else:
                    self.page.overlay.append(ft.SnackBar(ft.Text(f"No podés salir: {res.unwrap_err()}"), bgcolor=ft.Colors.RED_600, open=True))
                self.page.update()

            content = ft.Column([
                # ── Sección Título: fondo crema ─────────────────────────
                ft.Container(
                    content=ft.Row([
                        ft.Text(f"Hogar: {self.household.nombre}", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800),
                        ft.ElevatedButton("Abandonar Hogar", icon=ft.Icons.EXIT_TO_APP, color=ft.Colors.WHITE, bgcolor=ft.Colors.RED_600, on_click=on_leave)
                    ], wrap=True, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    bgcolor="#FFF8E7",
                    padding=ft.Padding.only(left=20, right=20, top=18, bottom=18),
                    border_radius=12,
                ),
                # ── Sección Balances: fondo lila pálido ─────────────────
                ft.Container(
                    content=ft.Column([
                        ft.Text("Balances", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800),
                        ft.Row(balance_cards, wrap=True) if balance_cards else ft.Text("No hay balances todavía", italic=True, color=ft.Colors.BLUE_GREY_400),
                    ]),
                    bgcolor="#F3E8FF",
                    padding=20,
                    border_radius=12,
                ),
                # ── Sección Acciones: fondo blanco ──────────────────────
                ft.Container(
                    content=ft.Row([
                        ft.ElevatedButton("Saldar Deuda (Registrar Pago)", icon=ft.Icons.PAYMENTS, color=ft.Colors.WHITE, bgcolor=ft.Colors.GREEN_600, on_click=open_dialog),
                        ft.ElevatedButton("Gestionar Miembros e Invitaciones", on_click=lambda _: self.router.navigate("/household/members"))
                    ], alignment=ft.MainAxisAlignment.START, wrap=True),
                    bgcolor=ft.Colors.WHITE,
                    padding=ft.Padding.only(left=20, right=20, top=12, bottom=12),
                ),
                # ── Footer: lila suave ──────────────────────────────────
                ft.Container(
                    content=ft.Row([
                        ft.Text("Contador Oriental · Hogares Compartidos", size=11, color=ft.Colors.BLUE_GREY_400, italic=True)
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    bgcolor="#EDE7F6",
                    padding=ft.Padding.only(top=14, bottom=14),
                ),
            ], spacing=8, scroll=ft.ScrollMode.AUTO)

        return MainLayout(
            page=self.page,
            router=self.router,
            content=ft.Container(
                content=content,
                padding=20,
                expand=True
            )
        )
