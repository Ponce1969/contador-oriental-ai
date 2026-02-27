
# configs/app_config.py
import os

import flet as ft


class ScreenConfig:
    MOBILE = {
        "width": 390,
        "height": 758,
        "max_content_width": 390,
    }

    TABLET = {
        "width": 768,
        "height": 1024,
        "max_content_width": 768,
    }

    DESKTOP = {
        "width": 1280,
        "height": 800,
        "max_content_width": None,  # no limit
    }

class AppConfig:
    APP_NAME = "{project_name}"
    DEFAULT_SCREEN = ScreenConfig.MOBILE
    THEME_MODE = ft.ThemeMode.LIGHT

    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    MEMORY_SERVICE_ENABLED = os.getenv("MEMORY_SERVICE_ENABLED", "true").lower() == "true"
