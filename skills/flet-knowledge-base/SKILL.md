---
name: flet-knowledge-base
description: "Trigger: Flet web, deep link, route, query param, page.route, page.query, password reset, Flet bug, Flet gotcha, Flet version. Portable knowledge base of Flet Web pitfalls, routing quirks, API differences, and proven patterns."
license: Apache-2.0
metadata:
  author: "Ponce1969"
  version: "1.0"
---

# Flet Knowledge Base — Portable Bitácora

Project-agnostic Flet Web gotchas compiled from real production bugs. Copy this file to any Flet project.

## Activation Contract

Load this skill BEFORE writing any Flet routing, navigation, query parameter, or authentication code. Also load when debugging Flet Web issues where pages don't render, redirects loop, or URL parameters are lost.

## Hard Rules

1. **Always test auth flows in a REAL BROWSER (incognito).** Flet Desktop masks Web-only bugs. Never trust desktop-only testing.
2. **Never assume Flet Web APIs work like Flask/FastAPI.** Flet has its own routing model with non-obvious behaviors documented below.
3. **When deploying Flet Web changes, verify the container actually rebuilt.** Docker build timeouts can silently fail — always `docker compose exec app grep 'pattern' file.py` to confirm the fix is in the container.

## Flet Web Routing Gotchas

### 1. `page.route` INCLUDES query params

```python
# WRONG — will never match
if route in routes_dict:           # route = "/reset-password?token=abc"
    view = routes_dict[route]       # KeyError! Key is "/reset-password"

# RIGHT — strip query string before dict lookup
clean_route = route.split("?")[0]  # "/reset-password"
if clean_route in routes_dict:
    view = routes_dict[clean_route]
```

The same applies to `public_routes` lists used for auth guards:
```python
# WRONG
elif route in public_routes:          # "/reset-password?token=abc" NOT in list

# RIGHT
clean_route = route.split("?")[0]
elif clean_route in public_routes:    # "/reset-password" IS in list
```

### 2. `QueryString.get()` raises `KeyError` (not like `dict.get()`)

```python
# WRONG — crashes with KeyError if key missing
token = self.page.query.get("token")   # KeyError: 'token'

# RIGHT — handle KeyError and use fallbacks
try:
    if hasattr(self.page, "query") and self.page.query:
        token_value = self.page.query.get("token")
        if token_value:
            self.token = token_value
except (KeyError, TypeError, AttributeError):
    pass  # Query not populated yet on initial render
```

### 3. `page.query` may be empty on first render

On the initial session load in Flet Web, `page.query` can be empty even when the browser URL has query parameters. Always provide fallback parsing methods:

```python
def _extract_query_param(self, page, param_name: str) -> str | None:
    """Extract a query parameter using multiple Flet Web methods.

    Flet Web populates page.query asynchronously after the first render.
    page.route may include the query string on initial load.
    """
    # Method 1: page.query (QueryString) — may be empty on first render
    try:
        if hasattr(page, "query") and page.query:
            value = page.query.get(param_name)
            if value:
                return value
    except (KeyError, TypeError, AttributeError):
        pass

    # Method 2: parse from page.route
    route = getattr(page, "route", "")
    if route and "?" in route:
        from urllib.parse import parse_qs, urlparse
        params = parse_qs(urlparse(route).query)
        if param_name in params:
            return params[param_name][0]

    # Method 3: parse from page.url (full browser URL)
    url = getattr(page, "url", "")
    if url and "?" in url:
        from urllib.parse import parse_qs, urlparse
        params = parse_qs(urlparse(url).query)
        if param_name in params:
            return params[param_name][0]

    return None
```

### 4. `page.on_route_change` is REQUIRED for deep links

Without `page.on_route_change`, browser-initiated URL changes (deep links, back/forward) are NOT processed by your app:

```python
def main(page: ft.Page):
    router = Router(page)
    public_routes = ["/forgot-password", "/reset-password", "/register"]

    def _navigate_to_route(route: str) -> None:
        clean_route = route.split("?")[0]
        if SessionManager.is_logged_in(page):
            router.navigate("/")
        elif clean_route in public_routes:
            router.navigate(route)  # pass full route, Router strips query
        else:
            router.navigate("/login")

    def on_route_change(e: ft.RouteChangeEvent) -> None:
        _navigate_to_route(e.route)

    page.on_route_change = on_route_change

    # Initial navigation — handles deep links on page load
    _navigate_to_route(page.route or "/login")
```

## Flet Web API Reference (0.81+)

| API | Correct usage | Gotcha |
|-----|--------------|--------|
| `page.route` | Includes query string: `/path?key=val` | Must `.split("?")[0]` for route matching |
| `page.query` | `QueryString` object, `.get(key)` | Raises `KeyError`, not `None`. May be empty on first render. |
| `page.query_params` | **Does NOT exist** (was a mistake) | Use `page.query` instead |
| `page.url` | Full browser URL string | Fallback for extracting params |
| `page.on_route_change` | Required for deep links | Without it, URL changes from browser are ignored |
| `ft.AppView.WEB_BROWSER` | Required for web deployment | Desktop mode has different routing behavior |

## Flet Web Auth Flow Pattern

```python
# main.py — correct pattern for auth + public routes + deep links
async def main(page: ft.Page):
    router = Router(page)
    PUBLIC_ROUTES = ["/forgot-password", "/reset-password", "/register"]

    def _navigate_to_route(route: str) -> None:
        clean = route.split("?")[0]
        if SessionManager.is_logged_in(page):
            router.navigate("/")
        elif clean in PUBLIC_ROUTES:
            router.navigate(route)        # Router handles query stripping
        else:
            router.navigate("/login")

    page.on_route_change = lambda e: _navigate_to_route(e.route)
    _navigate_to_route(page.route or "/login")
```

## Environment Checklist for Password Reset

| Variable | Purpose | Example |
|----------|---------|---------|
| `RESEND_API_KEY` | Resend email API | `re_xxxxx` |
| `RESEND_FROM_EMAIL` | Verified sender | `app@yourdomain.com` |
| `APP_BASE_URL` | Public URL for reset links | `https://app.yourdomain.com` |

**Critical**: Docker `docker-compose.yml` `environment:` section — `.env` is NOT passed to containers by default.

## Output Contract

When this skill is loaded:
- Check all routing code against the gotchas table
- Verify `page.on_route_change` is set for any app with deep links or auth
- Ensure query param extraction uses `try/except KeyError` with fallbacks
- Verify route matching strips query strings before dict/list lookup