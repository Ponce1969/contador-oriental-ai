import flet as ft
from typing import TYPE_CHECKING
from controllers.household_controller import HouseholdController
from views.layouts.main_layout import MainLayout
from models.errors import AppError
import datetime
from decimal import Decimal

if TYPE_CHECKING:
    from core.router import Router

class HouseholdDashboardView:
    def __init__(self, page: ft.Page, router: 'Router'):
        self.page = page
        self.router = router
        self.controller = HouseholdController()
        
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
                self.router.navigate("/household")
            else:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Error: {res.unwrap_err()}", color=ft.Colors.WHITE), bgcolor=ft.Colors.RED_600)
                self.page.snack_bar.open = True
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
                    color=ft.Colors.WHITE,
                    content=ft.Container(
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
                )
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            expand=True,
            alignment=ft.alignment.center
        )

    def render(self) -> ft.Control:
        self.load_data()
        
        if not self.household:
            content = self.create_household_ui()
        else:
            # Simple dashboard
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
                
            content = ft.Column([
                ft.Text(f"Hogar: {self.household.nombre}", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("Balances", size=18, weight=ft.FontWeight.BOLD),
                ft.Row(balance_cards, wrap=True),
                ft.Divider(),
                ft.ElevatedButton("Gestionar Miembros e Invitaciones", 
                                 on_click=lambda _: self.router.navigate("/household/members"))
            ])

        return MainLayout(
            page=self.page,
            router=self.router,
            content=ft.Container(
                content=content,
                padding=20,
                expand=True
            )
        )
