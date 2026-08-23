# Guía de Fine-Tuning para Gemma 2:2b con Unsloth — Contador Oriental

Bienvenido a tu primer fine-tuning. Esta guía te explica **paso a paso** y de manera conceptual cómo entrenar **Gemma 2:2b** para que entienda a la perfección la normativa laboral y tributaria de Uruguay, manteniendo la regla de oro: **Python calcula, la IA contextualiza y explica**.

---

## 1. ¿Qué es Unsloth y por qué lo usamos?

**Unsloth** es un framework de optimización de código abierto que acelera el entrenamiento de modelos de lenguaje (LLMs) entre **2x y 5x veces**, reduciendo el consumo de memoria VRAM en hasta un **70%** sin pérdida de precisión.

### Conceptos clave:
1. **QLoRA (Quantized Low-Rank Adaptation)**:
   - En lugar de reentrenar los 2.000 millones de parámetros de Gemma 2 (lo cual requeriría una GPU empresarial de $10.000 USD), congelamos el modelo base en **4 bits** y entrenamos únicamente una pequeña capa de adaptadores (matrices $A$ y $B$).
   - Esto permite hacer el fine-tuning en GPUs hogareñas o notebooks con 6 GB u 8 GB de VRAM en apenas 2 a 5 minutos.
2. **Invariante de Arquitectura**:
   - El modelo **nunca suma, resta ni inventa alícuotas**.
   - Aprende terminología, leyes uruguayas (Ley 12.840, Ley 18.083, Ley 20.124, etc.) y la obligación de incluir siempre el **descargo de responsabilidad legal**.

---

## 2. Los 4 Pasos del Proceso

```text
┌─────────────────────────────────┐
│ 1. Generar Dataset Curado       │ → scripts/build_fine_tuning_dataset.py
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ 2. Entrenar LoRA con Unsloth    │ → scripts/train_gemma2_unsloth.py
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ 3. Exportar a Formato GGUF      │ → models/gemma2_uruguay_gguf/unsloth.Q4_K_M.gguf
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ 4. Registrar en Ollama Local    │ → ollama create gemma2-contador-oriental -f Modelfile
└─────────────────────────────────┘
```

---

## 3. Guía Paso a Paso para Ejecutar

### Paso 1: Generar el Dataset Normativo
Ejecuta el generador que compila los ejemplos de entrenamiento con el descargo legal obligatorio:
```bash
uv run python scripts/build_fine_tuning_dataset.py
```
Esto creará el archivo `data/fine_tuning_normativo_uruguay.jsonl`.

---

### Paso 2: Preparar el Entorno de Unsloth

En tu máquina con GPU Nvidia (o Google Colab / WSL), instala Unsloth y sus dependencias:
```bash
pip install --upgrade pip
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
pip install --no-deps "xformers" "trl" "peft" "accelerate" "bitsandbytes"
```

---

### Paso 3: Ejecutar el Entrenamiento

Ejecuta el script de fine-tuning:
```bash
python scripts/train_gemma2_unsloth.py
```

El script automáticamente:
1. Descargará `unsloth/gemma-2-2b-it-bnb-4bit`.
2. Insertará los adaptadores LoRA (r=16, alpha=16).
3. Aplicará la plantilla de prompt de Gemma-2 (`<start_of_turn>user...`).
4. Entrenará durante 60 pasos con optimizador `adamw_8bit`.
5. Exportará el modelo cuantizado en formato **GGUF** (`Q4_K_M`) listo para Ollama en la carpeta `models/gemma2_uruguay_gguf/`.

---

### Paso 4: Crear el Modelo en Ollama

Crea un archivo llamado `Modelfile` con el siguiente contenido:

```dockerfile
FROM ./models/gemma2_uruguay_gguf/unsloth.Q4_K_M.gguf

PARAMETER temperature 0.2
PARAMETER top_p 0.9

SYSTEM """Sos el Contador Oriental, un asistente experto en finanzas de hogares y microemprendimientos en Uruguay. 
Explicas los cálculos provistos por el sistema de forma cálida, didáctica y clara en español rioplatense.
Nunca realizas cálculos matemáticos por tu cuenta; utilizas estrictamente los números provistos.
Toda explicación sobre impuestos, beneficios laborales o retenciones debe finalizar con el descargo de responsabilidad legal orientativo."""
```

Y luego regístralo en Ollama:
```bash
ollama create gemma2-contador-oriental -f Modelfile
```

---

### Paso 5: Probar el Modelo

Puedes interactuar directamente en tu terminal:
```bash
ollama run gemma2-contador-oriental
```

Y hacerle consultas con contexto inyectado como:
> *"Cobro $80.000 de jubilación BPS en 2026. ¿Por qué me descuentan IASS si el mínimo es de 9 BPC?"*

---

## 4. Trazabilidad y Descargo Legal Incorporado

Cada respuesta del modelo incluye automáticamente el aviso obligatorio:
> *Aviso: Este cálculo y explicación son de carácter meramente informativo y orientativo según la normativa vigente en Uruguay. No constituyen asesoramiento contable ni jurídico vinculante. Para decisiones formales o declaraciones juradas ante DGI/BPS/CJPPU, consulte a un profesional contable matriculado.*
