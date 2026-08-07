import flet as ft
from typing import TYPE_CHECKING
from controllers.household_controller import HouseholdController
from views.layouts.main_layout import MainLayout

if TYPE_CHECKING:
    from core.router import Router

from core.session import SessionManager

class HouseholdMembersView:
    def __init__(self, page: ft.Page, router: 'Router'):
        self.page = page
        self.router = router
        familia_id = SessionManager.get_familia_id(page)
        self.controller = HouseholdController(familia_id=familia_id)
        self.members = []
        
    def render(self) -> ft.Control:
        res = self.controller.get_members()
        if res.is_ok():
            self.members = res.unwrap()
            
        def on_invite(e):
            inv_res = self.controller.create_invitation()
            if inv_res.is_ok():
                inv = inv_res.unwrap()
                # En un entorno real se mostraría un link de invitación
                self.page.clipboard.set(inv.token)
                self.page.snack_bar = ft.SnackBar(ft.Text("Token de invitación copiado al portapapeles."))
                self.page.snack_bar.open = True
            else:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Error: {inv_res.unwrap_err()}"))
                self.page.snack_bar.open = True
            self.page.update()

        member_list = ft.ListView(expand=1, spacing=10, padding=20)
        for m in self.members:
            member_list.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.PERSON),
                    title=ft.Text(f"Familia {m.familia_id}"),
                    subtitle=ft.Text(f"Rol: {m.role}"),
                )
            )

        content = ft.Column([
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: self.router.navigate("/household")),
                ft.Text("Gestión de Miembros", size=24, weight=ft.FontWeight.BOLD),
            ]),
            ft.Divider(),
            ft.ElevatedButton("Generar Invitación", icon=ft.Icons.ADD_LINK, on_click=on_invite),
            ft.Container(height=20),
            member_list
        ], expand=True)

        return MainLayout(
            page=self.page,
            router=self.router,
            content=ft.Container(
                content=content,
                padding=20,
                expand=True
            )
        )
