"""
Script de Fine-Tuning con Unsloth para Gemma 2:2b (QLoRA de 4 bits).
Entrena el modelo sobre el dataset normativo uruguayo y exporta a GGUF para Ollama.
"""

import os
from pathlib import Path


def main():
    print("=" * 60)
    print("🚀 INICIANDO FINE-TUNING CON UNSLOTH (GEMMA 2:2B NORMATIVO UY)")
    print("=" * 60)

    try:
        from datasets import load_dataset
        from trl import SFTTrainer
        from transformers import TrainingArguments
        from unsloth import FastLanguageModel, is_bfloat16_supported
    except ImportError:
        print(
            "\n⚠️  Aviso: 'unsloth', 'trl' o 'transformers' no están instalados en este entorno."
        )
        print("Para ejecutar el entrenamiento con GPU, instala Unsloth siguiendo:")
        print("pip install \"unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git\"")
        print("pip install --no-deps \"xformers\" \"trl\" \"peft\" \"accelerate\" \"bitsandbytes\"\n")
        return

    max_seq_length = 2048
    dtype = None  # Auto detección de tipo (float16 o bfloat16)
    load_in_4bit = True  # Cuantización de 4 bits para entrenar en GPUs con poca VRAM (ej. 6GB-8GB)

    # 1. Cargar el modelo base pre-entrenado
    print("\n📦 Cargando modelo base Gemma 2:2b IT (4-bit)...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/gemma-2-2b-it-bnb-4bit",
        max_seq_length=max_seq_length,
        dtype=dtype,
        load_in_4bit=load_in_4bit,
    )

    # 2. Configurar adaptadores LoRA (Parameter-Efficient Fine-Tuning)
    print("\n⚙️ Configurando adaptadores LoRA...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,  # Rango de adaptación LoRA
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_alpha=16,
        lora_dropout=0,  # 0 es óptimo para Unsloth
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
        use_rslora=False,
        loftq_config=None,
    )

    # 3. Formateo de Prompt con Plantilla de Gemma-2
    gemma_prompt_template = """<start_of_turn>user
{instruction}

Información de contexto calculada por el sistema:
{input}<end_of_turn>
<start_of_turn>model
{output}<end_of_turn>"""

    def formatting_prompts_func(examples):
        instructions = examples["instruction"]
        inputs = examples["input"]
        outputs = examples["output"]
        texts = []
        for instruction, input_text, output in zip(instructions, inputs, outputs):
            text = gemma_prompt_template.format(
                instruction=instruction, input=input_text, output=output
            )
            texts.append(text)
        return {"text": texts}

    # 4. Cargar el Dataset Normativo
    dataset_path = Path("data/fine_tuning_normativo_uruguay.jsonl")
    if not dataset_path.exists():
        print(f"\n❌ Error: No se encontró el dataset en {dataset_path.resolve()}")
        print("Ejecuta primero: python scripts/build_fine_tuning_dataset.py")
        return

    print(f"\n📂 Cargando dataset desde {dataset_path}...")
    dataset = load_dataset("json", data_files=str(dataset_path), split="train")
    dataset = dataset.map(formatting_prompts_func, batched=True)

    # 5. Configurar el Entrenador SFT (Supervised Fine-Tuning)
    print("\n🎯 Configurando SFTTrainer...")
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        dataset_num_proc=2,
        packing=False,
        args=TrainingArguments(
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=5,
            max_steps=60,  # Cantidad de pasos óptima para datasets pequeños curados
            learning_rate=2e-4,
            fp16=not is_bfloat16_supported(),
            bf16=is_bfloat16_supported(),
            logging_steps=1,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            seed=3407,
            output_dir="outputs",
            report_to="none",
        ),
    )

    # 6. Ejecutar el Entrenamiento
    print("\n🔥 ¡Comenzando entrenamiento LoRA!")
    trainer_stats = trainer.train()
    print(f"\n✅ Entrenamiento completado. Stats: {trainer_stats}")

    # 7. Guardar el Modelo Ajustado y Exportar a GGUF para Ollama
    output_dir = "models/gemma2_uruguay_lora"
    print(f"\n💾 Guardando adaptadores LoRA en {output_dir}...")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    print("\n📦 Exportando a formato GGUF (Q4_K_M) para Ollama / Llama.cpp...")
    model.save_pretrained_gguf(
        "models/gemma2_uruguay_gguf",
        tokenizer,
        quantization_method="q4_k_m",
    )

    print("\n🎉 ¡PROCESO COMPLETADO CON ÉXITO!")
    print("Para importarlo en Ollama, crea un 'Modelfile':")
    print("  FROM ./models/gemma2_uruguay_gguf/unsloth.Q4_K_M.gguf")
    print("  ollama create gemma2-contador-oriental -f Modelfile")


if __name__ == "__main__":
    main()
