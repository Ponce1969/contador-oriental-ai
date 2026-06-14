import flet as ft

from core.logger import get_logger

logger = get_logger("Router")


class Router:
    def __init__(self, page):
        self.page = page
        self.current_route = "/"
        self.routes = self._load_routes()

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
            view = routes[route](self.page, self)
            self.page.add(view)
        except Exception:
            logger.exception("Error rendering view")
            self.page.add(ft.Text(value="Internal application error"))

        self.page.update()
