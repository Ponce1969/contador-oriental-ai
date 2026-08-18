# LABOR_INCOME_SPEC.md — Módulo Laboral e Ingresos Uruguayos (v2 Definitivo)

## 1. Visión General y Filosofía de Arquitectura

Este módulo formaliza la gestión de actividades económicas, relaciones de dependencia y beneficios laborales en Uruguay (Aguinaldo y Salario Vacacional) para el **Contador Oriental**, garantizando:
1. **Python como Única Autoridad Matemática**: Todo cómputo monetario se realiza exclusivamente en Python mediante `Decimal` (cero `float`). La IA (Gemma 2:2b / Llama 70B) **nunca hace aritmética**; únicamente narra y contextualiza los resultados determinísticos inyectados en su prompt.
2. **Separación Estricta entre Caja Real (`ACTUAL`) y Proyección (`PROJECTED`)**: La tabla `incomes` representa **exclusivamente dinero efectivamente cobrado**. Las estimaciones de aguinaldos o beneficios futuros se derivan en el motor de cálculo y **nunca alteran el balance del mes en el Dashboard**.
3. **Seguridad y Cero Regresión para Hogares en Producción**: Migraciones no destructivas, `concept = NULL` para ingresos históricos no clasificados y preservación total de los datos de las 9 familias activas.
4. **Experiencia Bimodal (`FinanceMode`)**: *Modo Básico* (default) para registro rápido sin burocracia, y *Modo Contador Oriental (Pro)* para quienes deseen planificación laboral profunda.

---

## 2. Bounded Contexts y Fronteras del Dominio

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. FINANCIAL DOMAIN                                                                    │
│    • Entidades: Income, Expense.                                                       │
│    • Responsabilidad: Dinero efectivamente cobrado/pagado que afecta el balance real.  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. LABOR & ECONOMIC DOMAIN                                                             │
│    • Entidades: EconomicActivity (1:N con FamilyMember), DependentDetails.             │
│    • Responsabilidad: Contexto del vínculo laboral (antigüedad, actividad, tipo).      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. PLANNING & CALCULATION ENGINE (Python Pure Service)                                 │
│    • Entidades: LaborCalculationEngine, CalculationRequest, CalculationResult.         │
│    • Responsabilidad: Aritmética pura Decimal de aguinaldo (1/12) y salario vacacional.│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. AI CONTEXT BUILDER                                                                  │
│    • Responsabilidad: Formateo de los resultados exactos para el asistente IA.         │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Modelo Conceptual y Entidades de Dominio

### A. Modos de Finanzas (`FinanceMode`)
```python
class FinanceMode(str, Enum):
    BASIC = "basic"                      # Modo Rápido (Default)
    CONTADOR_ORIENTAL = "contador_pro"   # Modo Contador Oriental (Beneficios habilitados)
```

### B. Naturaleza de la Actividad Económica (`ActivityNature`)
```python
class ActivityNature(str, Enum):
    DEPENDIENTE = "dependiente"                    # MVP: Empleados comercio, industria, servicios, público
    INDEPENDIENTE = "independiente"                # Fase 3: Servicios personales, Literal E, Monotributo
    PASIVIDAD = "pasividad"                        # Fase 3: Jubilaciones y pensiones
    TRANSFERENCIA_SOCIAL = "social_transfer"       # Fase 3: Asignaciones familiares, TUS, subsidios
```

### C. Conceptos de Ingreso (`IncomeConcept`)
```python
class IncomeConcept(str, Enum):
    SALARY = "salary"                      # Sueldo mensual habitual / Jornal
    AGUINALDO = "aguinaldo"                # Sueldo Anual Complementario cobrado
    SALARIO_VACACIONAL = "vacation_pay"    # Salario vacacional cobrado
    OVERTIME = "overtime"                  # Horas extras
    COMMISSION = "commission"              # Comisiones
    BONUS = "bonus"                        # Bonificaciones / Gratificaciones
    OTHER = "other"                        # Otros ingresos
```

### D. Modelos de Datos del Dominio
```python
class RemunerationType(str, Enum):
    MENSUAL = "mensual"
    JORNALERO = "jornalero"

class DependentDetails(BaseModel):
    """Detalle especializado para trabajadores en relación de dependencia (MVP)."""
    id: int | None = None
    economic_activity_id: int | None = None
    remuneration_type: RemunerationType = RemunerationType.MENSUAL
    weekly_hours: int = 40
    estimated_monthly_nominal: Decimal | None = None

class EconomicActivity(BaseModel):
    """Actividad económica o relación laboral de un integrante familiar (1:N con FamilyMember)."""
    id: int | None = None
    familia_id: int
    family_member_id: int
    nature: ActivityNature = ActivityNature.DEPENDIENTE
    title: str = "Comercio / Servicios"
    start_date: date | None = None       # Fecha de ingreso / alta (vital para aguinaldo)
    end_date: date | None = None         # Fecha de cese laboral (opcional)
    is_active: bool = True
    dependent_details: DependentDetails | None = None
```

---

## 4. Motor Determinístico de Cálculo Laboral

### A. Períodos de Aguinaldo en Uruguay (MTSS / Ley 12.840)
- **1ª Fracción (Junio)**: Devengado entre el **1º de diciembre** del año anterior y el **31 de mayo** del año en curso.
- **2ª Fracción (Diciembre)**: Devengado entre el **1º de junio** y el **30 de noviembre** del año en curso.

$$\text{Aguinaldo} = \text{quantize}\left(\frac{\sum \text{Remuneraciones Computables}}{12}, \text{Decimal('0.01')}\right)$$

### B. Invariante Cobrado vs. Devengado (MVP)
Para el empleado dependiente mensual estándar, un `Income` registrado con `concept = SALARY` en el mes $M$ se computa como la remuneración devengada del mes $M$.

### C. Estados y Contratos de Cálculo
```python
class CalculationStatus(str, Enum):
    CALCULATED = "calculated"              # Cálculo exacto con meses reales completos
    PROVISIONAL = "provisional"            # Cálculo estimado con meses futuros proyectados
    INSUFFICIENT_DATA = "insufficient_data"# Falta start_date o sueldo base
    REQUIRES_REVIEW = "requires_review"    # Ingresos no clasificados o caso variable/jornalero

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
    request_summary: dict
    rule_version: str = "UY-MTSS-SAC-2026-v1"
    status: CalculationStatus
    currency: str = "UYU"
    input_income_ids: list[int]
    months_breakdown: list[ComputableMonth]
    total_computable: Decimal
    divisor: Decimal = Decimal("12")
    final_amount: Decimal
    missing_fields: list[str] = []
    explanation_notes: list[str] = []
    calculated_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### D. Salario Vacacional Orientativo (Ley 16.101)
$$\text{Salario Vacacional} = \text{quantize}\left(\frac{\text{Sueldo Líquido Mensual}}{30} \times \text{Días de Licencia}, \text{Decimal('0.01')}\right)$$
- Si la actividad es jornalera o posee alta variabilidad salarial, el motor devuelve `REQUIRES_REVIEW` con advertencia de revisión profesional.

---

## 5. Esquema de Base de Datos y Persistencia (PostgreSQL)

```sql
-- 1. Modo de Finanzas en Familia
ALTER TABLE familias 
ADD COLUMN IF NOT EXISTS modo_finanzas VARCHAR(30) DEFAULT 'basic';

-- 2. Tabla de Actividades Económicas (1 a N con family_members)
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

-- 3. Tabla de Detalles de Dependencia
CREATE TABLE IF NOT EXISTS dependent_details (
    id SERIAL PRIMARY KEY,
    economic_activity_id INTEGER NOT NULL UNIQUE REFERENCES economic_activities(id) ON DELETE CASCADE,
    remuneration_type VARCHAR(30) NOT NULL DEFAULT 'mensual',
    weekly_hours INTEGER NOT NULL DEFAULT 40,
    estimated_monthly_nominal NUMERIC(12, 2) NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- 4. Ampliación Segura de Incomes
ALTER TABLE incomes 
ADD COLUMN IF NOT EXISTS concept VARCHAR(50) NULL,
ADD COLUMN IF NOT EXISTS economic_activity_id INTEGER REFERENCES economic_activities(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_incomes_concept ON incomes(familia_id, concept);
```

---

## 6. Integración con el Asistente IA (`ContextBuilder`)

El contexto inyectado a Gemma 2:2b / Llama 70B contiene los números determinísticos pre-resueltos:

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
INSTRUCCIÓN:
- Utilizá los números anteriores de forma textual. NUNCA hagas recálculos aritméticos.
- El aguinaldo se rige por la Ley 12.840 y el salario vacacional por la Ley 16.101.
```

---

## 7. Roadmap de Implementación

| Fase | Alcance |
|---|---|
| **Fase 1 (MVP Actual)** | `EconomicActivity`, `DependentDetails`, `AguinaldoCalculator`, `VacationPayCalculator`, `FinanceMode`, UI básica y tests exhaustivos. |
| **Fase 2** | Submotor de Retenciones (Fonasa 3% a 8%, Montepío 15%, FRL 0.1%, IRPF Cat. II). |
| **Fase 3** | Actividades Independientes (Servicios Personales IVA/IRPF, Literal E DGI, Monotributo MIDES, Pasividades IASS). |
| **Fase 4** | Dataset Normativo Uruguayo Curado y Fine-Tuning de Gemma 2:2b con Unsloth. |
