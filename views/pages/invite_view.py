from typing import TYPE_CHECKING

import flet as ft

from controllers.household_controller import HouseholdController
from core.session import SessionManager
from views.layouts.main_layout import MainLayout

if TYPE_CHECKING:
    from core.router import Router

class InviteView:
    def __init__(self, page: ft.Page, router: 'Router'):
        self.page = page
        self.router = router
        self.token = self._extract_token()

    def _extract_token(self) -> str | None:
        """Extrae el token usando el patrón recomendado de Flet Web."""
        try:
            if hasattr(self.page, "query") and self.page.query:
                val = self.page.query.get("token")
                if val:
                    return val

        except Exception:
            pass

        route = getattr(self.page, "route", "")
        if route and "?" in route:
            from urllib.parse import parse_qs, urlparse
            params = parse_qs(urlparse(route).query)
            if "token" in params:
                return params["token"][0]

        url = getattr(self.page, "url", "")
        if url and "?" in url:
            from urllib.parse import parse_qs, urlparse
            params = parse_qs(urlparse(url).query)
            if "token" in params:
                return params["token"][0]
                
        return None

    def render(self) -> ft.Control:
        if not self.token:
            return MainLayout(
                page=self.page,
                router=self.router,
                content=ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.ERROR_OUTLINE, size=64, color=ft.Colors.RED_400),
                        ft.Text("Enlace de invitación inválido", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text("No se encontró ningún token en el enlace."),
                        ft.ElevatedButton("Ir al Inicio", on_click=lambda _: self.router.navigate("/"))
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.Alignment(0, 0),
                    expand=True
                )
            )

        # Validar token antes de pedir login o mostrar botón
        is_valid_res = HouseholdController.is_invitation_valid(self.token)
        if is_valid_res.is_err() or not is_valid_res.unwrap():
            return MainLayout(
                page=self.page,
                router=self.router,
                content=ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.TIMER_OFF, size=64, color=ft.Colors.ORANGE_400),
                        ft.Text("El enlace expiró o ya fue usado", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                        ft.Text("Pedile un nuevo enlace a tu amigo para unirte al grupo.", text_align=ft.TextAlign.CENTER),
                        ft.Container(height=20),
                        ft.ElevatedButton("Ir al Inicio", on_click=lambda _: self.router.navigate("/"))
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.Alignment(0, 0),
                    expand=True
                )
            )

        if not SessionManager.is_logged_in(self.page):
            # Guardamos el token para que al iniciar sesión lo redirijamos
            SessionManager.set_pending_invite(self.page, self.token)
            
            return MainLayout(
                page=self.page,
                router=self.router,
                content=ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.MAIL, size=64, color=ft.Colors.BLUE_400),
                        ft.Text("¡Te han invitado a compartir gastos!", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                        ft.Text("Para aceptar la invitación, necesitás tener una cuenta en Contador Oriental.", text_align=ft.TextAlign.CENTER),
                        ft.Container(height=20),
                        ft.Row([
                            ft.ElevatedButton("Iniciar Sesión", icon=ft.Icons.LOGIN, on_click=lambda _: self.router.navigate("/login")),
                            ft.ElevatedButton("Registrarse", icon=ft.Icons.PERSON_ADD, on_click=lambda _: self.router.navigate("/register")),
                        ], alignment=ft.MainAxisAlignment.CENTER)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.Alignment(0, 0),
                    expand=True
                )
            )

        # Usuario está logueado
        def on_accept(e):
            familia_id = SessionManager.get_familia_id(self.page)
            if not familia_id:
                return
                
            controller = HouseholdController(familia_id=familia_id)
            res = controller.accept_invitation(self.token)
            
            if res.is_ok():
                SessionManager.clear_pending_invite(self.page)
                self.page.overlay.append(ft.SnackBar(ft.Text("¡Invitación aceptada exitosamente!"), bgcolor=ft.Colors.GREEN_600, open=True))
                self.router.navigate("/household")
            else:
                self.page.overlay.append(ft.SnackBar(ft.Text(f"Error: {res.unwrap_err()}"), bgcolor=ft.Colors.RED_600, open=True))
            self.page.update()
            
        def on_decline(e):
            SessionManager.clear_pending_invite(self.page)
            self.router.navigate("/")

        return MainLayout(
            page=self.page,
            router=self.router,
            content=ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.GROUP_ADD, size=64, color=ft.Colors.GREEN_400),
                    ft.Text("Invitación a Hogar", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text("¿Querés aceptar la invitación y unirte al grupo para compartir gastos?"),
                    ft.Container(height=20),
                    ft.Row([
                        ft.ElevatedButton("Aceptar Invitación", icon=ft.Icons.CHECK, bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE, on_click=on_accept),
                        ft.TextButton("Rechazar", on_click=on_decline),
                    ], alignment=ft.MainAxisAlignment.CENTER)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.Alignment(0, 0),
                expand=True
            )
        )
