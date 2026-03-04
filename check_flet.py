"""
🔍 Herramienta de Diagnóstico de Flet
Inspecciona controles, métodos y atributos de Flet para debugging.

Uso:
    python check_flet.py                    # Menú interactivo
    python check_flet.py FilePicker         # Inspeccionar control específico
    python check_flet.py FilePicker.pick_files  # Inspeccionar método específico
"""
import inspect
import sys
from typing import Any

import flet as ft


def print_header(title: str, width: int = 90) -> None:
    """Imprime un encabezado formateado."""
    print("\n" + "=" * width)
    print(f"� {title}")
    print("=" * width)


def print_section(title: str) -> None:
    """Imprime un título de sección."""
    print(f"\n📋 {title}:")


def inspect_method(obj: Any, method_name: str) -> None:
    """Inspecciona un método de un objeto."""
    if not hasattr(obj, method_name):
        print(f"❌ El método '{method_name}' no existe en {type(obj).__name__}")
        return

    method = getattr(obj, method_name)
    print_header(f"ANALIZANDO {type(obj).__name__}.{method_name}()")

    # Firma del método
    try:
        sig = inspect.signature(method)
        print_section("Firma del método")
        print(f"   {method_name}{sig}")

        # Parámetros
        print_section("Parámetros")
        if sig.parameters:
            for name, param in sig.parameters.items():
                default = (
                    "Sin default"
                    if param.default == inspect.Parameter.empty
                    else f"Default: {param.default}"
                )
                annotation = (
                    ""
                    if param.annotation == inspect.Parameter.empty
                    else f": {param.annotation}"
                )
                print(f"   • {name:<20} {annotation:<30} {default}")
        else:
            print("   Sin parámetros")

        # Tipo de retorno
        print_section("Tipo de retorno")
        if sig.return_annotation != inspect.Signature.empty:
            print(f"   {sig.return_annotation}")
        else:
            print("   No especificado")

    except Exception as e:
        print(f"   ⚠️  No se pudo obtener la firma: {e}")

    # Documentación
    print_section("Documentación")
    if method.__doc__:
        print(f"   {method.__doc__.strip()}")
    else:
        print("   Sin documentación")

    # Verificar si es async
    print_section("Tipo de función")
    if inspect.iscoroutinefunction(method):
        print("   ✅ ASYNC (debe usarse con await)")
    else:
        print("   🔄 SYNC (llamada normal)")


def inspect_control(control_name: str) -> None:
    """Inspecciona un control de Flet."""
    if not hasattr(ft, control_name):
        print(f"❌ El control '{control_name}' no existe en Flet")
        return

    control_class = getattr(ft, control_name)
    print_header(f"ANALIZANDO CONTROL: {control_name}")

    # Información básica
    print_section("Información básica")
    print(f"   Tipo: {type(control_class)}")
    print(f"   Módulo: {control_class.__module__}")

    # Documentación
    print_section("Documentación")
    if control_class.__doc__:
        doc_lines = control_class.__doc__.strip().split("\n")
        for line in doc_lines[:5]:  # Primeras 5 líneas
            print(f"   {line}")
        if len(doc_lines) > 5:
            print(f"   ... ({len(doc_lines) - 5} líneas más)")
    else:
        print("   Sin documentación")

    # Métodos públicos
    print_section("Métodos públicos")
    try:
        instance = control_class()
        methods = [
            m
            for m in dir(instance)
            if not m.startswith("_") and callable(getattr(instance, m))
        ]
        if methods:
            for method in sorted(methods)[:10]:  # Primeros 10
                is_async = inspect.iscoroutinefunction(getattr(instance, method))
                async_marker = "ASYNC" if is_async else "SYNC "
                print(f"   • {method:<30} [{async_marker}]")
            if len(methods) > 10:
                print(f"   ... ({len(methods) - 10} métodos más)")
        else:
            print("   Sin métodos públicos")
    except Exception as e:
        print(f"   ⚠️  No se pudo instanciar: {e}")

    # Propiedades/Atributos
    print_section("Propiedades principales")
    try:
        instance = control_class()
        attrs = [
            a
            for a in dir(instance)
            if not a.startswith("_") and not callable(getattr(instance, a))
        ]
        if attrs:
            for attr in sorted(attrs)[:10]:  # Primeros 10
                try:
                    value = getattr(instance, attr)
                    value_type = type(value).__name__
                    print(f"   • {attr:<30} {value_type}")
                except Exception:
                    print(f"   • {attr:<30} (no accesible)")
            if len(attrs) > 10:
                print(f"   ... ({len(attrs) - 10} atributos más)")
        else:
            print("   Sin atributos públicos")
    except Exception as e:
        print(f"   ⚠️  No se pudo inspeccionar: {e}")


def show_menu() -> None:
    """Muestra el menú interactivo."""
    print_header("HERRAMIENTA DE DIAGNÓSTICO DE FLET")
    print("\n📚 Opciones disponibles:")
    print("   1. Inspeccionar FilePicker")
    print("   2. Inspeccionar FilePicker.pick_files")
    print("   3. Inspeccionar FileUpload")
    print("   4. Inspeccionar Page")
    print("   5. Listar todos los controles de Flet")
    print("   6. Inspeccionar control personalizado")
    print("   0. Salir")
    print("\n" + "=" * 90)


def list_flet_controls() -> None:
    """Lista todos los controles disponibles en Flet."""
    print_header("CONTROLES DISPONIBLES EN FLET")

    controls = [
        name
        for name in dir(ft)
        if not name.startswith("_")
        and inspect.isclass(getattr(ft, name))
        and name[0].isupper()
    ]

    print(f"\n📦 Total de controles: {len(controls)}\n")

    # Agrupar por categoría (primera letra)
    from collections import defaultdict

    grouped = defaultdict(list)
    for control in sorted(controls):
        grouped[control[0]].append(control)

    for letter, items in sorted(grouped.items()):
        print(f"\n{letter}:")
        for item in items:
            print(f"   • {item}")


def main() -> None:
    """Función principal."""
    if len(sys.argv) > 1:
        # Modo comando directo
        arg = sys.argv[1]
        if "." in arg:
            # Formato: Control.metodo
            control_name, method_name = arg.split(".", 1)
            if hasattr(ft, control_name):
                control_class = getattr(ft, control_name)
                try:
                    instance = control_class()
                    inspect_method(instance, method_name)
                except Exception as e:
                    print(f"❌ Error al instanciar {control_name}: {e}")
            else:
                print(f"❌ Control '{control_name}' no encontrado")
        else:
            # Solo control
            inspect_control(arg)
        return

    # Modo interactivo
    while True:
        show_menu()
        choice = input("\n👉 Selecciona una opción: ").strip()

        if choice == "0":
            print("\n👋 ¡Hasta luego!")
            break
        elif choice == "1":
            inspect_control("FilePicker")
        elif choice == "2":
            picker = ft.FilePicker()
            inspect_method(picker, "pick_files")
        elif choice == "3":
            inspect_control("FileUpload")
        elif choice == "4":
            inspect_control("Page")
        elif choice == "5":
            list_flet_controls()
        elif choice == "6":
            control_name = input("\n📝 Nombre del control: ").strip()
            if control_name:
                inspect_control(control_name)
        else:
            print("\n❌ Opción inválida")

        input("\n⏎ Presiona Enter para continuar...")


if __name__ == "__main__":
    main()
