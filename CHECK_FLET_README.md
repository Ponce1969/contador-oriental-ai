# 🔍 check_flet.py — Herramienta de Diagnóstico para Flet 0.81

## Descripción

`check_flet.py` es una herramienta de diagnóstico para inspeccionar la API de Flet,
verificar compatibilidad del proyecto y detectar problemas conocidos en Flet 0.81 web.
Combina inspección estática con diagnósticos específicos del proyecto Contador Oriental.

## Uso rápido

```bash
# Reporte de compatibilidad del proyecto (RECOMENDADO)
python check_flet.py --compat

# Versión y paquetes instalados
python check_flet.py --version

# Buscar en la API de Flet
python check_flet.py --search upload

# Inspeccionar un control o método
python check_flet.py FilePicker
python check_flet.py FilePicker.pick_files
python check_flet.py UrlLauncher

# Listar todos los controles disponibles
python check_flet.py --all

# Menú interactivo
python check_flet.py
```

## Desde Docker (Flet real en producción)

```bash
docker cp check_flet.py auditor_familiar_app:/app/check_flet.py
docker exec auditor_familiar_app python /app/check_flet.py --compat
docker exec auditor_familiar_app python /app/check_flet.py FilePicker.pick_files
```

## Menú interactivo (9 opciones)

```
  1  Entorno y version
  2  Reporte compatibilidad del proyecto  [RECOMENDADO]
  3  Inspeccionar FilePicker
  4  Inspeccionar FilePicker.pick_files
  5  Inspeccionar Page
  6  Listar todos los controles
  7  Buscar en la API de Flet
  8  Inspeccionar control/metodo personalizado
  9  Guia de montaje (tabla tipo/metodo/instruccion)
  0  Salir
```

## Qué muestra `--compat` (Flet 0.81 Docker)

```
FilePicker
  [OK]  ft.FilePicker existe
  [OK]  pick_files() es ASYNC
  [OK]  with_data=True disponible
  [OK]  FilePicker.upload() existe

Page.overlay
  [OK]  page.overlay existe

URL Launcher
  [OK]  ft.UrlLauncher existe (Service — necesita overlay)
  [!!]  page.launch_url() DEPRECADO — usar ft.UrlLauncher

Page JavaScript
  [!!]  page sin metodos JavaScript

ElevatedButton
  [!!]  ElevatedButton.icon= existe (pre-0.81)
  [OK]  ElevatedButton sin text= — usar content=ft.Text(...)

Alignment
  [OK]  ft.Alignment(x, y) existe (0.81+)

SnackBar
  [OK]  ft.SnackBar existe
  [OK]  SnackBar.open — usar page.overlay.append(SnackBar(open=True))
```

## Hallazgos confirmados en Flet 0.81 web

| Control/Método | Estado | Nota |
|---|---|---|
| `ft.FilePicker` | ❌ No funciona en web | "Unknown control" / TimeoutException |
| `ft.UrlLauncher` | ❌ No funciona en web | Mismo problema que FilePicker |
| `page.launch_url()` | ⚠️ Deprecado | Llama a UrlLauncher internamente |
| `page.run_javascript()` | ❌ No existe | No hay acceso al DOM desde Python |
| `ft.Alignment(x, y)` | ✅ Correcto en 0.81 | Reemplaza `ft.alignment.center` |
| `ElevatedButton(text=)` | ❌ No existe | Usar `content=ft.Text(...)` |
| `page.overlay.append()` | ✅ Funciona | Para SnackBar, Dialogs |

## Opción 9 — Guía de montaje

Dado cualquier control, genera una tabla con:

```
TIPO     | METODO/ATTR            | INSTRUCCION DE MONTAJE
ASYNC    | pick_files             | result = await filepicker.pick_files()
EVENT    | on_result              | filepicker.on_result = mi_funcion
METHOD   | upload                 | filepicker.upload()
ATTR     | allowed_extensions     | filepicker.allowed_extensions = valor
```

## Referencias

- [Flet 0.81 Changelog](https://flet.dev/blog/)
- [Flet Controls Reference](https://flet.dev/docs/controls/)
- [Python inspect module](https://docs.python.org/3/library/inspect.html)

---

**Última actualización:** 2026-03-04 | Flet 0.81.0 | Python 3.12
