"""
Generador del dataset normativo uruguayo para Fine-Tuning de Gemma 2:2b con Unsloth.
Formato: Instruction-Following (Alpaca / ShareGPT) con descargo legal mandatorio.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LEGAL_DISCLAIMER = (
    "\n\n*Aviso: Este cálculo y explicación son de carácter meramente informativo "
    "y orientativo según la normativa vigente en Uruguay. No constituyen asesoramiento "
    "contable ni jurídico vinculante. Para decisiones formales o declaraciones juradas "
    "ante DGI/BPS/CJPPU, consulte a un profesional contable matriculado.*"
)

DATASET_ENTRIES: list[dict[str, Any]] = [
    # -------------------------------------------------------------
    # 1. TRABAJADORES DEPENDIENTES: AGUINALDO Y RETENCIONES
    # -------------------------------------------------------------
    {
        "instruction": "¿Cómo se calcula el aguinaldo de junio y qué normas se aplican en Uruguay?",
        "context": "Período: 1 de diciembre al 31 de mayo. Suma de ingresos computables en el semestre: $240.000 UYU. Divisor legal: 12.",
        "response": (
            "El Sueldo Anual Complementario (Aguinaldo) de junio se rige por la Ley 12.840 y "
            "decretos reglamentarios. Se calcula sumando todas las remuneraciones en dinero "
            "originadas en la relación laboral devengadas entre el 1 de diciembre y el 31 de mayo, "
            "y dividiendo ese total acumulado entre 12.\n\n"
            "En tu caso:\n"
            "- Remuneraciones devengadas en el semestre: $240.000 UYU.\n"
            "- Aguinaldo bruto nominal: $240.000 / 12 = $20.000 UYU.\n\n"
            "Sobre este monto bruto aplican los aportes a la seguridad social (Montepío 15%, "
            "FRL 0.1% y FONASA según tu situación familiar) y el IRPF correspondiente."
            + LEGAL_DISCLAIMER
        ),
    },
    {
        "instruction": "¿Por qué me descuentan FONASA y Montepío de mi salario y cuáles son las tasas?",
        "context": "Salario nominal: $60.000 UYU. Empleado soltero sin hijos. Año 2026. BPC = $7.036.",
        "response": (
            "En Uruguay, todo trabajador dependiente realiza aportes personales obligatorios a la "
            "Seguridad Social (BPS) sobre su salario nominal según las siguientes leyes:\n\n"
            "1. **Montepío (Aporte Jubilatorio - Ley 16.713 / Ley 20.130)**: Tasa del 15% sobre el nominal ($9.000 UYU).\n"
            "2. **FRL (Fondo de Reconversión Laboral - Ley 18.406)**: Tasa del 0.1% sobre el nominal ($60 UYU).\n"
            "3. **FONASA (Seguro Nacional de Salud - Ley 18.211)**: Para una persona soltera sin hijos con ingresos superiores a 2.5 BPC ($17.590 UYU), la alícuota es del 4.5% ($2.700 UYU).\n\n"
            "Total de retenciones a la seguridad social: $11.760 UYU (19.6% efectivo)."
            + LEGAL_DISCLAIMER
        ),
    },
    {
        "instruction": "¿Cómo funciona el cálculo del IRPF mensual y qué significa el 6% de incremento ficto por aguinaldo?",
        "context": "Sueldo nominal: $90.000 UYU. BPC 2026: $7.036 (Escala progresiva DGI). Sin hijos.",
        "response": (
            "El IRPF Categoría II (Rentas del Trabajo Dependiente) se liquida de forma mensual y "
            "progresiva por tramos de BPC (Ley 18.083 y Dec. 148/007).\n\n"
            "Para el cálculo del anticipo mensual, la normativa establece un incremento ficto del 6% "
            "sobre las retribuciones gravadas (Art. 63 Dec. 148/007), el cual anticipa mensualmente "
            "el impacto del aguinaldo para evitar que en junio y diciembre sufras un salto brusco de tramo.\n\n"
            "Luego se aplica la escala por franjas, se deducen los aportes a la seguridad social y cargas de familia "
            "(a una tasa del 14% si tus ingresos son hasta 15 BPC o del 8% si superan dicho umbral), resultando en "
            "la retención neta mensual que realiza tu empleador."
            + LEGAL_DISCLAIMER
        ),
    },

    # -------------------------------------------------------------
    # 2. SERVICIOS PERSONALES INDEPENDIENTES (IVA, IRPF, CJPPU)
    # -------------------------------------------------------------
    {
        "instruction": "Trabajo de forma independiente facturando servicios profesionales. ¿Qué impuestos debo liquidar y cómo se calcula el anticipo de IRPF?",
        "context": "Facturación neta bimestral sin IVA: $100.000 UYU. Gastos fictos (30%). Tasa anticipo: 10%. Retenciones sufridas: $2.000 UYU.",
        "response": (
            "Como prestador de Servicios Personales fuera de la relación de dependencia (Título 7 y Título 10 T.O. 1996), "
            "tenés las siguientes obligaciones tributarias principales:\n\n"
            "1. **IVA Servicios Personales**: Tasa básica general del 22% (o 10% en salud humana) sobre lo facturado.\n"
            "2. **Anticipo Bimestral de IRPF (Cat. II)**:\n"
            "   - Facturación neta del bimestre: $100.000 UYU.\n"
            "   - Deducción ficta de gastos (30% según Art. 34 Título 7): -$30.000 UYU.\n"
            "   - Base imponible computable (70%): $70.000 UYU.\n"
            "   - Anticipo orientativo (10% sobre base computable): $7.000 UYU.\n"
            "   - Menos retenciones sufridas en origen: -$2.000 UYU.\n"
            "   - **Neto a pagar a DGI por IRPF**: $5.000 UYU.\n\n"
            "Si tu cliente es una empresa CEDE o Gran Contribuyente, te retendrá preceptivamente el 60% del IVA devengado (Dec. 94/002)."
            + LEGAL_DISCLAIMER
        ),
    },
    {
        "instruction": "¿Cuánto tengo que pagar por mes a la Caja Profesional (CJPPU) si estoy en la Categoría 2?",
        "context": "Año 2026. Categoría 2 CJPPU. Sueldo ficto: $42.520 UYU. Tasa de aporte: 16.5%.",
        "response": (
            "La Caja de Jubilaciones y Pensiones de Profesionales Universitarios (CJPPU) establece la aportación "
            "obligatoria en base a 10 categorías de sueldos fictos trienales (Ley 17.738 Art. 60 y Ley 20.212).\n\n"
            "Para la **Categoría 2** en 2026:\n"
            "- Sueldo ficto mensual: $42.520 UYU.\n"
            "- Tasa de aportación: 16.5%.\n"
            "- **Aporte mensual obligatorio**: $7.015,80 UYU.\n\n"
            "Este aporte previsional se abona directamente a la CJPPU y es independiente de las obligaciones tributarias ante DGI."
            + LEGAL_DISCLAIMER
        ),
    },

    # -------------------------------------------------------------
    # 3. PEQUEÑA EMPRESA (LITERAL E)
    # -------------------------------------------------------------
    {
        "instruction": "¿Cuáles son los requisitos para estar en Literal E y cuánto se paga por mes?",
        "context": "Inicio de actividad: hace 6 meses (Año 1). Ventas anuales estimadas: 200.000 UI. Cuota base DGI: $5.450. BPS Patronal: $4.200.",
        "response": (
            "El régimen de Pequeña Empresa (Literal E del Art. 52, Título 4 T.O. 1996) es un régimen simplificado de DGI "
            "para micro y pequeños emprendimientos.\n\n"
            "**Requisitos y Topes**:\n"
            "- Las ventas brutas del ejercicio no pueden superar las **305.000 Unidades Indexadas (UI)** (aproximadamente $1.958.000 UYU al valor actual).\n"
            "- Si superás ese umbral, quedás automáticamente excluido y debés pasar al Régimen General (IRAE e IVA).\n\n"
            "**Escalonamiento de Pago (Ley 19.996 Art. 287)**:\n"
            "- **Año 1 (Meses 1 a 12)**: 25% de la cuota DGI ($1.362,50) + Cuota BPS patronal ($4.200) = **$5.562,50 UYU/mes**.\n"
            "- **Año 2 (Meses 13 a 24)**: 50% de la cuota DGI ($2.725,00) + BPS = **$6.925,00 UYU/mes**.\n"
            "- **Año 3 en adelante**: 100% de la cuota DGI ($5.450,00) + BPS = **$9.650,00 UYU/mes**."
            + LEGAL_DISCLAIMER
        ),
    },

    # -------------------------------------------------------------
    # 4. MONOTRIBUTO COMÚN Y SOCIAL MIDES
    # -------------------------------------------------------------
    {
        "instruction": "¿Qué diferencia hay entre el Monotributo Común y el Monotributo Social MIDES?",
        "context": "Monotributo unipersonal: local <= 15 m2, hasta 1 empleado. MIDES: Certificado de vulnerabilidad social, subsidio 4 años.",
        "response": (
            "Ambos regímenes unifican en un único tributo mensual las obligaciones de BPS y DGI (Ley 18.083 y Ley 18.874):\n\n"
            "1. **Monotributo Común**:\n"
            "   - Requisitos: Local no superior a 15 m² (o venta en vía pública/ferias), máximo 1 dependiente contratado y ventas anuales hasta 183.000 UI para unipersonales.\n"
            "   - Cuota: Se abona la cuota fija mensual unificada del 100% (aprox. $2.850 UYU).\n\n"
            "2. **Monotributo Social MIDES**:\n"
            "   - Requiere informe de evaluación social y certificado emitido por el MIDES para emprendimientos de personas en situación de vulnerabilidad socioeconómica.\n"
            "   - **Subsidio progresivo en 4 años**:\n"
            "     * Año 1: Paga el 25% de la cuota ($712,50 UYU).\n"
            "     * Año 2: Paga el 50% de la cuota ($1.425,00 UYU).\n"
            "     * Año 3: Paga el 75% de la cuota ($2.137,50 UYU).\n"
            "     * Año 4+: Paga el 100% de la cuota ($2.850,00 UYU).\n\n"
            "Es fundamental mantener el certificado MIDES vigente; de lo contrario, BPS liquida la cuota al 100%."
            + LEGAL_DISCLAIMER
        ),
    },

    # -------------------------------------------------------------
    # 5. PASIVIDADES, JUBILACIONES Y PENSIONES (IASS)
    # -------------------------------------------------------------
    {
        "instruction": "¿A partir de qué monto se paga IASS en las jubilaciones y cómo se calcula?",
        "context": "Año 2026. BPC = $7.036. Mínimo No Imponible: 9 BPC ($63.324). Jubilación nominal: $80.000 UYU. Deducción salud: 14%.",
        "response": (
            "El Impuesto de Asistencia a la Seguridad Social (IASS) grava los ingresos por jubilaciones, pensiones y "
            "pasividades en Uruguay (Ley 18.314 modif. por Ley 20.124):\n\n"
            "**Mínimo No Imponible (MNI)**:\n"
            "- A partir de la reforma de la Ley 20.124, el MNI es de **9 BPC mensuales** ($63.324 UYU en 2026). Si tu pasividad es menor o igual a esa cifra, estás totalmente exento de IASS.\n\n"
            "**Cálculo en tu caso ($80.000 UYU nominal)**:\n"
            "1. Excedente sobre las 9 BPC: $80.000 - $63.324 = $16.676 UYU.\n"
            "2. Tramo 2 (10% sobre el excedente de 9 a 15 BPC): $16.676 x 10% = $1.667,60 UYU de IASS bruto.\n"
            "3. Deducción por salud (14% sobre 0.5 BPC para ingresos <= 15 BPC): -$492,52 UYU.\n"
            "4. **IASS neto a retener**: $1.175,08 UYU.\n\n"
            "Si cobrás jubilación de BPS y además de otra caja paraestatal, ambas pasividades se consolidan para determinar la tasa marginal."
            + LEGAL_DISCLAIMER
        ),
    },
    {
        "instruction": "Cobro una jubilación de BPS de $60.000 y una pensión de la Caja Notarial de $40.000. ¿Cómo me afecta el IASS?",
        "context": "Jubilación BPS: $60.000. Pensión secundaria: $40.000. Total consolidado: $100.000. BPC 2026: $7.036 (MNI 9 BPC = $63.324).",
        "response": (
            "Cuando una persona percibe más de una pasividad, la normativa de DGI y BPS establece la **consolidación multicaixa**:\n\n"
            "- De forma aislada, tu jubilación de BPS ($60.000 UYU) no pagaría IASS porque no supera el mínimo de 9 BPC ($63.324 UYU).\n"
            "- Sin embargo, al sumar ambas pasividades el ingreso total mensual es de **$100.000 UYU** (~14.21 BPC).\n"
            "- El excedente gravable consolidado es de $36.676 UYU ($100.000 - $63.324), generando un IASS consolidado de $3.667,59 UYU.\n"
            "- Tras descontar la deducción de salud ($492,52 UYU), el impuesto neto conjunto es de $3.175,07 UYU.\n\n"
            "Cada organismo previsional te retendrá en tu recibo la cuota parte proporcional correspondiente a su haber (en tu recibo de BPS, el 60%: $1.905,04 UYU)."
            + LEGAL_DISCLAIMER
        ),
    },
]


def export_dataset_jsonl(output_path: str = "data/fine_tuning_normativo_uruguay.jsonl") -> None:
    """Genera el dataset en formato JSONL listo para Unsloth."""
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, "w", encoding="utf-8") as f:
        for item in DATASET_ENTRIES:
            # Formato estándar Alpaca / Unsloth
            alpaca_entry = {
                "instruction": item["instruction"],
                "input": item["context"],
                "output": item["response"],
            }
            f.write(json.dumps(alpaca_entry, ensure_ascii=False) + "\n")

    print(f"Dataset exportado exitosamente con {len(DATASET_ENTRIES)} ejemplos en: {out_file.resolve()}")


if __name__ == "__main__":
    export_dataset_jsonl()
