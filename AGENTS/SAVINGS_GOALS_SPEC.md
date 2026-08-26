# SAVINGS_GOALS_SPEC.md — Metas de Ahorro Familiar e Integración Laboral Uruguaya

Esta especificación define la arquitectura, modelo de datos, motor de cálculo y flujos de usuario para **Metas de Ahorro Familiar** (*Savings Goals / Alcancías Familiares*), protegiendo la frontera con **Hogares Compartidos** e integrando las fuentes de ingreso de la legislación uruguaya.

---

## 1. Frontera de Dominio: Metas de Ahorro vs. Hogares Compartidos

Es crítico no solapar ambos conceptos:

| Dimensión | **Hogares Compartidos (Shared Expenses)** | **Metas de Ahorro (Savings Goals)** |
| :--- | :--- | :--- |
| **Propósito** | División de gastos y saldar deudas entre 2 o más grupos (ej: Vacaciones compartidas, asado de amigos, casa de playa). | Acumulación de capital y planificación financiera **interna de una sola familia**. |
| **Participantes** | Múltiples familias / Invitados externos con balances cruzados. | Los integrantes del propio núcleo familiar (Patricia, Admin Ponce, etc.). |
| **Flujo de Dinero** | *Quién le debe a quién* (Splitwise/Settle-up). | *Cuánto nos falta para la meta* (Alcancía / Aporte recurrente). |
| **Destino** | Cancelar un gasto ya realizado. | Financiar un objetivo futuro (Auto, Vacaciones, Fondo de Emergencia, Reformas). |

---

## 2. Fuentes de Fondeo por Régimen Laboral Uruguayo

El motor de proyección de ahorro calcula los tiempos para alcanzar una meta basándose en la naturaleza de los ingresos del hogar:

```
                          ┌─── Sueldo Líquido Mensual (Aporte fijo mensual)
                          ├─── Aguinaldo Legal Junio (Ley 12.840)
  1. Dependientes ────────┼─── Aguinaldo Legal Diciembre (Ley 12.840)
                          └─── Salario Vacacional Anual (Ley 16.101)

                          ┌─── Pasividad Líquida Mensual
  2. Jubilados / Pasivos ─┴─── Aguinaldo Pasividades Diciembre (BPS)

                          ┌─── Retiro / Ingreso Habitual Mensual
  3. Independientes ──────┼─── Excedente de Facturación / Trabajos Grandes
     (Monotributo,        └─── Anticipos de Honorarios / Cobros Extraordinarios
      Literal E, CJPPU)

  4. Transferencias ─────── Asignaciones Familiares / Subsidios MIDES
```

---

## 3. Modelo de Datos (PostgreSQL)

```sql
-- 1. Tabla de Metas de Ahorro
CREATE TABLE IF NOT EXISTS savings_goals (
    id SERIAL PRIMARY KEY,
    familia_id INTEGER NOT NULL REFERENCES familias(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,                    -- ej: "Cambio de Auto", "Vacaciones Brasil"
    target_amount NUMERIC(12, 2) NOT NULL,         -- Monto objetivo
    currency VARCHAR(3) NOT NULL DEFAULT 'UYU',    -- UYU o USD
    current_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00, -- Monto ya acumulado
    deadline DATE NULL,                            -- Fecha objetivo (opcional)
    category VARCHAR(50) NOT NULL DEFAULT 'general', -- 'vehicle', 'travel', 'emergency', 'home', 'education'
    icon VARCHAR(50) NOT NULL DEFAULT 'savings',
    color VARCHAR(30) NOT NULL DEFAULT '#6200EE',
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_savings_goals_familia ON savings_goals(familia_id);

-- 2. Asignación y Fondeos a la Meta (Transacciones a la Alcancía)
CREATE TABLE IF NOT EXISTS savings_goal_contributions (
    id SERIAL PRIMARY KEY,
    savings_goal_id INTEGER NOT NULL REFERENCES savings_goals(id) ON DELETE CASCADE,
    family_member_id INTEGER NULL REFERENCES family_members(id) ON DELETE SET NULL,
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'UYU',
    source_type VARCHAR(50) NOT NULL DEFAULT 'regular_income', 
    -- 'regular_income', 'aguinaldo_june', 'aguinaldo_december', 'vacation_pay', 'extra_invoice', 'manual_deposit'
    note VARCHAR(255) NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_goal_contributions_goal ON savings_goal_contributions(savings_goal_id);
```

---

## 4. Estrategias de Planificación y Simulación

El usuario puede configurar cómo financiar cada meta:

1. **Estrategia A — Aporte Fijo Mensual:**
   - La familia ahorra un importe fijo mensual de su balance disponible ($10.000/mes).
   - $\text{Meses estimados} = \frac{\text{Monto Restante}}{\text{Aporte Mensual}}$.

2. **Estrategia B — Destino Porcentual de Aguinaldos / Vacacionales (Dependientes/Pasivos):**
   - *"Destinar el 50% del aguinaldo de diciembre de Patricia ($5.000) y de Admin Ponce ($15.000)"*.
   - El motor toma el valor precalculado por `LaborCalculationEngine` y reduce el plazo automáticamente.

3. **Estrategia C — Excedente o Facturación Extra (Independientes / Monotributistas / Literal E):**
   - Asignar un % de cada cobro extraordinario o trabajo puntual registrado en `Incomes`.

4. **Estrategia D — Modo Mixto Inteligente:**
   - Combina ahorro mensual recurrente + inyección de aguinaldos legales en junio y diciembre.

---

## 5. Integración con el Asesor IA (Contador Oriental)

Cuando la familia pregunte sobre sus metas, el `AIAdvisorService` recibe el estado de las metas y los plazos precalculados:

```text
### METAS DE AHORRO DEL HOGAR ###
- Meta: "Vacaciones en Piriápolis Familiar" | Objetivo: $ 60.000 UYU | Acumulado: $ 25.000 (41.6%)
  * Faltante: $ 35.000 UYU
  * Con ahorro mensual actual ($ 5.000/mes): Se alcanza en 7 meses (Marzo 2027).
  * Con inyección del 50% del Aguinaldo de Diciembre ($ 20.000): Se alcanza en Enero 2027.
```

---

## 6. Pautas de Diseño e Interfaz (UI/UX)

1. **Ubicación Arquitectónica:** Integrado dentro de la vista **`📋 Mis Planes`**, manteniendo limpia la barra de navegación.
2. **Componentes Colapsables (ExpansionTile):** Cada meta se presenta en un acordeón desplegable que se abre y cierra para no saturar la pantalla cuando no se usa.
3. **Ícono Distintivo:** `ft.Icons.SAVINGS` (Alcancía / Chanchito 🐷).
4. **Paleta de Colores Tenues (Soft Pastels):**
   - Fondos suaves consistentes con el diseño de la app: `ft.Colors.PURPLE_50`, `ft.Colors.TEAL_50`, `ft.Colors.AMBER_50`.
   - Cero fondos blancos crudos o chillones.
   - Barras de progreso sutiles con indicadores porcentuales legibles.

---

## 7. Fases de Implementación Propuestas

1. **Fase 1 (Dominio y Base de Datos):** Modelos `SavingsGoal`, `GoalContribution`, migraciones SQL, repositorios y servicios con validación multimoneda (UYU/USD).
2. **Fase 2 (Motor de Simulación):** Algoritmo de proyección temporal integrando sueldos, aguinaldos y excedentes independientes.
3. **Fase 3 (Interfaz Flet en Mis Planes):** Paneles colapsables en tonos pastel con el ícono de alcancía 🐷, barras de progreso y modal *"Aportar a la meta"*.
4. **Fase 4 (Asesor IA):** Inyección del bloque de metas en el prompt del Contador Oriental para consultas de planificación y asesoramiento.
