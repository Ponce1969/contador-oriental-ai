Plan Estratégico: AI Contador Familiar (Uruguay)
1. Visión General

Implementación de un asistente contable local integrado en un micro-framework Fleting (Flet). El objetivo es asesorar a familias en Uruguay sobre sus gastos, basándose en normativas locales y leyes vigentes.
2. El Modelo (El "Cerebro")

    Modelo: gemma2:2b (vía Ollama).

    Justificación: Modelo ligero y eficiente para ejecución local en Orange Pi 5 Plus (ARM) y PC MSI (GPU). Su tamaño reducido requiere un contexto muy limpio para evitar alucinaciones.

3. Estrategia de RAG Curado (Sin Base Vectorial)

Para maximizar la precisión de gemma2:2b y reducir el ruido, evitaremos el uso de bases de datos vectoriales (embeddings) para el conocimiento legal.

    Repositorio de Conocimiento: 9 archivos Markdown (.md).

    Restricciones: Máximo 200 líneas por archivo para garantizar que entren en la ventana de contexto del modelo.

    Temática (Uruguay): IRPF, Ley de Inclusión Financiera, IVA, Consejos de Ahorro en UI, etc.

    Mecanismo de Selección: 1.  El sistema analiza la consulta del usuario (Keyword Search/Metadata).
    2.  Selecciona el archivo .md más relevante.
    3.  Inyecta el contenido íntegro del archivo en el Prompt como contexto primario.

4. Integración de Datos (PostgreSQL)

    Fuente de Datos Dinámica: La base de datos auditor_familiar_db (PostgreSQL 16).

    Rol de la DB: Almacenar transacciones reales de la familia (monto, fecha, categoría).

    Flujo del Asistente:

        Input: Pregunta del usuario + Datos de gastos de la DB (PostgreSQL).

        Contexto: Información legal curada (Markdown seleccionado).

        Output: Respuesta de Gemma 2:2b actuando como Contador Uruguayo.

5. Arquitectura de Despliegue (Docker)

    App: Contenedor Python (Fleting) en puerto 8550.

    DB: Contenedor PostgreSQL 16.

    AI: Ollama corriendo como servicio Host (para acceso directo a GPU/NPU).

Instrucción para Cascade:

    "Cascade, usaremos este documento como guía para las futuras tareas de implementación. Tu prioridad es mantener el código simple, evitar librerías de vectores innecesarias y enfocarte en la lectura de archivos Markdown locales para alimentar el prompt de Gemma 2:2b."



inclusion_financiera_uy.md:

Guía: Ley de Inclusión Financiera y Beneficios (Uruguay)
1. Reducción de IVA en Compras

El mayor beneficio para el ahorro familiar en Uruguay es la reducción de puntos de IVA al utilizar medios de pago electrónicos (Ley N° 19.210).

    Tarjetas de Débito e Instrumentos de Dinero Electrónico: Reducción de 2 puntos porcentuales de IVA en compras generales (tasa básica del 22% pasa a 20% y mínima del 10% pasa a 8%).

    Tarjetas de Crédito: No aplican para la reducción general de 2 puntos, salvo en promociones específicas o rubros gastronómicos/turísticos.

2. Beneficios en Gastos de Restaurantes y Turismo

Para el rubro "Esparcimiento" y "Gastronomía", el beneficio es mayor para fomentar el sector:

    Descuento de 9 puntos de IVA: Aplica en servicios gastronómicos (restaurantes, bares, cafeterías) y catering para eventos, siempre que se pague con tarjeta de débito, crédito o dinero electrónico.

3. Pagos de Servicios e Impuestos

    Débitos Automáticos: Fomentar el uso de débitos automáticos en cuentas bancarias para el pago de facturas de entes públicos (UTE, OSE, ANTEL) suele otorgar bonificaciones anuales por buen pagador, variando según el ente.

4. Consejos del Contador para la Familia

    Priorizar Débito: Para compras de supermercado y farmacia, usar siempre Débito para asegurar el 2% de ahorro inmediato.

    Cena fuera: Al salir a comer, cualquier tarjeta (Crédito o Débito) sirve para obtener el 9% de descuento, lo que impacta significativamente en el presupuesto mensual de ocio.

    Alquileres: Los pagos de alquiler mayores a 40 BPC anuales deben realizarse mediante transferencia bancaria o acreditación en cuenta para ser legalmente válidos y poder aplicar a la devolución de IRPF por alquiler.

Instrucciones para la implementación en el código:

Cuando Cascade o tu lógica de Python lea este archivo, el Prompt que le envíes a Gemma debería estructurarse así:
Python

# Pseudo-código de ejemplo
contexto = leer_archivo("inclusion_financiera_uy.md")
pregunta_usuario = "¿Me conviene pagar el súper con crédito o débito?"

prompt = f"""
Eres un contador experto en Uruguay. 
Utiliza el siguiente contexto legal para responder la duda de la familia:
---
{contexto}
---
Pregunta: {pregunta_usuario}
Respuesta breve y profesional:
"""


irpf_familia_uy.md :

Guía: IRPF y Deducciones para el Núcleo Familiar (Uruguay)
1. Naturaleza del Impuesto

El IRPF es un impuesto directo que grava las rentas de fuente uruguaya obtenidas por personas físicas residentes. Se aplica de forma progresiva mediante franjas de ingresos.
2. Deducciones por Hijos y Personas a Cargo

Las familias pueden reducir el monto a pagar mediante deducciones anuales fijas:

    Hijos menores de 18 años: Se permite deducir un monto anual fijo por cada hijo a cargo (aproximadamente 20 BPC al año).

    Hijos con discapacidad: La deducción se duplica en casos de hijos con discapacidad, sin importar la edad.

    Deducción compartida: Si ambos padres tributan IRPF, pueden optar por dividir la deducción (50% cada uno) o que uno solo la aplique al 100%.

3. Crédito por Alquiler de Vivienda Permanente

Las familias que alquilan su hogar pueden recuperar parte del dinero pagado:

    Monto del beneficio: Se puede imputar como pago del IRPF el 6% del precio del alquiler efectivamente pagado durante el año civil.

    Requisitos: El contrato debe estar por escrito, tener un plazo mayor a un año y los pagos deben ser comprobables (transferencia o depósito).

    Identificación: Es obligatorio identificar al arrendador (dueño o inmobiliaria) con nombre y RUT/CI.

4. Deducción por Cuotas de Préstamos Hipotecarios

Si la familia compró su vivienda mediante préstamo bancario (BHU, bancos privados):

    Condición: Solo aplica para vivienda única y permanente.

    Límite: Existe un tope anual de deducción (aprox. 36 BPC) siempre que el valor de la vivienda no supere las 794.000 UI al momento de la compra.

5. Notas para el Contador (Gemma 2:2b)

    Mínimo no imponible: No todos los ingresos pagan; existe una franja exenta que se ajusta anualmente según la BPC (Base de Prestaciones y Contribuciones).

    Declaración Jurada: Muchas familias con un solo trabajo no están obligadas a declararlo, pero les conviene hacerlo si tienen alquileres para cobrar la devolución.

Por qué este archivo ayudará a tu Contador local:

    Contexto Específico: Si el usuario dice "Tengo dos hijos y alquilo", el sistema abrirá este archivo y Gemma sabrá que debe mencionar las 20 BPC por hijo y el 6% del alquiler.

    Detección de Oportunidades: Gemma podrá sugerir: "Recuerda que como pagas alquiler, en julio podrías pedir la devolución del 6% ante la DGI".

Siguiente paso con Cascade:

Ya tenemos dos archivos clave (inclusion_financiera_uy.md e irpf_familia_uy.md). crea una carpeta llamada knowledge/ en tu proyecto de Fleting y guarde estos archivos allí.


ahorro_ui_uy.md:

Guía: Ahorro en Unidades Indexadas (UI) en Uruguay
1. ¿Qué es la Unidad Indexada (UI)?

La UI es una unidad de valor que se ajusta diariamente según la variación del Índice de Precios al Consumo (IPC). Su objetivo es mantener el poder adquisitivo del dinero frente a la inflación en Uruguay.
2. Ventajas del Ahorro en UI

    Protección contra la Inflación: A diferencia del peso uruguayo nominal, un ahorro en UI no pierde valor cuando los precios suben; el capital se ajusta automáticamente.

    Estabilidad frente al Dólar: Para gastos locales (como la compra de una vivienda o educación en Uruguay), la UI es más estable y segura que el dólar, que puede sufrir volatilidades bruscas.

3. Instrumentos Comunes de Ahorro

    Cuentas de Ahorro en UI: La mayoría de los bancos (BROU, bancos privados) permiten abrir cajas de ahorro donde el saldo se expresa en UI.

    Plazos Fijos en UI: Depósitos a término (generalmente mínimo de 6 meses o un año) que ofrecen una pequeña tasa de interés anual por encima del ajuste por inflación.

    Letras de Regulación Monetaria: Instrumentos emitidos por el Banco Central del Uruguay (BCU) accesibles a través de corredores de bolsa o bancos, a menudo con mejores tasas que las cuentas comunes.

4. Consejos del Contador para la Familia

    Fondo de Reserva: Se recomienda mantener el fondo de emergencia de la familia en UI si no se planea usar en los próximos 6 a 12 meses.

    Metas de Largo Plazo: Para el ahorro destinado a la compra de una vivienda o el futuro de los hijos, la UI es el instrumento más recomendado por la normativa uruguaya para evitar la desvalorización.

    Consulta de Valor: El valor de la UI cambia todos los días y es publicado oficialmente por el Instituto Nacional de Estadística (INE).

Cómo este archivo potencia a tu Agente:

Con este conocimiento, si una familia le pregunta a Gemma: "¿Qué hago con los 50.000 pesos que me sobraron este mes?", el modelo podrá responder:

    "Como contador, te sugiero considerar la apertura de una cuenta en Unidades Indexadas (UI). Esto protegerá tu dinero de la inflación en Uruguay, asegurando que tus ahorros mantengan su valor real a lo largo del tiempo."



Ya tienes la trilogía base para el RAG Curado:

    inclusion_financiera_uy.md (Ahorro en compras/IVA).

    irpf_familia_uy.md (Impuestos y devoluciones).

    ahorro_ui_uy.md (Protección del capital).

Deberiamos mejorar todo el contenido con mas ejemplos y explicaciones mas detalladas, aqui solo mostre un ejemplo de cada archivo, sabiendo que el rag curado esta en la carpeta knowledge, no debe pasar de 200 lineas de codigo, para que un modelo local pequeño pueda aprender de esta informacion.


-----------------
La función "Selectora de Conocimiento"
teniendo en cuenta que el despliege se hace en un servidor oranpi5 plus de 16 gigas de ram.

Este código es el que conectará tu app de Flet con los archivos Markdown y Ollama.
Python

import os

def obtener_contexto_curado(pregunta_usuario):
    # Definimos el mapa de conocimientos
    mapa_conocimiento = {
        "ahorro_ui_uy.md": ["ahorro", "ui", "unidades indexadas", "inflación", "invertir", "plazo fijo"],
        "irpf_family_uy.md": ["irpf", "impuestos", "hijos", "alquiler", "deducciones", "dgi", "devolución"],
        "inclusion_financiera_uy.md": ["iva", "tarjeta", "débito", "crédito", "descuento", "restaurante", "compras"]
    }
    
    carpeta_knowledge = "./knowledge"
    pregunta_lower = pregunta_usuario.lower()
    
    # Buscamos el archivo más relevante
    archivo_seleccionado = None
    for archivo, palabras_clave in mapa_conocimiento.items():
        if any(palabra in pregunta_lower for palabra in palabras_clave):
            archivo_seleccionado = archivo
            break
    
    # Si encontramos un archivo, leemos su contenido
    if archivo_seleccionado:
        ruta = os.path.join(carpeta_knowledge, archivo_seleccionado)
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read()
    
    return "No hay un marco legal específico seleccionado, responde basándote en conocimientos generales de contabilidad uruguaya."

3. El Prompt Final para Gemma 2:2b

Ahora, cuando Cascade configure la llamada a Ollama, el prompt debe verse así para que Gemma no "alucine":
Python

def generar_respuesta_contador(pregunta_usuario):
    contexto = obtener_contexto_curado(pregunta_usuario)
    
    prompt_final = f"""
    SISTEMA: Eres un Contador Público experto en la normativa de Uruguay. 
    Tu objetivo es ayudar a las familias con un lenguaje claro pero profesional.
    
    CONTEXTO LEGAL URUGUAYO:
    {contexto}
    
    PREGUNTA DEL USUARIO:
    {pregunta_usuario}
    
    INSTRUCCIÓN: Responde la pregunta basándote estrictamente en el CONTEXTO LEGAL proporcionado si es relevante. 
    Si la información no está en el contexto, usa tu conocimiento general sobre Uruguay.
    """
    
    # Aquí iría la llamada a Ollama pasando prompt_final
    # response = ollama.generate(model='gemma2:2b', prompt=prompt_final)

¿Por qué esto es mejor para tu Orange Pi 5?

    Velocidad de Rayo: No hay búsqueda matemática en vectores, solo lectura de archivos de texto.

    Contexto Puro: Al inyectar el Markdown entero (que mide menos de 200 líneas), Gemma tiene la "ley en la mano" mientras responde.

    Memoria Local: Al no usar servicios externos, todo se queda en tu servidor Linux.



📂 Nueva Estructura Sugerida

Debes añadir estos archivos en las siguientes ubicaciones para que el sistema sea escalable:
Plaintext

├── knowledge/                        # 📂 Nueva: RAG Curado (Archivos Markdown)
│   ├── inclusion_financiera_uy.md    # Ley 19.210 y beneficios IVA
│   ├── irpf_familia_uy.md            # Deducciones hijos/alquiler
│   └── ahorro_ui_uy.md               # Conceptos de Unidades Indexadas
├── services/
│   ├── ...
│   └── ai_advisor_service.py         # 📄 Nuevo: Lógica de selección de MD y Ollama
├── models/
│   ├── ...
│   └── ai_model.py                   # 📄 Nuevo: Esquemas Pydantic para el Chat
├── views/pages/
│   └── ai_advisor_view.py            # 📄 Nuevo: Interfaz de Chat con el Contador
└── controllers/
    └── ai_controller.py              # 📄 Nuevo: Orquestador Vista ↔ Servicio IA

🛠️ Responsabilidades por Capa (Arquitectura IA)

Para mantener tus Principios Técnicos (Tipado estricto y Result[T, E]), así es como deben trabajar estos archivos:
1. knowledge/ (Data estática)

Son tus archivos de texto. Cascade debe tratarlos como archivos de solo lectura. No son base de datos, son el contexto directo para el prompt.
2. services/ai_advisor_service.py

Este es el "corazón" del RAG.

    Función: Leer los archivos de knowledge/, seleccionar el correcto basándose en palabras clave y enviar el prompt a la API local de Ollama.

    Retorno: Debe devolver un Result[str, AIError] para seguir tu estándar de manejo de errores.

3. controllers/ai_controller.py

    Función: Recibe la pregunta de la view, llama al AIAdvisorService y, si es necesario, consulta al ExpenseService para pasarle a la IA los gastos reales de la familia desde PostgreSQL.

    Integración: Aquí es donde el Contador IA se vuelve "inteligente", porque el controlador puede darle a Gemma tanto la Ley como los Datos Reales de la base de datos.

4. views/pages/ai_advisor_view.py

    Interfaz: Un componente de chat limpio en Flet donde el usuario pregunta y recibe la respuesta de Gemma 2:2b.

🔄 El Flujo de Datos del Contador

    Usuario pregunta en ai_advisor_view.

    Controller detecta la intención. Si pregunta por ahorros, el controller pide los gastos del mes al ExpenseRepository.

    Service busca en knowledge/ahorro_ui_uy.md.

    Prompt Final: Se envía a Gemma 2:2b (Ollama) un texto que combina: "Contexto Legal" + "Gastos Reales de la Familia" + "Pregunta".

    Resultado: Gemma responde con precisión quirúrgica sobre la realidad de esa familia en Uruguay.