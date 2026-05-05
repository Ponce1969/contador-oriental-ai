"""
Vista de "Mis Planes" - Fintech Premium Dark Theme.
Compras en cuotas con barras de progreso y glassmorphism.
"""
from __future__ import annotations

from decimal import Decimal

import flet as ft

from controllers.installment_controller import InstallmentController
from core.session import SessionManager
from core.state import AppState
from services.infrastructure.formatters import format_pesos
from views.layouts.main_layout import MainLayout

# ── Fintech Dark Palette ─────────────────────────────────────────────
_NAVY = "#0f172a"          # fondo principal
_SLATE = "#1e293b"         # cards
_EMERALD = "#10b981"       # positivo, progreso, totales
_EMERALD_MINT = "#34d399"  # brillo del gradiente
_RUBY = "#e11d48"          # alerta, deuda
_AMBER = "#f59e0b"         # advertencia intermedia
_SLATE_TEXT = "#94a3b8"    # texto secundario
_WHITE = "#f8fafc"         # texto principal
_BORDER = "rgba(255,255,255,0.05)"


def _color_semaforo(ratio: float) -> str:
    """Colores semaforicos: 80%+ emerald, 40-80% amber, <40% ruby."""
    if ratio >= 0.80:
        return _EMERALD
    elif ratio >= 0.40:
        return _AMBER
    else:
        return _RUBY


def _barra_progreso(pagadas: int, total: int) -> ft.Control:
    """Barra de progreso premium con degradado y glow."""
    ratio = float(pagadas / total) if total > 0 else 0.0
    color = _color_semaforo(ratio)
    celebrando = ratio >= 0.80

    return ft.Column(
        controls=[
            # Contenedor exterior con sombra glow
            ft.Container(
                content=ft.Container(
                    width=ratio * 300 if ratio > 0 else 4,
                    height=8,
                    border_radius=10,
                    gradient=ft.LinearGradient(
                        begin=ft.alignment.Alignment(-1, 0),
                        end=ft.alignment.Alignment(1, 0),
                        colors=[_EMERALD, _EMERALD_MINT],
                    ),
                    shadow=(
                        ft.BoxShadow(
                            spread_radius=2 if celebrando else 0.5,
                            blur_radius=8 if celebrando else 3,
                            color=f"{_EMERALD}44" if celebrando else f"{_EMERALD}22",
                        )
                    ),
                ),
                border_radius=10,
                bgcolor="#334155",
                height=8,
                animate=ft.Animation(600, ft.AnimationCurve.EASE_OUT),
            ),
            ft.Row(
                controls=[
                    ft.Text(
                        f"{pagadas}/{total} cuotas",
                        size=11,
                        color=color,
                        weight=ft.FontWeight.W_600,
                    ),
                ],
            ),
        ],
        spacing=4,
    )


class PlanesView:
    """Vista premium de compras en cuotas activas."""

    def __init__(self, page: ft.Page, router):
        self.page = page
        self.router = router

        if not SessionManager.is_logged_in(page):
            router.navigate("/login")
            return

        familia_id = SessionManager.get_familia_id(page)
        self.controller = InstallmentController(familia_id=familia_id)
        self._planes_column = ft.Column(spacing=14)

    def render(self):
        is_mobile = AppState.device == "mobile"

        content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Text(
                                    value="Mis Planes",
                                    size=22 if is_mobile else 28,
                                    weight=ft.FontWeight.BOLD,
                                    color=_WHITE,
                                ),
                            ],
                        ),
                        padding=ft.padding.only(bottom=4),
                    ),
                    ft.Text(
                        "Compras en cuotas activas y su progreso",
                        size=12,
                        color=_SLATE_TEXT,
                    ),
                    ft.Divider(color="#334155", height=24),
                    self._planes_column,
                ],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=20,
            expand=True,
        )

        self._render_planes()

        return MainLayout(
            page=self.page,
            content=content,
            router=self.router,
        )

    def _render_planes(self) -> None:
        self._planes_column.controls.clear()

        planes = self.controller.obtener_cuotas_pendientes()

        if not planes:
            self._planes_column.controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(
                                ft.Icons.CHECK_CIRCLE_OUTLINE,
                                size=64,
                                color=_EMERALD,
                            ),
                            ft.Text(
                                "No tenes cuotas pendientes",
                                size=16,
                                weight=ft.FontWeight.W_600,
                                color=_WHITE,
                            ),
                            ft.Text(
                                "Todas tus compras estan pagas.",
                                size=12,
                                color=_SLATE_TEXT,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    padding=60,
                    alignment=ft.alignment.Alignment(0, 0),
                )
            )
            return

        # ── Header: total del mes ──
        total_mes = Decimal("0")
        for plan in planes:
            total_mes += plan.monto_por_cuota

        self._planes_column.controls.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CREDIT_CARD, color=_EMERALD, size=20),
                        ft.Text(
                            f"Cuotas del mes: {format_pesos(total_mes)}",
                            size=14,
                            weight=ft.FontWeight.W_600,
                            color=_EMERALD,
                        ),
                        ft.Text(
                            f"({len(planes)} compras activas)",
                            size=12,
                            color=_SLATE_TEXT,
                        ),
                    ],
                    spacing=8,
                ),
                padding=ft.padding.only(bottom=12),
            ),
        )

        # ── Cards de planes ──
        for plan in sorted(planes, key=lambda p: p.cuotas_restantes):
            pagadas = plan.cuotas_pagadas_calculada
            ratio = float(pagadas / plan.numero_cuotas)
            celebrando = ratio >= 0.80
            color_acento = _color_semaforo(ratio)

            self._planes_column.controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Column(
                                        controls=[
                                            ft.Text(
                                                plan.descripcion,
                                                size=15,
                                                weight=ft.FontWeight.BOLD,
                                                color=_WHITE,
                                            ),
                                            ft.Text(
                                                f"{plan.nombre_tarjeta} · "
                                                f"{format_pesos(plan.monto_por_cuota)}"
                                                f" c/u",
                                                size=11,
                                                color=_SLATE_TEXT,
                                            ),
                                        ],
                                        expand=True,
                                    ),
                                    ft.Text(
                                        format_pesos(plan.monto_total),
                                        size=20,
                                        weight=ft.FontWeight.BOLD,
                                        color=color_acento,
                                    ),
                                ],
                            ),
                            ft.Container(height=10),
                            _barra_progreso(pagadas, plan.numero_cuotas),
                            ft.Container(height=4),
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        f"Restan {plan.cuotas_restantes} cuotas",
                                        size=11,
                                        color=_SLATE_TEXT,
                                    ),
                                    (
                                        ft.Container(
                                            content=ft.Row(
                                                controls=[
                                                    ft.Icon(
                                                        ft.Icons.LOCAL_FIRE_DEPARTMENT,
                                                        size=12,
                                                        color=_EMERALD_MINT,
                                                    ),
                                                    ft.Text(
                                                        "Casi listo!",
                                                        size=11,
                                                        weight=ft.FontWeight.W_600,
                                                        color=_EMERALD_MINT,
                                                    ),
                                                ],
                                                spacing=4,
                                            ),
                                        )
                                        if celebrando
                                        else ft.Container()
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                        ],
                        spacing=2,
                    ),
                    padding=18,
                    border_radius=16,
                    bgcolor=_SLATE,
                    border=ft.border.all(1, _BORDER),
                    shadow=(
                        ft.BoxShadow(
                            spread_radius=0,
                            blur_radius=12,
                            color=f"{_EMERALD}22",
                        )
                        if celebrando
                        else ft.BoxShadow(
                            spread_radius=0,
                            blur_radius=4,
                            color="#00000022",
                        )
                    ),
                    animate=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
                )
            )
