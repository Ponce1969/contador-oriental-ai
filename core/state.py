
class AppState:
    device = None  # mobile | tablet | desktop
    initial_device = "mobile"
    language = "pt"
    initialized = False
    current_route = "/"
    file_picker = None  # ft.FilePicker registrado al inicio de la sesion
