# LABOR_INCOME_SPEC.md — Módulo Laboral e Ingresos Uruguayos (v2)

## 1. Visión General y Filosofía de Arquitectura

El propósito del módulo es modelar la realidad laboral y de beneficios sociales en Uruguay para el **Contador Oriental**, permitiendo que las familias planifiquen con precisión sus aguinaldos, licencias y regímenes laborales sin sacrificar la simplicidad para quienes solo desean registrar gastos rápidos.

### Invariantes y Principios No Negociables
1. **Python es la Única Autoridad Matemática**:
   - Todos los cálculos monetarios se ejecutan en Python usando exclusivamente **`Decimal`**.
   - Queda estrictamente prohibido el uso de `float` en el motor de cálculo.
   - La IA (Gemma 2:2b / Llama 70B) **NUNCA hace aritmética**. Recibe los valores finales pre-calculados y estructurados para explicarlos y contextualizarlos en español rioplatense.
2. **Separación Estricta entre Real (`ACTUAL`) y Proyectado (`PROJECTED`)**:
   - La tabla `incomes` representa **exclusivamente flujo de caja real efectivamente percibido**.
   - Las proyecciones de aguinaldo y salario vacacional viven en el motor laboral y se muestran en la sección de planificación; **NUNCA alteran el balance del mes en el Dashboard ni contaminan los snapshots de gastos/ingresos**.
3. **Seguridad y Cero Regresión para Hogares en Producción**:
   - Migraciones 100% no destructivas con valores por defecto semánticos.
   - Aislamiento multi-tenant estricto mediante `familia_id` en todas las consultas y repositorios.
4. **Progressive Disclosure y Experiencia Bimodal**:
   - **Modo Básico (Default)**: Experiencia limpia y minimalista para quienes solo quieren anotar ingresos y gastos.
   - **Modo Contador Oriental (Pro)**: Habilita el cálculo de aguinaldos, perfiles laborales y beneficios.

---

## 2. Modos de Finanzas del Hogar (`FinanceMode`)

Configurable en la entidad `Familia` (`familias.modo_finanzas`):

```python
class FinanceMode(str, Enum):
    BASIC = "basic"                      # Modo Rápido: solo flujo de caja real
    CONTADOR_ORIENTAL = "contador_pro"   # Modo Pro: beneficios laborales, aguinaldos y regímenes
```

- El cambio de modo es una **preferencia de presentación (UX)** y **nunca recalcula ni altera datos históricos**.
- Si un usuario en modo básico consulta sobre aguinaldos a la IA, el sistema detecta la consulta, verifica si faltan datos en su perfil y le sugiere activar el modo Contador Oriental.

---

## 3. Modelo Conceptual y Perfil Laboral Extensible (`LaborProfile`)

Para permitir que el sistema crezca sin refactorizaciones destructivas, se modela un **Perfil Laboral Extensible** vinculado a `FamilyMember`:

```
FamilyMember (Persona)
    └── LaborProfile (1 a 1 opcional)
            ├── Núcleo Común (regimen, actividad, fecha_inicio, fecha_fin, caja)
            └── Detalles Específicos por Régimen (MVP: DependienteDetails)
```

### A. Regímenes Laborales (`LaborRegime`)
```python
class LaborRegime(str, Enum):
    DEPENDIENTE = "dependiente"                    # MVP: Comercio, Industria, Servicios, Público
    SERVICIOS_PERSONALES = "servicios_personales"  # Fase 3: Profesionales e independientes con IVA/IRPF
    LITERAL_E = "literal_e"                        # Fase 3: Pequeña empresa (IVA cuota fija DGI)
    MONOTRIBUTO = "monotributo"                    # Fase 3: Monotributo común / Monotributo MIDES
    PASIVIDAD = "pasividad"                        # Fase 3: Jubilaciones y pensiones
    TRANSFERENCIAS_SOCIALES = "social_benefits"    # Fase 3: AFAM, TUS, subsidios
```

### B. Cajas de Previsión Social (`PensionFund`)
```python
class PensionFund(str, Enum):
    BPS = "bps"
    CJPPU = "cjppu"          # Caja de Profesionales Universitarios
    NOTARIAL = "notarial"
    BANCARIA = "bancaria"
    MILITAR = "militar"
    POLICIAL = "policial"
    NINGUNA = "ninguna"
```

### C. Estructura del Perfil Laboral (Dominio)
```python
class DependienteLaborDetails(BaseModel):
    """Detalles específicos para trabajadores en relación de dependencia (MVP)."""
    tipo_remuneracion: str = "mensual"  # "mensual" | "jornalero"
    horas_semanales: int = 40
    tiene_hijos_a_cargo: bool = False
    tiene_conyuge_a_cargo: bool = False
    aplica_fonasa: bool = True

class LaborProfile(BaseModel):
    """Perfil económico/laboral del integrante familiar."""
    id: int | None = None
    familia_id: int
    family_member_id: int
    regimen: LaborRegime = LaborRegime.DEPENDIENTE
    actividad: str = "Comercio / Servicios"
    fecha_inicio: date | None = None      # Fecha de ingreso/antigüedad
    fecha_fin: date | None = None         # Fecha de egreso (si cesó)
    caja_previsional: PensionFund = PensionFund.BPS
    detalles_dependiente: DependienteLaborDetails | None = None
    activo: bool = True
```

---

## 4. Conceptos de Ingreso (`IncomeConcept`)

Para evitar flags booleanos inconsistentes (`es_aguinaldo`, `es_salario_vacacional`), el tipo de ingreso se define como un concepto tipado:

```python
class IncomeConcept(str, Enum):
    SALARY = "salary"                      # Sueldo mensual habitual / Jornal
    AGUINALDO = "aguinaldo"                # Sueldo Anual Complementario cobrado
    SALARIO_VACACIONAL = "vacation_pay"    # Salario vacacional cobrado
    OVERTIME = "overtime"                  # Horas extras computables
    COMMISSION = "commission"              # Comisiones computables
    BONUS = "bonus"                        # Bonificaciones / Gratificaciones
    OTHER = "other"                        # Otros ingresos
```

- `computable_para_aguinaldo`: `SALARY`, `OVERTIME`, `COMMISSION` son computables por ley (Ley 12.840).

---

## 5. Motor Determinístico de Cálculos Laborales (`LaborCalculationEngine`)

El cálculo de beneficios es una función pura en Python que produce un resultado trazable y auditable.

### A. Períodos de Aguinaldo en Uruguay (MTSS / Ley 12.840)
- **1ª Fracción (Junio)**: Devengado entre el **1º de diciembre** del año anterior y el **31 de mayo** del año en curso.
- **2ª Fracción (Diciembre)**: Devengado entre el **1º de junio** y el **30 de noviembre** del año en curso.

$$\text{Aguinaldo} = \text{quantize}\left(\frac{\sum_{m \in \text{Período}} \text{Remuneraciones Computables}(m)}{12}, \text{Decimal('0.01')}\right)$$

### B. Contrato de Resultado del Cálculo (`CalculationResult`)
```python
class CalculationStatus(str, Enum):
    CALCULATED = "calculated"              # Cálculo exacto con datos completos
    PROVISIONAL = "provisional"            # Proyección estimada con meses faltantes
    INSUFFICIENT_DATA = "insufficient_data"# Falta fecha de inicio o datos mínimos
    REQUIRES_REVIEW = "requires_review"    # Régimen o situación especial fuera de estándar

class ComputableMonth(BaseModel):
    year: int
    month: int
    monto: Decimal
    es_proyectado: bool = False  # True si el mes aún no transcurrió y se usó sueldo base

class CalculationResult(BaseModel):
    calculation_type: str                   # "AGUINALDO_JUNIO", "AGUINALDO_DICIEMBRE", "SALARIO_VACACIONAL"
    rule_version: str                       # "UY-MTSS-SAC-2026-v1"
    status: CalculationStatus
    currency: str = "UYU"
    total_computable: Decimal
    divisor: Decimal = Decimal("12")
    final_amount: Decimal
    months_breakdown: list[ComputableMonth]
    explanation_notes: list[str]
    calculated_at: datetime = Field(default_factory=datetime.now)
```

### C. Salario Vacacional (Ley 16.101)
$$\text{Salario Vacacional} = \text{quantize}\left(\frac{\text{Sueldo Líquido Mensual}}{30} \times \text{Días de Licencia}, \text{Decimal('0.01')}\right)$$

---

## 6. Persistencia y Esquema de Base de Datos (PostgreSQL)

### Tabla `familias` (Ampliación)
```sql
ALTER TABLE familias 
ADD COLUMN IF NOT EXISTS modo_finanzas VARCHAR(30) DEFAULT 'basic';
```

### Nueva Tabla `labor_profiles`
```sql
CREATE TABLE IF NOT EXISTS labor_profiles (
    id SERIAL PRIMARY KEY,
    familia_id INTEGER NOT NULL REFERENCES familias(id) ON DELETE CASCADE,
    family_member_id INTEGER NOT NULL REFERENCES family_members(id) ON DELETE CASCADE,
    regimen VARCHAR(50) NOT NULL DEFAULT 'dependiente',
    actividad VARCHAR(100) NOT NULL DEFAULT 'Comercio / Servicios',
    fecha_inicio DATE NULL,
    fecha_fin DATE NULL,
    caja_previsional VARCHAR(50) NOT NULL DEFAULT 'bps',
    tipo_remuneracion VARCHAR(30) NOT NULL DEFAULT 'mensual',
    horas_semanales INTEGER NOT NULL DEFAULT 40,
    tiene_hijos_a_cargo BOOLEAN NOT NULL DEFAULT FALSE,
    tiene_conyuge_a_cargo BOOLEAN NOT NULL DEFAULT FALSE,
    aplica_fonasa BOOLEAN NOT NULL DEFAULT TRUE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_member_labor_profile UNIQUE (familia_id, family_member_id)
);

CREATE INDEX IF NOT EXISTS idx_labor_profiles_familia ON labor_profiles(familia_id);
```

### Tabla `incomes` (Ampliación No Destructiva)
```sql
ALTER TABLE incomes 
ADD COLUMN IF NOT EXISTS concept VARCHAR(50) DEFAULT 'salary',
ADD COLUMN IF NOT EXISTS labor_profile_id INTEGER REFERENCES labor_profiles(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_incomes_concept ON incomes(familia_id, concept);
```

---

## 7. Integración con el Asistente IA (Gemma 2:2b / Llama 70B)

### Protocolo de Construcción de Contexto (`ContextBuilder`)
Python ejecuta los cálculos determinísticos y genera una estructura limpia para el prompt:

```text
=== CONTEXTO LABORAL Y BENEFICIOS (CALCULADO POR PYTHON) ===
- Modo de Hogar: Contador Oriental (Pro)
- Miembro: Gonzalo
  * Régimen: Dependiente (Comercio) | Aporte: BPS
  * Antigüedad: Desde 01/01/2024 (6 meses computables en período actual)
  * Sueldo Líquido Habitual: $ 45.000 (UYU)
  * Aguinaldo Proyectado Junio 2026: $ 22.500 (Regla: UY-MTSS-SAC-2026-v1, Estado: CALCULATED)
    - Desglose: 6 meses devengados a $ 45.000 ($ 270.000 / 12)
  * Salario Vacacional Disponible (20 días): $ 30.000 estimado
============================================================
REGLA PARA LA IA:
- Utilizá los números anteriores de forma textual. NO hagas recálculos ni divisiones.
- Si el usuario pregunta por la normativa, explicá que el aguinaldo se rige por la Ley 12.840 y el salario vacacional por la Ley 16.101.
```

---

## 8. Roadmap de Implementación por Fases

| Fase | Alcance | Entregables |
|---|---|---|
| **Fase 1 (MVP)** | Dependiente + Sueldo + Aguinaldo + Vacacional | `LaborProfile`, `AguinaldoCalculator`, `VacationalCalculator`, `FinanceMode` selector, UI de perfil laboral y tests exhaustivos. |
| **Fase 2** | Retenciones y Desglose Nominal/Líquido | `FonasaCalculator` (3% a 8% con reglas de 2.5 BPC, cónyuge, hijos), Montepío 15%, FRL 0.1%. |
| **Fase 3** | Regímenes Independientes | Servicios Personales (IVA 22%/10%, IRPF Cat. II), Literal E (DGI fija), Monotributo MIDES, Pasividades (IASS). |
| **Fase 4** | Dataset Curado y Fine-Tuning | Creación de dataset uruguayo normativo supervisado y Fine-Tuning de Gemma 2:2b con Unsloth. |

---

## 9. Plan de Pruebas (`python-testing-spec`)

1. **Determinismo y Precisión Monetaria**:
   - Pruebas con importes con centésimos y validación de redondeo `ROUND_HALF_UP` en `Decimal`.
2. **Resistencia a Mutaciones**:
   - Tests que fallen si el divisor `Decimal("12")` se altera a `Decimal("10")` o `Decimal("6")`.
   - Tests que fallen si un mes no computable se suma al acumulador de aguinaldo.
3. **Casos Borde de Antigüedad y Período**:
   - Empleado con alta a mitad de período (ej. marzo para aguinaldo de junio).
   - Empleado con cese previo al pago.
   - Semestre completo con sueldos variables y horas extras.
4. **Invariante de Balance**:
   - Verificar que `DashboardView.balance_uyu` dé exactamente el mismo resultado con o sin proyecciones de aguinaldo calculadas.
5. **Aislamiento Multi-tenant**:
   - Probar que un cálculo de la Familia A nunca acceda a los ingresos o perfiles de la Familia B.
