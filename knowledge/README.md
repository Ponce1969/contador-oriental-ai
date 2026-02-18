# Knowledge Base - Contador Oriental

Esta carpeta contiene el conocimiento curado para el asistente de IA "Contador Oriental".

## Archivos Actuales

### 1. `inclusion_financiera_uy.md`
**Tema:** Ley de Inclusión Financiera y beneficios de IVA
**Keywords:** iva, tarjeta, débito, crédito, descuento, restaurante, compras, super
**Contenido:**
- Reducción de 2 puntos de IVA con débito
- Descuento de 9 puntos en restaurantes
- Ejemplos prácticos de ahorro

### 2. `irpf_familia_uy.md`
**Tema:** Impuesto a la Renta y deducciones familiares
**Keywords:** irpf, impuesto, hijo, alquiler, deduccion, dgi, devolucion, hipoteca
**Contenido:**
- Deducciones por hijos (20 BPC/año)
- Crédito por alquiler (6% anual)
- Deducción por hipoteca
- Ejemplos de familias tipo

### 3. `ahorro_ui_uy.md`
**Tema:** Ahorro en Unidades Indexadas
**Keywords:** ahorro, ui, unidad indexada, inflacion, plazo fijo, invertir, banco
**Contenido:**
- Qué es la UI
- Instrumentos de ahorro (cuentas, plazos fijos)
- Protección contra inflación
- Ejemplos de ahorro a largo plazo

## Reglas de Contenido

1. **Máximo 200 líneas por archivo** - Para caber en el contexto de gemma2:2b
2. **Lenguaje claro y directo** - Evitar jerga innecesaria
3. **Ejemplos prácticos** - Siempre incluir casos concretos con montos
4. **Formato Markdown** - Usar headers, listas y negritas para estructura
5. **Actualización anual** - Revisar valores de BPC y tasas cada enero

## Cómo Agregar Nuevo Conocimiento

1. Crear archivo `.md` en esta carpeta
2. Seguir estructura: Título → Conceptos → Consejos → Ejemplos
3. Agregar keywords al `mapa_conocimiento` en `ai_advisor_service.py`
4. Mantener menos de 200 líneas
5. Probar con preguntas reales

## Próximos Archivos Sugeridos

- `iva_general_uy.md` - Tasas de IVA por categoría
- `bps_aportes_uy.md` - Aportes jubilatorios, monotributo
- `gastos_deducibles_uy.md` - Qué gastos se pueden deducir
- `educacion_salud_uy.md` - Beneficios fiscales
- `vehiculos_patentes_uy.md` - Impuestos de vehículos
- `emprendedores_uy.md` - Monotributo, facturación electrónica
