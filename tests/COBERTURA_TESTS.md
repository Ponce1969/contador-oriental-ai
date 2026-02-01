# Cobertura de Tests - Fleting

> **Estado:** 130 tests pasando | **Cobertura:** 85% | **Última actualización:** 2026-02-01

## 📊 Resumen General

```
Total Tests: 130
Cobertura:   85%
Estado:      ✅ Todos pasando
```

## 🗂️ Archivos de Tests

| Archivo | Tests | Descripción |
|---------|-------|-------------|
| `test_expense_model.py` | 9 | Tests del modelo Expense |
| `test_income_model.py` | 11 | Tests del modelo Income |
| `test_user_model.py` | 11 | Tests de User, UserCreate, UserLogin |
| `test_family_member_model.py` | 9 | Tests de FamilyMember e IncomeType |
| `test_shopping.py` | 3 | Tests de ShoppingItem |
| `test_expense_service.py` | 8 | Tests de ExpenseService |
| `test_income_service.py` | 7 | Tests de IncomeService |
| `test_auth_service.py` | 8 | Tests de AuthService |
| `test_family_member_service.py` | 14 | Tests de FamilyMemberService |
| `test_controllers.py` | 16 | Tests de AuthController, ExpenseController, IncomeController |
| `test_family_member_repository.py` | 5 | Tests de FamilyMemberRepository |
| `test_family_member_mappers.py` | 4 | Tests de mappers de family_member |
| `test_income_mappers.py` | 4 | Tests de mappers de income |
| `test_integration.py` | 4 | Tests de flujos completos |
| `test_edge_cases.py` | 7 | Tests de edge cases y validaciones |
| `test_utilities.py` | 6 | Tests de configuración y utilidades |

## ✅ Tests por Categoría

### Models (52 tests)
- **Expense:** Creación, validación, defaults, categorías, recurrencia
- **Income:** Creación, validación, defaults, categorías, recurrencia
- **User:** Creación, timestamps, validación, login
- **FamilyMember:** Propiedades, tipos de ingreso, defaults
- **ShoppingItem:** Creación, validación, estado

### Services (44 tests)
- **ExpenseService:** CRUD, validaciones, totales mensuales, resumen por categorías
- **IncomeService:** CRUD, validaciones, totales mensuales, resumen por categorías
- **AuthService:** Registro, login, cambio de password, validaciones
- **FamilyMemberService:** CRUD, validaciones de sueldo, listados

### Controllers (16 tests)
- **AuthController:** Login exitoso/fallido, validaciones
- **ExpenseController:** CRUD, filtros, totales, resúmenes
- **IncomeController:** CRUD, filtros por miembro, totales, resúmenes

### Repositories (29 tests)
- **FamilyMemberRepository:** CRUD, filtros, soft delete
- **Mappers:** Conversión domain ↔ table para expenses, incomes, family_members

### Integration (4 tests)
- Flujo completo de registro de usuario
- Tracking de gastos
- Tracking de ingresos
- Cálculo de balance presupuestario

### Edge Cases (7 tests)
- Validaciones de montos (0, negativos)
- Descripciones vacías
- Usuarios duplicados
- Recurrentes sin frecuencia
- Recursos no existentes

## 📈 Cobertura por Módulo

| Módulo | Cobertura | Estado |
|--------|-----------|--------|
| models/ | 87-100% | ✅ Excelente |
| services/ | 78-94% | ✅ Bueno |
| controllers/ | 84-96% | ✅ Bueno |
| repositories/ | 67-100% | ✅ Bueno |
| configs/ | 95% | ✅ Excelente |
| core/ | 85% | ✅ Bueno |

## 🎯 Próximos Pasos (Sugeridos)

### Para alcanzar 90%:
- [ ] Tests para `shopping_service.py` (0% → 85%)
- [ ] Tests para `shopping_repository.py` (86% → 100%)
- [ ] Tests para `family_member_mappers.py` (67% → 85%)
- [ ] Tests de error handling en controllers

### Mejoras:
- [ ] Tests de performance (tiempos de respuesta)
- [ ] Tests de concurrencia (si aplica)
- [ ] Tests de UI con Flet (si es posible)
- [ ] Mock de dependencias externas

## 🚀 Comandos Útiles

```bash
# Ejecutar todos los tests
uv run pytest tests/

# Ejecutar con cobertura
uv run pytest tests/ --cov=. --cov-report=term

# Reporte HTML
uv run pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html

# Ejecutar un archivo específico
uv run pytest tests/test_expense_service.py -v

# Ejecutar con verbose
uv run pytest tests/ -v
```

## 📝 Notas

- Los tests usan **SQLite en memoria** para aislamiento
- Cada test tiene su propia sesión de BD (transaccional)
- Fixtures en `conftest.py` proporcionan datos de prueba
- Tests de integración verifican flujos completos

---

**Mantenido por:** Equipo de desarrollo Fleting  
**Próxima revisión:** Continuar con tests faltantes para 90%+
