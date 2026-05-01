class AppState:
    device = None  # mobile | tablet | desktop
    initial_device = "mobile"
    language = "pt"
    initialized = False
    current_route = "/"
    file_picker = None  # ft.FilePicker registrado al inicio de la sesion
    prefilled_question: str | None = None  # Pregunta pre-cargada desde otra vista
    from_history: bool = False  # True si la pregunta viene del botón de Historial
