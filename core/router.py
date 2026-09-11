import flet as ft

from core.logger import get_logger

logger = get_logger("Router")


class Router:
    @classmethod
    def get(cls, page) -> "Router":
        """Obtener o registrar la instancia única de Router para la página."""
        if not hasattr(page, "data") or not isinstance(page.data, dict):
            page.data = {}
        if "router" not in page.data or not isinstance(page.data["router"], cls):
            page.data["router"] = cls(page)
        return page.data["router"]

    def __init__(self, page):
        self.page = page
        self._current_route = "/"
        if hasattr(self.page, "data") and isinstance(self.page.data, dict):
            if "current_route" in self.page.data:
                self._current_route = self.page.data["current_route"]
            else:
                self.page.data["current_route"] = self._current_route
            self.page.data["router"] = self
        self.routes = self._load_routes()

    @property
    def current_route(self) -> str:
        if hasattr(self.page, "data") and isinstance(self.page.data, dict):
            return self.page.data.get("current_route", self._current_route)
        return self._current_route

    @current_route.setter
    def current_route(self, value: str) -> None:
        self._current_route = value
        if hasattr(self.page, "data") and isinstance(self.page.data, dict):
            self.page.data["current_route"] = value

    def _load_routes(self):
        from configs.routes import routes

        return routes

    @staticmethod
    def _strip_query(route: str) -> str:
        """Remove query string from route for dict lookup.
        e.g. '/reset-password?token=abc' -> '/reset-password'
        """
        return route.split("?")[0]

    def navigate(self, route):
        routes = self.routes

        # Strip query params before matching (token is read from page.query)
        clean_route = self._strip_query(route)
        if clean_route not in routes:
            logger.warning(f"Route not found: {clean_route}")
            clean_route = "/"

        logger.info(f"Navigating to: {clean_route}")
        self.current_route = clean_route
        self.page.controls.clear()

        try:
            view = routes[clean_route](self.page, self)
            self.page.add(view)
        except Exception:
            logger.exception("Error rendering view")
            self.page.add(ft.Text(value="Internal application error"))

        self.page.update()
