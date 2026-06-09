# Resumen de Correcciones - Contador Oriental

## Fecha: 2026-06-09

### 1. Corrección de Corrupción Monetaria en expenses_view.py

**Problema:** El método `_on_edit_expense` usaba `str(expense.monto).rstrip("0").rstrip(".")` que corrompía valores enteros como 1000 transformándolos en "1".

**Solución:** Implementado formateo seguro de Decimal:
```python
monto_str = f"{expense.monto:f}"
if '.' in monto_str:
    monto_str = monto_str.rstrip('0').rstrip('.')
```

**Resultado:**
- Decimal("1000") → "1000" ✓
- Decimal("1500.50") → "1500.5" ✓
- Decimal("1000.00") → "1000" ✓

---

### 2. Corrección de Tipos en ai_model.py

**Problema:** Los métodos `variacion_total_pct` y `variacion_ticket_pct` estaban declarados para retornar `float | None` pero en realidad retornaban `Decimal`.

**Solución:** Cambiadas las anotaciones de tipo:
```python
@property
def variacion_total_pct(self) -> Decimal | None:
    ...

@property  
def variacion_ticket_pct(self) -> Decimal | None:
    ...
```

**Resultado:** Tipos ahora son consistentes con el valor real retornado.

---

### 3. Corrección de Inyección SQL en expense_repository.py

**Problema:** El método `buscar_por_similitud` construía SQL mediante concatenación de strings:
```python
sql = text(str(sql) + " AND fecha >= :fecha_min")
```
Esto rompía el parameter binding de SQLAlchemy.

**Solución:** Construcción segura de SQL con lista de partes:
```python
sql_parts = ["SELECT ... WHERE ..."]
params = {...}

if fecha_min is not None:
    sql_parts.append("AND fecha >= :fecha_min")
    params["fecha_min"] = fecha_min

sql_string = " ".join(sql_parts)
sql = text(sql_string)
```

**Resultado:** Parameter binding funciona correctamente, sin riesgo de inyección SQL.

---

### 4. Corrección de Bypass de Seguridad en base_repository.py

**Problema:** El filtro por familia usaba `if self.familia_id` que es `False` cuando `familia_id == 0`, permitiendo bypass del aislamiento de datos.

**Solución:** Cambiadas 4 ocurrencias de:
```python
if self.familia_id and hasattr(self.model, "family_id"):
```
a:
```python
if self.familia_id is not None and hasattr(self.model, "family_id"):
```

**Métodos afectados:**
- `get_by_id()`
- `get_all()`
- `count()`
- `get_active()`

**Resultado:** Filtro de familia ahora funciona correctamente incluso con `familia_id == 0`.

---

### 5. Corrección de Formato de Moneda para IA en memory_event_handler.py

**Problema:** El archivo `memory_event_handler.py` usaba `format_pesos` (con punto como separador de miles) en lugar de `format_pesos_ai` (con espacio) para formatear montos que se guardan en la memoria vectorial de la IA. Esto causaba que las IAs (Gemma2 y Llama3) interpretaran mal los montos, confundiendo el punto como separador decimal.

**Solución:** Cambiado el import y todas las ocurrencias de `format_pesos` a `format_pesos_ai`:
```python
from services.infrastructure.formatters import format_pesos_ai
```

**Funciones afectadas:**
- `_formatear_gasto()`
- `_formatear_compra_cuotas()`
- `_formatear_ingreso()`
- `_formatear_snapshot()`
- `_formatear_ocr()`

**Resultado:**
- Antes: "Gasto registrado: Supermercado por $ 18.480" (confunde a la IA)
- Después: "Gasto registrado: Supermercado por $ 18 480" (inequívoco para IA)

Las IAs ahora interpretan correctamente los montos en pesos uruguayos.

---

### 6. Corrección de Script de Verificación de API Deprecada

**Problema:** El script `check_deprecated_api.py` usaba caracteres Unicode (✅, ❌, ⚠️) que causaban errores de encoding en Windows.

**Solución:** Reemplazados emojis por texto ASCII:
- ✅ → [OK]
- ❌ → [FAIL]
- ⚠️ → [WARN]

**Resultado:** Script ahora funciona correctamente en consola Windows.

---

## Verificación Final

✅ Todos los módulos importan correctamente  
✅ Tests de formateo Decimal pasan  
✅ Tests de tipos CategoryMetric pasan  
✅ Script de API deprecada no encuentra problemas  
✅ No hay uso de APIs obsoletas de Flet  

## Archivos Modificados

1. `views/pages/expenses_view.py` - Fix de corrupción monetaria
2. `models/ai_model.py` - Corrección de tipos Decimal
3. `repositories/expense_repository.py` - Fix de inyección SQL
4. `repositories/base_repository.py` - Fix de bypass de seguridad (4 métodos)
5. `services/ai/memory_event_handler.py` - Fix de formato de moneda para IA (5 funciones)
6. `scripts/check_deprecated_api.py` - Fix de encoding Windows

## Estado del Proyecto

- ✅ Sin vulnerabilidades críticas conocidas
- ✅ Tipos de datos consistentes (Decimal everywhere)
- ✅ APIs de Flet actualizadas y compatibles
- ✅ Aislamiento de datos por familia garantizado
- ✅ Parameter binding SQL seguro
- ✅ Formato de moneda inequívoco para IA (espacio como separador de miles)
