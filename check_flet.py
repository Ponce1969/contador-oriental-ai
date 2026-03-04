"""
Herramienta de Diagnostico de Flet para Contador Oriental.

Inspecciona controles, metodos y compatibilidad de Flet.
Incluye diagnosticos especificos para problemas conocidos del proyecto.

Uso:
    python check_flet.py                        # Menu interactivo
    python check_flet.py --version              # Version y entorno
    python check_flet.py --compat               # Reporte de compatibilidad del proyecto
    python check_flet.py FilePicker             # Inspeccionar control
    python check_flet.py FilePicker.pick_files  # Inspeccionar metodo
    python check_flet.py --search overlay       # Buscar en API de Flet
    python check_flet.py --all                  # Listar todos los controles

En Docker:
    docker exec auditor_familiar_app python check_flet.py --compat
"""
from __future__ import annotations

import importlib
import inspect
import os
import platform
import sys
from collections import defaultdict
from typing import Any

import flet as ft

W = 88  # ancho de linea


# ---------------------------------------------------------------------------
# Helpers de presentacion
# ---------------------------------------------------------------------------

def hr(char: str = "=") -> None:
    print(char * W)


def header(title: str) -> None:
    print()
    hr()
    print(f"  {title}")
    hr()


def section(title: str) -> None:
    print(f"\n  -- {title} --")


def ok(msg: str) -> None:
    print(f"  [OK]  {msg}")


def warn(msg: str) -> None:
    print(f"  [!!]  {msg}")


def err(msg: str) -> None:
    print(f"  [XX]  {msg}")


def info(msg: str) -> None:
    print(f"        {msg}")


# ---------------------------------------------------------------------------
# Version y entorno
# ---------------------------------------------------------------------------

def show_version() -> None:
    header("ENTORNO Y VERSION")

    section("Python")
    info(f"Version : {platform.python_version()}")
    info(f"Impl    : {platform.python_implementation()}")
    info(f"OS      : {platform.system()} {platform.release()}")
    info(f"Docker  : {'si' if os.path.exists('/.dockerenv') else 'no'}")

    section("Flet")
    flet_version = getattr(ft, "__version__", "desconocida")
    info(f"Version : {flet_version}")
    info(f"Modulo  : {ft.__file__}")

    section("Paquetes relevantes")
    for pkg in ["httpx", "pytesseract", "PIL", "pydantic", "sqlalchemy", "result"]:
        try:
            mod = importlib.import_module(pkg if pkg != "PIL" else "PIL.Image")
            ver = getattr(mod, "__version__", "?")
            ok(f"{pkg:<15} {ver}")
        except ImportError:
            warn(f"{pkg:<15} NO INSTALADO")


# ---------------------------------------------------------------------------
# Reporte de compatibilidad del proyecto
# ---------------------------------------------------------------------------

def check_compat() -> None:
    """Verifica compatibilidad de la API de Flet con lo que usa el proyecto."""
    header("REPORTE DE COMPATIBILIDAD — CONTADOR ORIENTAL")

    issues: list[str] = []
    oks: list[str] = []

    # --- FilePicker ---
    section("FilePicker")
    if hasattr(ft, "FilePicker"):
        ok("ft.FilePicker existe")
        picker = ft.FilePicker()

        # pick_files async
        if hasattr(picker, "pick_files"):
            pf = picker.pick_files
            if inspect.iscoroutinefunction(pf):
                ok("pick_files() es ASYNC (API 0.81+)")
                oks.append("FilePicker.pick_files es async")
            else:
                warn("pick_files() es SYNC — API pre-0.81 (usa on_result callback)")
                issues.append("FilePicker.pick_files es SYNC — necesita on_result")

            # with_data param
            sig = inspect.signature(pf)
            if "with_data" in sig.parameters:
                ok("pick_files() tiene parametro with_data=True (leer bytes en web)")
                oks.append("FilePicker.pick_files tiene with_data")
            else:
                warn("pick_files() NO tiene with_data — no puede leer bytes en web")
                issues.append("FilePicker.pick_files sin with_data")
        else:
            err("pick_files() NO existe")
            issues.append("FilePicker sin pick_files()")

        # upload method
        if hasattr(picker, "upload"):
            ok("FilePicker.upload() existe (alternativa para web)")
        else:
            warn("FilePicker.upload() no existe en esta version")

    else:
        err("ft.FilePicker NO existe")
        issues.append("ft.FilePicker no existe")

    # --- Page.overlay ---
    section("Page.overlay")
    if hasattr(ft.Page, "overlay"):
        ok("page.overlay existe")
        oks.append("page.overlay existe")
    else:
        err("page.overlay NO existe — no se pueden agregar FilePicker ni SnackBar")
        issues.append("page.overlay no existe")

    # --- Page.run_javascript ---
    section("Page JavaScript")
    has_js = False
    for js_method in ("run_javascript", "eval_javascript", "invoke_method"):
        if hasattr(ft.Page, js_method):
            ok(f"page.{js_method}() existe")
            has_js = True
    if not has_js:
        warn("page no tiene metodos JavaScript — no se puede usar fetch nativo")
        issues.append("page sin metodos JavaScript (run_javascript/eval_javascript)")

    # --- ElevatedButton icon= y text= ---
    section("ElevatedButton API")
    try:
        sig = inspect.signature(ft.ElevatedButton.__init__)
        params = list(sig.parameters.keys())
        if "icon" in params:
            warn("ElevatedButton acepta icon= (API pre-0.81)")
            issues.append("ElevatedButton.icon= existe (puede funcionar diferente en 0.81)")
        else:
            ok("ElevatedButton NO tiene icon= — usar content=ft.Row([ft.Icon(), ft.Text()])")
            oks.append("ElevatedButton sin icon= confirmado")
        if "text" in params:
            warn("ElevatedButton acepta text= (API pre-0.81)")
        else:
            ok("ElevatedButton NO tiene text= — pasar ft.Text como content")
    except Exception as e:
        warn(f"No se pudo inspeccionar ElevatedButton: {e}")

    # --- ft.alignment vs ft.Alignment ---
    section("Alignment API")
    if hasattr(ft, "alignment") and hasattr(ft.alignment, "center"):
        warn("ft.alignment.center existe (API pre-0.81) — usar ft.Alignment(0,0)")
        issues.append("ft.alignment.center disponible — posible confusion con ft.Alignment()")
    if hasattr(ft, "Alignment"):
        ok("ft.Alignment(x, y) existe (API 0.81+)")
        oks.append("ft.Alignment existe")

    # --- launch_url / UrlLauncher ---
    section("URL Launcher")
    if hasattr(ft, "UrlLauncher"):
        ok("ft.UrlLauncher existe (Service — necesita estar en page.overlay/services)")
        oks.append("ft.UrlLauncher existe")
    if hasattr(ft.Page, "launch_url"):
        import inspect as _inspect
        src = _inspect.getsource(ft.Page.launch_url)
        if "deprecated" in src.lower():
            warn("page.launch_url() esta DEPRECADO en esta version")
            issues.append("page.launch_url() deprecado — usar ft.UrlLauncher Service")
        else:
            ok("page.launch_url() existe y no esta deprecado")
    else:
        warn("page.launch_url() no existe")

    # --- SnackBar via overlay ---
    section("SnackBar")
    if hasattr(ft, "SnackBar"):
        ok("ft.SnackBar existe")
        snack = ft.SnackBar(ft.Text("test"))
        if hasattr(snack, "open"):
            ok("SnackBar.open existe — usar page.overlay.append(SnackBar(open=True))")
        else:
            warn("SnackBar.open no existe — API diferente")
    if hasattr(ft.Page, "snack_bar"):
        warn("page.snack_bar existe (API pre-0.81) — usar page.overlay.append()")
        issues.append("page.snack_bar existe — migracion pendiente")

    # --- Resumen ---
    section("RESUMEN")
    print(f"\n  OK    : {len(oks)} verificaciones pasadas")
    print(f"  Issues: {len(issues)} problemas encontrados\n")
    if issues:
        print("  Problemas:")
        for i, issue in enumerate(issues, 1):
            print(f"    {i}. {issue}")
    else:
        ok("Sin problemas de compatibilidad detectados")


# ---------------------------------------------------------------------------
# Inspeccion de metodo
# ---------------------------------------------------------------------------

def inspect_method(obj: Any, method_name: str) -> None:
    if not hasattr(obj, method_name):
        err(f"El metodo '{method_name}' no existe en {type(obj).__name__}")
        return

    method = getattr(obj, method_name)
    header(f"METODO: {type(obj).__name__}.{method_name}()")

    try:
        sig = inspect.signature(method)
        section("Firma")
        print(f"  {method_name}{sig}")

        section("Parametros")
        if sig.parameters:
            for name, param in sig.parameters.items():
                default = (
                    "requerido"
                    if param.default == inspect.Parameter.empty
                    else repr(param.default)
                )
                ann = (
                    ""
                    if param.annotation == inspect.Parameter.empty
                    else f"  tipo: {param.annotation}"
                )
                print(f"  • {name:<22} default={default:<20}{ann}")
        else:
            info("Sin parametros")

        section("Retorno")
        if sig.return_annotation != inspect.Signature.empty:
            info(str(sig.return_annotation))
        else:
            info("No especificado")

    except Exception as e:
        warn(f"No se pudo obtener la firma: {e}")

    section("Async")
    if inspect.iscoroutinefunction(method):
        ok("ASYNC — usar con: await o asyncio.create_task()")
    else:
        info("SYNC — llamada normal")

    section("Codigo fuente")
    try:
        src_lines, start = inspect.getsourcelines(method)
        print(f"  Linea {start} en {inspect.getfile(method)}")
        for line in src_lines[:20]:
            print(f"  {line}", end="")
        if len(src_lines) > 20:
            print(f"\n  ... ({len(src_lines) - 20} lineas mas)")
    except Exception as e:
        warn(f"No se pudo obtener codigo: {e}")

    section("Documentacion")
    if method.__doc__:
        for line in method.__doc__.strip().split("\n")[:8]:
            info(line)
    else:
        info("Sin documentacion")


# ---------------------------------------------------------------------------
# Inspeccion de control
# ---------------------------------------------------------------------------

def inspect_control(control_name: str) -> None:
    if not hasattr(ft, control_name):
        err(f"'{control_name}' no existe en ft")
        _suggest_similar(control_name)
        return

    cls = getattr(ft, control_name)
    header(f"CONTROL: {control_name}")

    section("Informacion basica")
    info(f"Tipo   : {type(cls).__name__}")
    info(f"Modulo : {cls.__module__}")
    mro = [c.__name__ for c in cls.__mro__ if c.__name__ not in ("object",)]
    info(f"MRO    : {' -> '.join(mro)}")

    section("Constructor __init__")
    try:
        sig = inspect.signature(cls.__init__)
        params = [
            p for p in sig.parameters.values()
            if p.name not in ("self", "args", "kwargs")
        ]
        if params:
            for p in params:
                default = (
                    "requerido"
                    if p.default == inspect.Parameter.empty
                    else repr(p.default)
                )
                ann = (
                    ""
                    if p.annotation == inspect.Parameter.empty
                    else f"  tipo: {p.annotation}"
                )
                print(f"  • {p.name:<22} default={default:<20}{ann}")
        else:
            info("Sin parametros adicionales")
    except Exception as e:
        warn(f"No se pudo inspeccionar constructor: {e}")

    section("Metodos publicos")
    try:
        instance = cls()
        methods = sorted(
            m for m in dir(instance)
            if not m.startswith("_") and callable(getattr(instance, m))
        )
        for m in methods:
            is_async = inspect.iscoroutinefunction(getattr(instance, m))
            tag = "ASYNC" if is_async else "sync "
            print(f"  • {m:<35} [{tag}]")
        if not methods:
            info("Sin metodos publicos")
    except Exception as e:
        warn(f"No se pudo instanciar para metodos: {e}")

    section("Atributos publicos")
    try:
        instance = cls()
        attrs = sorted(
            a for a in dir(instance)
            if not a.startswith("_") and not callable(getattr(instance, a))
        )
        for a in attrs:
            try:
                val = getattr(instance, a)
                print(f"  • {a:<35} {type(val).__name__} = {repr(val)[:40]}")
            except Exception:
                print(f"  • {a:<35} (no accesible)")
        if not attrs:
            info("Sin atributos publicos")
    except Exception as e:
        warn(f"No se pudo instanciar para atributos: {e}")

    section("Documentacion")
    if cls.__doc__:
        for line in cls.__doc__.strip().split("\n")[:6]:
            info(line)
    else:
        info("Sin documentacion")


# ---------------------------------------------------------------------------
# Busqueda en la API
# ---------------------------------------------------------------------------

def search_api(keyword: str) -> None:
    header(f"BUSQUEDA: '{keyword}'")
    keyword_lower = keyword.lower()

    matches: list[tuple[str, str]] = []
    for name in sorted(dir(ft)):
        if keyword_lower in name.lower():
            obj = getattr(ft, name)
            kind = "clase" if inspect.isclass(obj) else "funcion" if callable(obj) else "valor"
            matches.append((name, kind))

    if matches:
        print(f"\n  {len(matches)} resultados:\n")
        for name, kind in matches:
            print(f"  • ft.{name:<35} [{kind}]")
    else:
        info(f"Sin resultados para '{keyword}'")
        _suggest_similar(keyword)


def _suggest_similar(name: str) -> None:
    all_names = [n for n in dir(ft) if not n.startswith("_")]
    similar = [n for n in all_names if name.lower()[:4] in n.lower()]
    if similar:
        info(f"Similares: {', '.join(similar[:8])}")


# ---------------------------------------------------------------------------
# Listado de controles
# ---------------------------------------------------------------------------

def list_all_controls() -> None:
    header("TODOS LOS CONTROLES DE FLET")

    controls = sorted(
        name for name in dir(ft)
        if not name.startswith("_")
        and inspect.isclass(getattr(ft, name))
        and name[0].isupper()
    )

    print(f"\n  Total: {len(controls)} clases\n")

    grouped: dict[str, list[str]] = defaultdict(list)
    for c in controls:
        grouped[c[0]].append(c)

    for letter in sorted(grouped):
        print(f"\n  {letter}:")
        for item in grouped[letter]:
            print(f"    • {item}")


# ---------------------------------------------------------------------------
# Menu interactivo
# ---------------------------------------------------------------------------

def guia_montaje(objeto_o_clase: Any) -> None:
    """Tabla de guia de montaje deducida por tipo (estilo autor Fleting)."""
    version = getattr(ft, "__version__", "?")
    nombre = getattr(objeto_o_clase, "__name__", type(objeto_o_clase).__name__)
    header(f"GUIA DE MONTAJE: {nombre}  (Flet {version})")

    # Constructor
    print(f"\n  Como crear {nombre}:")
    try:
        sig = inspect.signature(objeto_o_clase.__init__)
        for pname, param in sig.parameters.items():
            if pname == "self":
                continue
            req = (
                "[OBLIGATORIO]"
                if param.default is inspect.Parameter.empty
                else f"[Opcional: {param.default!r}]"
            )
            print(f"    • {pname:<20} {req}")
    except Exception:
        pass

    # Tabla de deduccion
    print()
    hr("-")
    print(f"  {'TIPO':<8} | {'METODO/ATTR':<22} | INSTRUCCION DE MONTAJE")
    hr("-")

    obj_nom = nombre.lower()
    for attr in sorted(dir(objeto_o_clase)):
        if attr.startswith("_"):
            continue
        try:
            val = getattr(objeto_o_clase, attr)
            if inspect.iscoroutinefunction(val):
                tipo = "ASYNC"
                guia = f"result = await {obj_nom}.{attr}()  # pausa y retorna dato"
            elif callable(val):
                if attr.startswith("on_"):
                    tipo = "EVENT"
                    guia = f"{obj_nom}.{attr} = mi_funcion  # se activa al ocurrir algo"
                else:
                    tipo = "METHOD"
                    guia = f"{obj_nom}.{attr}()  # accion inmediata sin espera"
            else:
                tipo = "ATTR"
                guia = f"{obj_nom}.{attr} = valor  # cambia propiedad"
            print(f"  {tipo:<8} | {attr:<22} | {guia}")
        except Exception:
            continue

    hr("-")
    print("  TIP: ASYNC  -> usar con await o asyncio.create_task()")
    print("  TIP: EVENT  -> la funcion recibe un objeto 'e' (evento)")
    print("  TIP: METHOD -> llamada normal, retorna inmediatamente")


def show_menu() -> None:
    header("DIAGNOSTICO FLET — CONTADOR ORIENTAL")
    flet_ver = getattr(ft, "__version__", "?")
    info(f"Flet {flet_ver} | Python {platform.python_version()}")
    print()
    print("  1  Entorno y version")
    print("  2  Reporte compatibilidad del proyecto  [RECOMENDADO]")
    print("  3  Inspeccionar FilePicker")
    print("  4  Inspeccionar FilePicker.pick_files")
    print("  5  Inspeccionar Page")
    print("  6  Listar todos los controles")
    print("  7  Buscar en la API de Flet")
    print("  8  Inspeccionar control/metodo personalizado")
    print("  9  Guia de montaje (tabla tipo/metodo/instruccion)")
    print("  0  Salir")
    print()
    hr("-")


def main() -> None:
    args = sys.argv[1:]

    # Flags directos
    if "--version" in args:
        show_version()
        return
    if "--compat" in args:
        show_version()
        check_compat()
        return
    if "--all" in args:
        list_all_controls()
        return
    if "--search" in args:
        idx = args.index("--search")
        if idx + 1 < len(args):
            search_api(args[idx + 1])
        else:
            err("--search requiere un termino: python check_flet.py --search overlay")
        return

    # Control.metodo o Control
    if args and not args[0].startswith("--"):
        arg = args[0]
        if "." in arg:
            control_name, method_name = arg.split(".", 1)
            if hasattr(ft, control_name):
                try:
                    instance = getattr(ft, control_name)()
                    inspect_method(instance, method_name)
                except Exception as e:
                    err(f"No se pudo instanciar {control_name}: {e}")
            else:
                err(f"Control '{control_name}' no encontrado")
                _suggest_similar(control_name)
        else:
            inspect_control(arg)
        return

    # Menu interactivo
    while True:
        show_menu()
        choice = input("  Opcion: ").strip()

        if choice == "0":
            print("\n  Hasta luego.\n")
            break
        elif choice == "1":
            show_version()
        elif choice == "2":
            show_version()
            check_compat()
        elif choice == "3":
            inspect_control("FilePicker")
        elif choice == "4":
            picker = ft.FilePicker()
            inspect_method(picker, "pick_files")
        elif choice == "5":
            inspect_control("Page")
        elif choice == "6":
            list_all_controls()
        elif choice == "7":
            kw = input("  Termino de busqueda: ").strip()
            if kw:
                search_api(kw)
        elif choice == "8":
            target = input("  Control o Control.metodo: ").strip()
            if "." in target:
                cname, mname = target.split(".", 1)
                if hasattr(ft, cname):
                    try:
                        inspect_method(getattr(ft, cname)(), mname)
                    except Exception as e:
                        err(f"Error: {e}")
                else:
                    err(f"'{cname}' no existe")
            elif target:
                inspect_control(target)
        elif choice == "9":
            cname = input("  Control para guia de montaje [FilePicker]: ").strip()
            cname = cname or "FilePicker"
            if hasattr(ft, cname):
                guia_montaje(getattr(ft, cname))
            else:
                err(f"'{cname}' no existe")
                _suggest_similar(cname)
        else:
            warn("Opcion invalida")

        input("\n  [Enter para continuar]")


if __name__ == "__main__":
    main()
