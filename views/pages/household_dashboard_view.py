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
        nombre_field = ft.TextField(label="Nombre del nuevo hogar")
        
        def on_create(e):
            if not nombre_field.value:
                return
            res = self.controller.create_household(nombre_field.value)
            if res.is_ok():
                self.page.snack_bar = ft.SnackBar(ft.Text("Hogar creado con éxito"))
                self.page.snack_bar.open = True
                self.router.navigate("/household")
            else:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Error: {res.unwrap_err()}"))
                self.page.snack_bar.open = True
            self.page.update()

        return ft.Column([
            ft.Text("No pertenecés a ningún hogar.", size=20, weight=ft.FontWeight.BOLD),
            ft.Text("Creá uno nuevo para compartir gastos con amigos o familia."),
            nombre_field,
            ft.ElevatedButton("Crear Hogar", on_click=on_create)
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

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
            title="Hogar Compartido",
            content=ft.Container(
                content=content,
                padding=20,
                expand=True
            )
        )
