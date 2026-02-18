from __future__ import annotations

import importlib
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:
    from core.router import Router

logger = logging.getLogger(__name__)

ROUTES = [
    {
        "path": "/login",
        "view": "views.pages.login_view.LoginView",
        "label": "🔐 Login",
        "icon": ft.Icons.LOGIN,
        "show_in_top": False,
        "show_in_bottom": False,
    },
    {
        "path": "/register",
        "view": "views.register_view.RegisterView",
        "label": "📝 Registro",
        "icon": ft.Icons.PERSON_ADD,
        "show_in_top": False,
        "show_in_bottom": False,
    },
    {
        "path": "/",
        "view": "views.pages.dashboard_view.DashboardView",
        "label": "📊 Dashboard",
        "icon": ft.Icons.DASHBOARD,
        "show_in_top": True,
        "show_in_bottom": True,
    },
    {
        "path": "/home",
        "view": "views.pages.home_view.HomeView",
        "label": "🏠 Inicio",
        "icon": ft.Icons.HOME,
        "show_in_top": False,
        "show_in_bottom": False,
    },
    {
        "path": "/family",
        "view": "views.pages.family_members_view.FamilyMembersView",
        "label": "� Familia",
        "icon": ft.Icons.PEOPLE,
        "show_in_top": True,
        "show_in_bottom": True,
    },
    {
        "path": "/incomes",
        "view": "views.pages.incomes_view.IncomesView",
        "label": "💰 Ingresos",
        "icon": ft.Icons.ACCOUNT_BALANCE_WALLET,
        "show_in_top": True,
        "show_in_bottom": True,
    },
    {
        "path": "/expenses",
        "view": "views.pages.expenses_view.ExpensesView",
        "label": "💸 Gastos",
        "icon": ft.Icons.MONEY_OFF,
        "show_in_top": True,
        "show_in_bottom": True,
    },
    {
        "path": "/ai-contador",
        "view": "views.pages.ai_advisor_view.AIAdvisorView",
        "label": "🧮 Contador Oriental",
        "icon": ft.Icons.PSYCHOLOGY,
        "show_in_top": True,
        "show_in_bottom": True,
    },
    {
        "path": "/shopping",
        "view": "views.pages.shopping_view.ShoppingView",
        "label": "Shopping (legacy)",
        "icon": ft.Icons.SHOPPING_CART,
        "show_in_top": False,
        "show_in_bottom": False,
    },
    {
        "path": "/settings",
        "view": "views.pages.settings_view.SettingsView",
        "label": "menu.settings",
        "icon": ft.Icons.SETTINGS,
        "show_in_top": True,
        "show_in_bottom": False,
    },
    {
        "path": "/help",
        "view": "views.pages.help_view.HelpView",
        "label": "menu.help",
        "icon": ft.Icons.HELP,
        "show_in_top": True,
        "show_in_bottom": True,
    }
]

def load_view_class(view_path: str) -> type | None:
    """
    Carga dinámicamente una clase de vista desde su ruta de módulo.
    
    Args:
        view_path: Ruta completa del módulo y clase (ej: 'views.pages.login_view.LoginView')
        
    Returns:
        Clase de vista o None si falla la carga
    """
    module_name, class_name = view_path.rsplit(".", 1)
    
    try:
        module = importlib.import_module(module_name)
        view_class = getattr(module, class_name)
        return view_class
    except (ImportError, AttributeError) as e:
        logger.error(f"Error al cargar view {view_path}: {e}")
        return None


def create_view_renderer(view_path: str) -> Callable:
    """
    Crea una función nombrada que renderiza una vista.
    Más legible y debuggeable que lambdas anidadas.
    
    Args:
        view_path: Ruta completa del módulo y clase de la vista
        
    Returns:
        Función que instancia y renderiza la vista
    """
    def render_view(page: ft.Page, router: Router) -> ft.Control:
        view_class = load_view_class(view_path)
        if view_class is None:
            logger.error(f"No se pudo cargar la vista: {view_path}")
            return ft.Text("Error: Vista no encontrada")
        
        view_instance = view_class(page, router)
        return view_instance.render()
    
    # Asignar nombre descriptivo para debugging
    render_view.__name__ = f"render_{view_path.split('.')[-1]}"
    return render_view


def build_routes_dict() -> dict[str, Callable]:
    """
    Construye el diccionario de rutas mapeando paths a funciones de renderizado.
    Usa funciones nombradas en lugar de lambdas para mejor legibilidad.
    
    Returns:
        Diccionario con paths como keys y funciones de renderizado como values
    """
    routes_dict = {}
    
    for route_config in ROUTES:
        path = route_config["path"]
        view_path = route_config["view"]
        routes_dict[path] = create_view_renderer(view_path)
    
    logger.info(f"Rutas configuradas: {len(routes_dict)} rutas cargadas")
    return routes_dict


routes = build_routes_dict()

