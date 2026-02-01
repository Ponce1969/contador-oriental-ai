
import importlib

import flet as ft

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

def load_view(view_path: str):
    module_name, class_name = view_path.rsplit(".", 1)
    
    try:
        module = importlib.import_module(module_name)
        view_class = getattr(module, class_name)
        return view_class
    except (ImportError, AttributeError) as e:
        print(f"Erro ao carregar view {view_path}: {e}")
        return None

def get_routes():
    routes = {}

    for r in ROUTES:
        view_path = str(r["view"])  # Asegurar que es string
        def create_view_lambda(path=view_path):
            return lambda page, router: load_view(path)(page, router).render()

        routes[r["path"]] = create_view_lambda()

    return routes

routes = get_routes()

