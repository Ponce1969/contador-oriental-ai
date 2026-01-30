from __future__ import annotations

from datetime import date

import flet as ft
from result import Err, Ok

from controllers.shopping_controller import ShoppingController
from flet_types.flet_types import CorrectElevatedButton, CorrectSnackBar
from models.errors import AppError
from models.shopping_model import ShoppingItem
from views.layouts.main_layout import MainLayout


class ShoppingView:
    def __init__(self, page, router):
        self.page = page
        self.router = router

        # Controller con gestión automática de sesión
        self.controller = ShoppingController()

        self.name_input = ft.TextField(label="Producto", width=200)
        self.price_input = ft.TextField(label="Precio", width=100)
        self.category_input = ft.TextField(label="Categoría", width=150)
        self.items_column = ft.Column()

    def render(self):
        content = ft.Column(
            controls=[
                ft.Text(value=self.controller.get_title(), size=24),
                ft.Divider(),
                ft.Row(
                    controls=[
                        self.name_input,
                        self.price_input,
                        self.category_input,
                        CorrectElevatedButton("Agregar", on_click=self._on_add_item)
                    ]
                ),
                ft.Divider(),
                self.items_column,
            ],
            spacing=16,
        )

        # Render items iniciales
        self._render_items()

        return MainLayout(
            page=self.page,
            content=content,
            router=self.router,
        )

    def _on_add_item(self, _: ft.ControlEvent) -> None:
        item = ShoppingItem(
            name=self.name_input.value or "",
            price=float(self.price_input.value or 0),
            category=self.category_input.value or "General",
            purchase_date=date.today(),
        )

        result = self.controller.add_item(item)

        match result:
            case Ok(_):
                self._clear_inputs()
                self._render_items()

            case Err(error):
                self._show_error(error)

    def _render_items(self) -> None:
        self.items_column.controls.clear()

        for item in self.controller.list_items():
            self.items_column.controls.append(
                ft.Text(value=f"{item.name} - ${item.price:.2f} [{item.category}]")
            )

        self.page.update()

    def _clear_inputs(self) -> None:
        self.name_input.value = ""
        self.price_input.value = ""
        self.category_input.value = ""

    def _show_error(self, error: AppError) -> None:
        snack_bar = CorrectSnackBar(
            content=ft.Text(value=error.message),
            open=True
        )
        self.page.overlay.append(snack_bar)
        self.page.update()
