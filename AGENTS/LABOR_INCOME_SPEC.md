# LABOR_INCOME_SPEC.md — Módulo Laboral e Ingresos Uruguayos (v2 Definitivo)

## 1. Visión General y Filosofía de Arquitectura

Este módulo formaliza la gestión de actividades económicas, relaciones de dependencia y beneficios laborales en Uruguay (Aguinaldo y Salario Vacacional) para el **Contador Oriental**, garantizando:

1. **Python como Única Autoridad Matemática**: Todo cómputo monetario se realiza exclusivamente en Python mediante `Decimal` (cero `float`). La IA (Gemma 2:2b / Llama 70B) **nunca hace aritmética**; únicamente narra y contextualiza los resultados determinísticos inyectados en su prompt para prevenir alucinaciones.
2. **Separación Estricta entre Caja Real (`ACTUAL`) y Proyección (`PROJECTED`)**: La tabla `incomes` representa **exclusivamente dinero efectivamente cobrado** (flujo de caja real). Las estimaciones de aguinaldos o beneficios futuros se derivan bajo demanda en el motor de cálculo y **nunca alteran el balance del mes en el Dashboard**.
3. **Seguridad y Cero Regresión para Hogares en Producción**: Migraciones no destructivas, `concept = NULL` para ingresos históricos no clasificados y preservación total de los datos de las 9 familias activas en producción.
4. **Experiencia Bimodal (`FinanceMode`)**:
   - *Modo Básico* (default): Registro rápido de ingresos sin burocracia ni campos laborales obligatorios.
   - *Modo Contador Oriental (Pro)*: Habilita la gestión de actividades económicas, desglose de haberes, estimación de aguinaldo y salario vacacional.

---

## 2. Bounded Contexts y Fronteras del Dominio

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. FINANCIAL DOMAIN                                                                    │
│    • Entidades: Income, Expense.                                                       │
│    • Invariante: Flujo de caja real. Solo dinero cobrado/pagado entra a incomes.      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. LABOR & ECONOMIC DOMAIN                                                             │
│    • Entidades: EconomicActivity (1:N con FamilyMember), DependentDetails.             │
│    • Invariante: Representa la fuente generadora y contexto normativo/contractual.     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. PLANNING & CALCULATION ENGINE (Pure Python Service)                                 │
│    • Entidades: LaborCalculationEngine, CalculationRequest, CalculationResult.         │
│    • Invariante: Aritmética pura Decimal de Aguinaldo (Ley 12.840) y Vacacional.       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. AI CONTEXT BUILDER                                                                  │
│    • Responsabilidad: Construye el prompt inyectando métricas calculadas por Python.   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Modelo Conceptual y Entidades de Dominio

### A. Separación Conceptual de Dimensiones

Para evitar que una sola entidad absorba toda la lógica financiera del sistema, se distinguen explícitamente las siguientes dimensiones:
- **Situación Laboral / Naturaleza (`ActivityNature`)**: Dependiente, Independiente, Pasividad, Transferencia Social.
- **Detalles Específicos del Régimen**: Núcleo común extensible (`EconomicActivity`) con tablas 1:1 especializadas (`DependentDetails` para dependientes; futuras para independientes).
- **Concepto de Ingreso (`IncomeConcept`)**: Clasificación granular del ítem cobrado (`salary`, `aguinaldo`, `vacation_pay`, `overtime`, `commission`, `bonus`, `other`).
- **Régimen Previsional / Tributario**: Atributos futuros desacoplados (BPS, Caja Profesional, Fonasa, IRPF/IASS).

### B. Modos de Finanzas (`FinanceMode`)
```python
class FinanceMode(StrEnum):
    BASIC = "basic"                      # Modo Rápido (Default)
    CONTADOR_ORIENTAL = "contador_pro"   # Modo Contador Oriental (Beneficios habilitados)
```

### C. Naturaleza de la Actividad Económica (`ActivityNature`)
```python
class ActivityNature(StrEnum):
    DEPENDIENTE = "dependiente"                    # MVP: Empleados comercio, industria, servicios, público
    INDEPENDIENTE = "independiente"                # Fase 3: Servicios personales, Literal E, Monotributo
    PASIVIDAD = "pasividad"                        # Fase 3: Jubilaciones y pensiones (BPS, Cajas)
    TRANSFERENCIA_SOCIAL = "social_transfer"       # Fase 3: Asignaciones familiares, TUS, subsidios
```

### D. Conceptos de Ingreso (`IncomeConcept`)
```python
class IncomeConcept(StrEnum):
    SALARY = "salary"                      # Sueldo mensual habitual / Jornal
    AGUINALDO = "aguinaldo"                # Sueldo Anual Complementario cobrado
    SALARIO_VACACIONAL = "vacation_pay"    # Salario vacacional cobrado
    OVERTIME = "overtime"                  # Horas extras
    COMMISSION = "commission"              # Comisiones
    BONUS = "bonus"                        # Bonificaciones / Gratificaciones
    OTHER = "other"                        # Otros ingresos
```

### E. Modelos de Datos del Dominio

```python
class RemunerationType(StrEnum):
    MENSUAL = "mensual"
    JORNALERO = "jornalero"

class DependentDetails(BaseModel):
    """Detalle especializado para trabajadores en relación de dependencia (MVP)."""
    id: int | None = None
    economic_activity_id: int | None = None
    remuneration_type: RemunerationType = RemunerationType.MENSUAL
    weekly_hours: int = 40
    estimated_monthly_nominal: Decimal | None = None
    created_at: datetime | None = None

class EconomicActivity(BaseModel):
    """
    Actividad económica o relación laboral de un integrante familiar.
    Cardinalidad: FamilyMember (1) -> EconomicActivity (N).
    Permite múltiples actividades simultáneas (ej. empleo dependiente + docencia independiente).
    """
    id: int | None = None
    familia_id: int
    family_member_id: int
    nature: ActivityNature = ActivityNature.DEPENDIENTE
    title: str = "Comercio / Servicios"
    start_date: date | None = None       # Fecha de ingreso / alta (vital para cómputo de aguinaldo)
    end_date: date | None = None         # Fecha de cese laboral (None si activa)
    is_active: bool = True
    dependent_details: DependentDetails | None = None
```

---

## 4. Motor Determinístico de Cálculo Laboral (Python)

### A. Períodos y Cómputo de Aguinaldo en Uruguay (Ley 12.840 y Dec. Ley 14.525)

El Sueldo Anual Complementario (SAC) se abona en dos fracciones:
1. **1ª Fracción (Junio)**: Devengado entre el **1º de diciembre** del año anterior y el **31 de mayo** del año en curso. Plazo legal de pago: hasta el 30 de junio.
2. **2ª Fracción (Diciembre)**: Devengado entre el **1º de junio** y el **30 de noviembre** del año en curso. Plazo legal de pago: hasta el 20 de diciembre.

$$\text{Aguinaldo} = \text{quantize}\left(\frac{\sum \text{Remuneraciones Computables}}{12}, \text{Decimal('0.01')}\right)$$

### B. Invariante Cobrado vs. Devengado (MVP)
- Para empleados dependientes de cobro mensual habitual, el `Income` registrado en el mes $M$ representa la remuneración devengada del mes $M$.
- Si faltan meses dentro del semestre de devengo y la actividad laboral está vigente, el motor proyecta los meses restantes utilizando `estimated_monthly_nominal` o el promedio de los meses ya registrados, marcando el resultado como `PROVISIONAL`.

### C. Estados y Contratos del Motor de Cálculo

```python
class CalculationStatus(StrEnum):
    CALCULATED = "calculated"              # Semestre cerrado con todos los meses reales
    PROVISIONAL = "provisional"            # Semestre en curso con meses proyectados
    INSUFFICIENT_DATA = "insufficient_data"# Falta fecha de inicio o salario base
    REQUIRES_REVIEW = "requires_review"    # Actividad jornalera, irregular o ingresos ambiguos

class ComputableMonth(BaseModel):
    year: int
    month: int
    monto: Decimal
    es_proyectado: bool = False

class CalculationRequest(BaseModel):
    familia_id: int
    family_member_id: int
    economic_activity_id: int
    calculation_type: str                  # "AGUINALDO_JUNIO" | "AGUINALDO_DICIEMBRE" | "SALARIO_VACACIONAL"
    period_year: int
    period_semester: int                   # 1 (Dic-May) o 2 (Jun-Nov)
    accrual_start: date
    accrual_end: date
    devengados: list[Income]
    activity_start_date: date | None
    estimated_base_salary: Decimal | None

class CalculationResult(BaseModel):
    request_summary: dict[str, Any]
    rule_version: str = "UY-MTSS-SAC-2026-v1"
    status: CalculationStatus
    currency: str = "UYU"
    input_income_ids: list[int]
    months_breakdown: list[ComputableMonth]
    total_computable: Decimal
    divisor: Decimal = Decimal("12")
    final_amount: Decimal
    missing_fields: list[str] = Field(default_factory=list)
    explanation_notes: list[str] = Field(default_factory=list)
    calculated_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### D. Salario Vacacional Orientativo (Ley 16.101)

$$\text{Salario Vacacional} = \text{quantize}\left(\frac{\text{Sueldo Líquido Mensual}}{30} \times \text{Días de Licencia}, \text{Decimal('0.01')}\right)$$

- En el MVP se asume la base legal de 20 días anuales (o prorrata si la antigüedad en el año civil es menor).
- Si la remuneración es de tipo `JORNALERO` o variable, el estado retornado es `REQUIRES_REVIEW` con nota explicativa.

---

## 5. Esquema de Base de Datos y Persistencia (PostgreSQL)

```sql
-- 1. Modo de Finanzas en Familia
ALTER TABLE familias 
ADD COLUMN IF NOT EXISTS modo_finanzas VARCHAR(30) DEFAULT 'basic';

-- 2. Tabla de Actividades Económicas (1:N con family_members)
CREATE TABLE IF NOT EXISTS economic_activities (
    id SERIAL PRIMARY KEY,
    familia_id INTEGER NOT NULL REFERENCES familias(id) ON DELETE CASCADE,
    family_member_id INTEGER NOT NULL REFERENCES family_members(id) ON DELETE CASCADE,
    nature VARCHAR(50) NOT NULL DEFAULT 'dependiente',
    title VARCHAR(100) NOT NULL DEFAULT 'Comercio / Servicios',
    start_date DATE NULL,
    end_date DATE NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_economic_activities_member ON economic_activities(familia_id, family_member_id);

-- 3. Tabla de Detalles de Dependencia (1:1 con economic_activities)
CREATE TABLE IF NOT EXISTS dependent_details (
    id SERIAL PRIMARY KEY,
    economic_activity_id INTEGER NOT NULL UNIQUE REFERENCES economic_activities(id) ON DELETE CASCADE,
    remuneration_type VARCHAR(30) NOT NULL DEFAULT 'mensual',
    weekly_hours INTEGER NOT NULL DEFAULT 40,
    estimated_monthly_nominal NUMERIC(12, 2) NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- 4. Ampliación Segura y No Destructiva de Incomes
ALTER TABLE incomes 
ADD COLUMN IF NOT EXISTS concept VARCHAR(50) NULL,
ADD COLUMN IF NOT EXISTS economic_activity_id INTEGER REFERENCES economic_activities(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_incomes_concept ON incomes(familia_id, concept);
CREATE INDEX IF NOT EXISTS idx_incomes_activity ON incomes(familia_id, economic_activity_id);
```

---

## 6. Integración con el Asistente IA (`ContextBuilder`)

El contexto inyectado al modelo local Gemma 2:2b (u Ollama / Llama 70B) recibe **únicamente valores calculados y preformateados**:

```text
=== BENEFICIOS LABORALES CALCULADOS POR PYTHON ===
- Miembro: Gonzalo
  * Actividad: Cajero de Supermercado (Dependiente)
  * Antigüedad: Desde 01/12/2025 (6 meses computables en período actual)
  * Sueldo Líquido Habitual: $ 45.000 (UYU)
  * Aguinaldo Proyectado Junio 2026: $ 22.500 (Regla: UY-MTSS-SAC-2026-v1, Estado: CALCULATED)
    - Desglose: 6 meses devengados a $ 45.000 ($ 270.000 / 12)
  * Salario Vacacional Estimado (20 días): $ 30.000 (Orientativo)
==================================================
INSTRUCCIÓN PARA LA IA:
- Utilizá los números anteriores de forma textual. NUNCA realices recálculos aritméticos.
- El aguinaldo se rige por la Ley 12.840 y el salario vacacional por la Ley 16.101.
```

---

## 7. Plan de Implementación y Roadmap

| Fase | Alcance | Estado |
|---|---|---|
| **Fase 1 (MVP)** | Dominio `EconomicActivity` (1:N), `DependentDetails`, `AguinaldoCalculator`, `VacationPayCalculator`, `FinanceMode`, `LaborService`, tests unitarios y 0 errores en Ty/Ruff. | **Completado ✅** |
| **Fase 2** | Submotor de Retenciones e Impuestos (Montepío 15%, Fonasa 3% a 8%, FRL 0.1%, IRPF Categoría II mensual con 6% ficto y liquidación anual DGI, cálculo inverso determinístico por bisección). | **CLOSED ✅** |
| **Fase 3A** | Servicios Personales (Evaluador de elegibilidad factual, IVA 22%/10% con retenciones CEDE 60%, IRPF anticipos bimestrales con deducción ficta 30% o real, y CJPPU categorías 1 a 10 al 16.5%). | **Completado ✅** |
| **Fase 3B** | Pequeña Empresa — Literal E (Tope anual 305.000 UI con cotización dinámica, cuota mensual DGI escalonada 25%/50%/100%, aporte patronal BPS). | **Completado ✅** |
| **Fase 3C** | Monotributo Común y Monotributo Social MIDES (Evaluador de elegibilidad $\le 15\text{ m}^2$, topes 183.000 / 305.000 UI, cuota única BPS+DGI y subsidio MIDES en 4 años). | **Completado ✅** |
| **Fase 3D** | Pasividades, Jubilaciones y Pensiones — IASS (Mínimo no imponible 9 BPC, 5 tramos progresivos, deducciones por salud 14%/8%, consolidación de múltiples cajas). | **Completado ✅** |
| **Fase 4** | Dataset Normativo Uruguayo Curado y Fine-Tuning de Gemma 2:2b con Unsloth para asesoramiento contextual sin alucinaciones. | **Siguiente Paso 🎯** |



