# LABOR_INCOME_SPEC.md — Módulo Laboral e Ingresos Uruguayos

## 1. Visión General y Objetivos

El objetivo de este módulo es dotar al **Contador Oriental** de una comprensión y gestión profunda de la economía laboral uruguaya, manteniendo una arquitectura bimodal:
- **Simplicidad para quienes buscan solo registrar números rápidos.**
- **Potencia y precisión legal/contable para quienes desean planificar aguinaldos, licencias, aportes y regímenes independientes.**

### Principios de Diseño
1. **Seguridad Absoluta de Datos**: Cero pérdida o corrupción de datos de las familias activas en producción. Migraciones 100% no destructivas.
2. **Progressive Disclosure (Revelación Progresiva)**: Los formularios muestran únicamente los campos relevantes para el régimen laboral configurado.
3. **Bimodalidad (Modo Básico vs. Modo Contador)**: Configurable a nivel del hogar para adaptarse a cada perfil de usuario.

---

## 2. Modos de Experiencia del Hogar

Configurable en el perfil familiar (`familias.modo_finanzas`):

| Modo | Características |
|---|---|
| **Básico / Rápido** (Default) | Ingresos simples (monto, fecha, descripción, categoría). Sin preguntas impositivas ni cálculos adicionales. Cero fricción. |
| **Contador Oriental (Pro)** | Habilita regímenes laborales uruguayos, proyección de aguinaldos (Junio/Diciembre), salario vacacional, cálculo de líquidos y retenciones. |

---

## 3. Regímenes Laborales Uruguayos

Definidos en el enum `RegimenLaboral`:

### A. Dependiente (`dependiente`)
- **Aplica a**: Empleados de comercio, industria, servicios, sector público y doméstico.
- **Conceptos Habilitados**:
  - `💼 Sueldo Mensual / Quincenal` (Líquido o Nominal con desglose)
  - `🎁 Aguinaldo (SAC)`:
    - *Fracción Junio*: $1/12$ de remuneraciones devengadas entre 1º de diciembre y 31 de mayo (Ley 12.840).
    - *Fracción Diciembre*: $1/12$ de remuneraciones devengadas entre 1º de junio y 30 de noviembre (Ley 12.840 / 14.525).
  - `🏖️ Salario Vacacional`: Pago previo obligatorio por días de licencia (Ley 16.101, mínimo jornal líquido $\times$ días).
  - `⏱️ Horas Extras / Comisiones / Primas`.
- **Descuentos Típicos de Referencia**:
  - Montepío BPS ($15\%$)
  - FONASA ($3\%$ a $8\%$ según cónyuge/hijos)
  - FRL ($0.1\%$)
  - IRPF Categoría II (según franja)

### B. Unipersonal / Servicios Personales (`servicios_personales`)
- **Aplica a**: Profesionales no dependientes, consultores, desarrolladores, prestadores de servicios.
- **Conceptos Habilitados**:
  - `🧾 Facturación Bruta (con o sin IVA 22% / 10%)`
  - `📉 Anticipos IRPF Cat. II` (bimensual)
  - `🏥 Aporte BPS / Fonasa / Caja Profesional (CJPPU)`

### C. Empresa Unipersonal / Pequeña Empresa Literal E (`literal_e`)
- **Aplica a**: Comercios barriales, almacenes, pequeños talleres (tope hasta 305.000 UI anuales).
- **Conceptos Habilitados**:
  - `🏪 Ventas / Ingresos del Negocio`
  - `📑 Cuota Fija Mensual IVA Literal E (DGI)`
  - `🏛️ Aporte Patronal Titular BPS`

### D. Monotributo / Monotributo Social MIDES (`monotributo`)
- **Aplica a**: Pequeños emprendimientos, feriantes, artesanos, servicios de reducida dimensión económica.
- **Conceptos Habilitados**:
  - `🛒 Ingresos de Venta / Servicio`
  - `🏷️ Cuota Única Unificada BPS / DGI`

### E. Pasividades y Retiros (`pasividad`)
- **Aplica a**: Jubilados y pensionistas (BPS, Caja Militar, Policial, Bancaria, Notarial, CJPPU).
- **Conceptos Habilitados**:
  - `👴 Jubilación / Pensión`
  - `📉 Retención IASS y Fonasa`
  - `🎁 Aguinaldo Pasivos (BPS diciembre)`

### F. Transferencias Sociales (`transferencias_sociales`)
- **Aplica a**: Familias receptoras de beneficios estatales.
- **Conceptos Habilitados**:
  - `👶 Asignación Familiar (AFAM / Plan de Equidad - BPS)`
  - `💳 Tarjeta Uruguay Social (TUS - MIDES)`
  - `🩺 Subsidios BPS (Enfermedad, Desempleo, Maternidad/Paternidad)`

---

## 4. Estructura de Datos y Modelo Relacional

### Tabla `family_members` (Ampliación No Destructiva)
```sql
ALTER TABLE family_members 
ADD COLUMN IF NOT EXISTS regimen_laboral VARCHAR(50) DEFAULT 'general',
ADD COLUMN IF NOT EXISTS aportes_fonasa_hijos BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS aportes_fonasa_conyuge BOOLEAN DEFAULT FALSE;
```

### Tabla `incomes` (Ampliación No Destructiva)
```sql
ALTER TABLE incomes 
ADD COLUMN IF NOT EXISTS tipo_concepto VARCHAR(50) DEFAULT 'sueldo_estandar',
ADD COLUMN IF NOT EXISTS es_aguinaldo BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS es_salario_vacacional BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS periodo_aguinaldo VARCHAR(20) DEFAULT NULL, -- 'junio_2026', 'diciembre_2026'
ADD COLUMN IF NOT EXISTS monto_nominal DECIMAL(12, 2) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS retenciones_totales DECIMAL(12, 2) DEFAULT NULL;
```

### Tabla `familias` (Preferencia de Modo)
```sql
ALTER TABLE familias 
ADD COLUMN IF NOT EXISTS modo_finanzas VARCHAR(30) DEFAULT 'basico'; -- 'basico' o 'contador_oriental'
```

---

## 5. Lógica de Cálculo y Asistencia de la IA (Reglas Estrictas)

### Regla de Oro: Aritmética 100% en Python con `Decimal`
- **CERO `float`**: Todo cálculo financiero, sueldo, retención, aguinaldo o acumulador se computa en Python usando `Decimal` (evitando imprecisiones de punto flotante IEEE 754).
- **CERO Aritmética en el LLM**: La IA (tanto Gemma 2:2b local como Llama 70B) **NUNCA debe hacer sumas, restas, divisiones ni cálculos de aguinaldo**. 
- **Pre-cálculo determinístico**: El backend de Python calcula de forma exacta los montos proyectados, subtotales por régimen y retenciones, inyectándolos en el prompt con los valores finales ya resueltos.
- **Rol del LLM / Fine-Tuning**: El modelo únicamente **lee, narra y explica** en español rioplatense, fundamentando en la normativa uruguaya sin riesgo de alucinación numérica.

1. **Calculador de Proyección de Aguinaldo (Python Engine)**:
   $$\text{Aguinaldo Estimado} = \text{quantize}\left(\frac{\sum \text{Sueldos e Ingresos Variables del Semestre (Decimal)}}{12}\right)$$
   - En **Mayo**: Python calcula la 1ª fracción y la pasa al prompt como dato exacto.
   - En **Noviembre**: Python calcula la 2ª fracción y la pasa al prompt como dato exacto.
2. **Contexto Inyectado para el Contador Oriental IA**:
   El prompt recibe los números exactos pre-formateados:
   > *"DATOS CALCULADOS: Ingreso líquido: $ 45.000, Aguinaldo proyectado junio: $ 22.500 (calculado sobre 6 meses devengados)."*


---

## 6. Plan de Verificación y Testing

- **Tests Unitarios**: Validar el modelo Pydantic `Income` y `FamilyMember` con los nuevos campos opcionales y sus defaults.
- **Tests de Migración**: Verificar que los registros históricos mantengan compatibilidad 100% sin campos nulos obligatorios.
- **Tests de Cálculo de Aguinaldo**: Probar la fórmula del $1/12$ con meses variables y escenarios de alta reciente.
- **Tests de Resistencia a Mutaciones**: Validar que los cálculos de balance familiar no dupliquen ingresos al calcular aguinaldos proyectados vs. reales.
