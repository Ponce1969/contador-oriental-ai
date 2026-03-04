# 🔍 check_flet.py - Herramienta de Diagnóstico de Flet

## 📋 Descripción

`check_flet.py` es una herramienta de diagnóstico interactiva para inspeccionar controles, métodos y atributos de Flet. Útil para debugging, exploración de la API y resolución de problemas.

## 🚀 Uso

### Modo Interactivo (Menú)

```bash
python check_flet.py
```

Muestra un menú con opciones predefinidas:
- Inspeccionar FilePicker
- Inspeccionar FilePicker.pick_files
- Inspeccionar FileUpload
- Inspeccionar Page
- Listar todos los controles
- Inspeccionar control personalizado

### Modo Comando Directo

```bash
# Inspeccionar un control
python check_flet.py FilePicker

# Inspeccionar un método específico
python check_flet.py FilePicker.pick_files

# Otros ejemplos
python check_flet.py TextField
python check_flet.py Page.add
python check_flet.py ElevatedButton.on_click
```

## 📊 Información que Proporciona

### Para Controles:

- ✅ Tipo y módulo
- ✅ Documentación
- ✅ Métodos públicos (SYNC/ASYNC)
- ✅ Propiedades y atributos
- ✅ Tipos de datos

### Para Métodos:

- ✅ Firma completa
- ✅ Parámetros con tipos y defaults
- ✅ Tipo de retorno
- ✅ Documentación
- ✅ Si es SYNC o ASYNC

## 💡 Ejemplos de Uso

### Ejemplo 1: Investigar FilePicker

```bash
$ python check_flet.py FilePicker

🔍 ANALIZANDO CONTROL: FilePicker
================================================================================

📋 Información básica:
   Tipo: <class 'type'>
   Módulo: flet.core.file_picker

📋 Documentación:
   A control that allows you to use the native file explorer...

📋 Métodos públicos:
   • get_directory_path          [ASYNC]
   • pick_files                  [ASYNC]
   • save_file                   [ASYNC]
   • upload                      [SYNC ]
   ...

📋 Propiedades principales:
   • allowed_extensions          list
   • dialog_title                str
   • file_name                   str
   • file_type                   FilePickerFileType
   ...
```

### Ejemplo 2: Verificar si un método es async

```bash
$ python check_flet.py FilePicker.pick_files

🔍 ANALIZANDO FilePicker.pick_files()
================================================================================

📋 Firma del método:
   pick_files(self, dialog_title=None, ...)

📋 Parámetros:
   • dialog_title               : str | None              Default: None
   • allowed_extensions         : list[str] | None        Default: None
   • allow_multiple             : bool                    Default: False

📋 Tipo de retorno:
   Coroutine[Any, Any, list[FilePickerFile]]

📋 Tipo de función:
   ✅ ASYNC (debe usarse con await)
```

### Ejemplo 3: Listar todos los controles

```bash
$ python check_flet.py

# Seleccionar opción 5
📦 Total de controles: 150+

A:
   • AlertDialog
   • AnimatedSwitcher
   • AppBar
   ...

B:
   • Banner
   • BottomAppBar
   • BottomSheet
   ...
```

## 🎯 Casos de Uso Reales

### 1. Debugging del FilePicker

**Problema:** FilePicker no funciona en web

```bash
$ python check_flet.py FilePicker.pick_files

# Resultado:
📋 Tipo de función:
   ✅ ASYNC (debe usarse con await)
```

**Solución:** Usar `await picker.pick_files()` en lugar de `picker.pick_files()`

### 2. Explorar alternativas

**Problema:** Necesito subir archivos en web

```bash
$ python check_flet.py FileUpload

# Resultado:
📋 Métodos públicos:
   • upload                      [SYNC ]
   
📋 Propiedades principales:
   • upload_url                  str
   • on_upload                   callable
```

**Solución:** Usar FileUpload con un endpoint HTTP

### 3. Verificar parámetros de un método

**Problema:** No sé qué parámetros acepta `pick_files`

```bash
$ python check_flet.py FilePicker.pick_files

# Resultado:
📋 Parámetros:
   • dialog_title               : str | None              Default: None
   • allowed_extensions         : list[str] | None        Default: None
   • allow_multiple             : bool                    Default: False
   • initial_directory          : str | None              Default: None
```

**Solución:** Ahora sé exactamente qué parámetros usar

## 🔧 Personalización

### Agregar nuevas opciones al menú

Edita la función `show_menu()` en `check_flet.py`:

```python
def show_menu() -> None:
    print("\n📚 Opciones disponibles:")
    print("   1. Inspeccionar FilePicker")
    print("   2. Inspeccionar FilePicker.pick_files")
    # ... agregar más opciones
    print("   7. Inspeccionar mi control personalizado")
```

### Inspeccionar controles personalizados

Si tienes controles personalizados en tu proyecto:

```python
# En check_flet.py, agregar al inicio:
import sys
sys.path.append("./views/components")
from mi_control import MiControl

# Luego usar:
inspect_control("MiControl")
```

## 📚 Referencia Rápida

### Comandos Útiles

```bash
# Controles comunes
python check_flet.py TextField
python check_flet.py ElevatedButton
python check_flet.py Container
python check_flet.py Row
python check_flet.py Column

# Métodos comunes
python check_flet.py Page.add
python check_flet.py Page.update
python check_flet.py TextField.focus

# File pickers
python check_flet.py FilePicker
python check_flet.py FilePicker.pick_files
python check_flet.py FileUpload
python check_flet.py FileUpload.upload

# Navegación
python check_flet.py Page.go
python check_flet.py Page.route
```

## 🐛 Troubleshooting

### Error: ModuleNotFoundError: No module named 'flet'

```bash
# Instalar Flet
pip install flet
# o
uv pip install flet
```

### Error: Control no encontrado

```bash
# Verificar que el nombre esté correcto (case-sensitive)
python check_flet.py FilePicker  # ✅ Correcto
python check_flet.py filepicker  # ❌ Incorrecto
```

### No se puede instanciar el control

Algunos controles requieren parámetros obligatorios. El script mostrará un warning pero seguirá funcionando.

## 💡 Tips

1. **Usa el modo comando directo** para scripts y automatización
2. **Usa el modo interactivo** para exploración y aprendizaje
3. **Combina con la documentación oficial** de Flet para mejor comprensión
4. **Guarda la salida** para referencia futura: `python check_flet.py FilePicker > filepicker_info.txt`

## 🎓 Casos de Uso Avanzados

### Script de validación

```bash
#!/bin/bash
# Verificar que todos los controles usados existen

for control in FilePicker FileUpload TextField ElevatedButton; do
    echo "Verificando $control..."
    python check_flet.py $control > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "  ✅ $control existe"
    else
        echo "  ❌ $control no encontrado"
    fi
done
```

### Generar documentación

```bash
# Generar documentación de todos los controles usados
for control in $(grep -r "ft\." views/ | grep -oP "ft\.\K[A-Z]\w+" | sort -u); do
    echo "## $control" >> CONTROLES_USADOS.md
    python check_flet.py $control >> CONTROLES_USADOS.md
    echo "" >> CONTROLES_USADOS.md
done
```

## 🔗 Referencias

- [Documentación oficial de Flet](https://flet.dev/docs/)
- [Flet Controls Reference](https://flet.dev/docs/controls/)
- [Python inspect module](https://docs.python.org/3/library/inspect.html)

---

**Versión:** 2.0.0  
**Última actualización:** 2026-03-03  
**Autor:** Herramienta de diagnóstico mejorada
