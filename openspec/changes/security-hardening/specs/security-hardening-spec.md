# Especificación Técnica: Security Hardening & Isolation

## Requerimientos

### REQ-SEC-01: Aislamiento de Red de Base de Datos
- **Definición:** Ningún servicio de almacenamiento persistente (Postgres, pgvector, Neo4j) debe escuchar en interfaces de red públicas o de área local (`0.0.0.0`).
- **Criterio de Aceptación:** En `docker-compose.yml`, todos los mapeos de puertos de servicios de datos deben especificar explícitamente `127.0.0.1:puerto_host:puerto_contenedor` o no publicar puertos fuera de la red interna `auditor_network`.

### REQ-SEC-02: Delimitación Estructural de Entradas RAG y OCR
- **Definición:** Toda entrada de datos no confiable (texto transcrito por Tesseract OCR, textos de tickets, fragmentos de documentos vectorizados) debe estar encapsulada en delimitadores estructurales antes de su interpolación en el prompt del LLM.
- **Criterio de Aceptación:**
  - `ai_advisor_service.py` formatea los datos con `<datos_financieros>...</datos_financieros>`.
  - El prompt del sistema instruye al modelo a tratar el contenido entre estas etiquetas exclusivamente como valores numéricos y literales de gastos, sin interpretar comandos.

### REQ-SEC-03: Inmutabilidad de Contexto en Invocaciones Asíncronas
- **Definición:** Las corrutinas de chat en `AIController` y `AIAdvisorView` no deben compartir estado mutable de sesión entre llamadas concurrentes.
- **Criterio de Aceptación:** `AIContext` se retorna explícitamente como parte de `AIResponse` o se asocia un identificador único de mensaje (`message_id`) en lugar de almacenar `self.last_context` en la instancia del controlador.
