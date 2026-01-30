# 🛒 Smart Shopping List

Aplicación de escritorio construida con **Python 3.12**, **Flet**, **Fleting** y **arquitectura MVC**, pensada como una base sólida y escalable para evolucionar hacia un **auditor personal/familiar de gastos mensuales**.

Este proyecto no es un ejemplo trivial: está diseñado siguiendo **buenas prácticas profesionales**, con tipado estricto, separación de responsabilidades y manejo explícito de errores mediante `Result[T, E]`.

**🚀 Basado en Fleting Framework** - Micro framework MVC para Flet con routing automático, layouts consistentes y CLI productiva.

---

## 🎯 Objetivo del proyecto

El objetivo inicial es construir una **lista de compras persistente**, que permita:

* Registrar productos comprados día a día
* Guardarlos en una base de datos
* Consultarlos posteriormente

A partir de esta base, la aplicación podrá evolucionar hacia:

* Totales de gasto mensual
* Comparación de precios por producto
* Detección de hábitos de consumo
* Auditoría completa de gastos (comida, vehículo, servicios, etc.)

---

## 🧱 Principios técnicos

Este proyecto sigue de forma estricta los siguientes principios:

* **Python moderno (3.12)**
* **Tipado estático estricto** (sin `Any`)
* **Arquitectura MVC real con Fleting**
* **Dominio desacoplado de la infraestructura**
* **Sin `try/except` para flujo normal**
* **Errores como valores (`Result[T, E]`)**

La aplicación está pensada para crecer sin necesidad de reescrituras importantes.

---

## 🧩 Arquitectura general (MVC)

La aplicación se divide en capas claras:

### Model

* Modelos de dominio con **Pydantic**
* Representan conceptos del negocio (ej: `ShoppingItem`)
* No conocen ni la UI ni la base de datos

### View

* Construida con **Flet**
* Solo se encarga de mostrar información y capturar eventos
* No contiene lógica de negocio ni SQL

### Controller

* Orquesta la comunicación entre la vista y los servicios
* No toma decisiones de negocio

### Service

* Contiene las reglas del dominio
* Valida invariantes
* Devuelve `Result` en lugar de lanzar excepciones

### Repository

* Encapsula el acceso a la base de datos
* Traduce entre ORM y dominio
* Aísla completamente SQLAlchemy

---

## 📂 Estructura del proyecto

```text
├── main.py                 # Punto de entrada de la aplicación (Fleting)
├── models/                 # Modelos de dominio (Pydantic)
│   ├── shopping_model.py
│   └── errors.py
├── views/                  # Vistas Flet (UI)
│   └── pages/
│       ├── shopping_view.py
│       ├── home_view.py
│       └── settings_view.py
├── controllers/            # Controladores MVC
│   └── shopping_controller.py
├── services/               # Lógica de negocio
│   └── shopping_service.py
├── repositories/           # Persistencia
│   ├── shopping_repository.py
│   └── mappers.py
├── database/               # Infraestructura de base de datos
│   ├── engine.py
│   ├── base.py
│   └── tables.py
├── core/                   # Núcleo de Fleting
│   ├── sqlalchemy_session.py
│   └── database.py
├── configs/                # Configuraciones
│   ├── routes.py
│   └── app_config.py
└── flet_types/             # Tipos correctos para Flet
    └── flet_types.py
```

---

## 🗄️ Base de datos

* Base de datos: **SQLite**
* ORM: **SQLAlchemy 2.0**
* Estilo declarativo moderno

La base de datos se crea automáticamente al iniciar la aplicación.

El dominio **no depende del ORM**: se utilizan mappers explícitos para traducir entre tablas y modelos Pydantic.

---

## ⚠️ Manejo de errores

En lugar de excepciones, el proyecto utiliza el tipo:

```python
Result[T, E]
```

Donde:

* `T` es el valor esperado
* `E` es un error explícito del dominio o la infraestructura

Esto permite:

* Código predecible
* Tests más simples
* UI sin `try/except`

---

## 🚀 Flujo actual de la aplicación

1. El usuario interactúa con la **vista Flet**
2. La vista envía eventos al **controller**
3. El controller llama al **service**
4. El service valida reglas y delega al **repository**
5. El repository persiste en SQLite y devuelve un `Result`
6. La vista reacciona al resultado

---

## 🛣️ Roadmap de evolución

### Fase 1 (actual)

* Lista de compras persistente
* Crear y listar ítems

### Fase 2

* Marcar productos como comprados
* Eliminar productos

### Fase 3

* Totales diarios y mensuales
* Agrupación por categorías

### Fase 4

* Comparación histórica de precios
* Detección de consumo excesivo

### Fase 5

* Gastos no relacionados a compras
* Auditor mensual completo

---

## 🧠 Público objetivo

* Personas que quieren controlar sus gastos
* Familias
* Desarrolladores Python que quieran aprender:

  * Flet
  * Arquitectura limpia
  * Tipado moderno

---

## 🚀 Flujo actual de la aplicación

1. El usuario interactúa con la **vista Flet** (routing automático de Fleting)
2. La vista envía eventos al **controller**
3. El controller llama al **service** usando sesión de SQLAlchemy
4. El service valida reglas y delega al **repository**
5. El repository persiste en SQLite y devuelve un `Result`
6. La vista reacciona al resultado

---



## ✅ Estado actual

✔ ✅ **Migración a Fleting completada**
✔ ✅ **Base de datos conectada y funcional**
✔ ✅ **Arquitectura MVC con tipado estricto**
✔ ✅ **Routing automático funcionando**
✔ ✅ **Vista de shopping operativa**

**🎯 Proyecto listo para escalar con Fleting!**
