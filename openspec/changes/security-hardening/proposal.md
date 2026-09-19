# Propuesta de Refactorización: Hardening y Seguridad del Contador Oriental

**Fecha:** 2026-09-16  
**Origen:** Auditoría de Seguridad con `agentic-security-auditor` (MAESTRO 7-Layers)  
**Proyecto:** Auditor Familiar / Contador Oriental (`flet`)  
**Engram Anchor:** Memory #1256

---

## 1. Contexto y Justificación
Durante la auditoría de seguridad del proyecto `flet` se identificaron riesgos que no impiden el funcionamiento actual, pero que debilitan la postura de seguridad del sistema frente a ataques de red, inyecciones de prompt indirectas y condiciones de carrera concurrentes:

1. **Capa 4 MAESTRO (Infraestructura / Docker):** La base de datos vectorial PostgreSQL y la base de grafos Neo4j exponen puertos directamente en todas las interfaces de red (`0.0.0.0:5432`, `0.0.0.0:7474`), y el contenedor de PostgreSQL corre con privilegios `root` (UID 0) sin un sistema de archivos de sólo lectura.
2. **Capa 2 y 3 MAESTRO (Datos / Framework):** Los textos extraídos por OCR de tickets de compra y los fragmentos recuperados vía RAG de `pgvector` se concatenan en el prompt del LLM sin delimitadores estructurales explícitos, exponiendo al Contador Oriental a inyecciones indirectas si un ticket contiene instrucciones adversariales.
3. **Capa 3 MAESTRO (Concurrencia y Estado):** `AIController` mantiene estado mutable por instancia (`self.last_context`), generando ventanas de carrera temporal si se ejecutan consultas asíncronas en paralelo.

---

## 2. Alcance del Hardening Propuesto

### A. Aislamiento de Red e Infraestructura (Docker)
- Restringir la publicación de puertos de base de datos a loopback local (`127.0.0.1:${POSTGRES_PORT:-5442}:5432`).
- Evaluar la ejecución del contenedor de base de datos con usuario no-root y capacidades mínimas (`CAP_DROP`).

### B. Contención de Inyección de Prompt Indirecta (RAG / OCR)
- Envolver todos los datos provenientes de OCR y búsquedas vectoriales en etiquetas de delimitación estructurales XML/Markdown (ej. `<datos_financieros_origen_externo>...</datos_financieros_origen_externo>`).
- Ajustar el system prompt para que el modelo procese el contenido de esas etiquetas estrictamente como datos pasivos de cálculo, rechazando cualquier directiva que intente alterar su comportamiento.

### C. Desacoplamiento de Estado Concurrente (Controlador)
- Refactorizar `AIController` para que `last_context` no sea un atributo de instancia mutable global, sino un objeto de contexto atómico asociado al ciclo de vida del mensaje/request actual.

---

## 3. Impacto y Compatibilidad
- Los cambios son internos y de infraestructura; no alteran la interfaz de usuario de Flet ni las fórmulas de cálculo contable uruguayo.
- Requiere reiniciar los servicios Docker tras ajustar `docker-compose.yml`.
