# Tareas de Implementación: Security Hardening & Isolation

## Fase 1: Hardening de Infraestructura Docker
- [x] Modificar `docker-compose.yml` para vincular PostgreSQL a `127.0.0.1:${POSTGRES_PORT:-5442}:5432`.
- [x] Verificar que Neo4j (si aplica en compose) no exponga puertos fuera de `127.0.0.1` (no presente en compose).
- [x] Probar conectividad interna de la app Flet hacia Postgres en la red `auditor_network`.

## Fase 2: Delimitadores contra Inyección Indirecta
- [x] Actualizar formateadores de prompt en `services/ai/ai_advisor_service.py` para encerrar contexto de gastos y OCR en `<datos_financieros>`.
- [x] Actualizar el system prompt en `ocr_api/main.py` / `ai_advisor_service.py` con directivas explícitas de tratamiento pasivo de datos delimitados.
- [x] Crear test unitario en `tests/test_ai_advisor_security.py` verificando delimitación estructural y tratamiento pasivo de datos.

## Fase 3: Aislamiento de Estado Concurrente
- [x] Refactorizar `AIController` para recibir y retornar `AIContext` de forma funcional y desacoplada de la instancia (removidos `self.last_context` y `self.last_pregunta`).
- [x] Actualizar `AIResponse` para encapsular `context: AIContext | None` de forma inmutable.
