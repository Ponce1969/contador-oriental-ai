#!/usr/bin/env bash
# ==============================================================================
# Contador Oriental — Script de Benchmarking y Prueba de Voz (voice_api)
# Envía un archivo de audio (.m4a, .webm, .wav, .mp3) a voice_api
# midiendo Round-Trip Time (RTT), transcripción y extracción financiera.
# ==============================================================================
set -euo pipefail

DEFAULT_URL="http://localhost:8553/process-expense-voice"
API_URL="$DEFAULT_URL"
AUDIO_FILE=""

# Colores ANSI
if [ -t 1 ]; then
    C_RESET="\033[0m"
    C_BOLD="\033[1m"
    C_CYAN="\033[36m"
    C_GREEN="\033[32m"
    C_YELLOW="\033[33m"
    C_RED="\033[31m"
else
    C_RESET=""
    C_BOLD=""
    C_CYAN=""
    C_GREEN=""
    C_YELLOW=""
    C_RED=""
fi

show_help() {
    cat << EOF
Uso: $0 -f <RUTA_AUDIO> [OPCIONES]

Envía un archivo de audio al microservicio voice_api midiendo tiempo de respuesta (RTT),
tiempo de Faster-Whisper, tiempo de extracción NLP y datos financieros extraídos.

Opciones:
  -f, --file RUTA          Ruta al archivo de audio (WAV, MP3, M4A, WEBM, OGG) [REQUERIDO]
  -u, --url URL            URL del endpoint (default: $DEFAULT_URL)
  -t, --transcribe-only    Usar endpoint /transcribe solo para texto sin NLP
  -h, --help               Muestra esta ayuda y sale

Ejemplos:
  $0 -f audio_disco.m4a
  $0 -f gasto.wav -u http://192.168.1.50:8553/process-expense-voice
  $0 -f gasto.ogg --transcribe-only -u http://localhost:8553/transcribe
EOF
}

# Parseo de opciones
while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--file)
            AUDIO_FILE="$2"
            shift 2
            ;;
        -u|--url)
            API_URL="$2"
            shift 2
            ;;
        -t|--transcribe-only)
            API_URL="${API_URL/\/process-expense-voice/\/transcribe}"
            shift 1
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${C_RED}Opción desconocida: $1${C_RESET}" >&2
            show_help
            exit 1
            ;;
    esac
done

if [ -z "$AUDIO_FILE" ]; then
    echo -e "${C_RED}Error: Debe especificar un archivo de audio con -f / --file${C_RESET}" >&2
    show_help
    exit 1
fi

if [ ! -f "$AUDIO_FILE" ]; then
    echo -e "${C_RED}Error: El archivo no existe: $AUDIO_FILE${C_RESET}" >&2
    exit 1
fi

FILE_SIZE_KB=$(awk "BEGIN {printf \"%.1f\", $(wc -c < "$AUDIO_FILE") / 1024}")

echo -e "${C_BOLD}${C_CYAN}=== Benchmarking de Voz (Faster-Whisper + NLP) ===${C_RESET}"
echo -e "Audio:     ${C_YELLOW}$AUDIO_FILE${C_RESET} (${FILE_SIZE_KB} KB)"
echo -e "Endpoint:  ${C_YELLOW}$API_URL${C_RESET}"
echo -e "Enviando petición..."

TMP_OUT=$(mktemp)
trap 'rm -f "$TMP_OUT"' EXIT

START_TIME=$(date +%s%N 2>/dev/null || python3 -c 'import time; print(int(time.time()*1e9))')

HTTP_CODE=$(curl -s -S -o "$TMP_OUT" -w "%{http_code}" \
    -F "file=@$AUDIO_FILE" \
    "$API_URL" || echo "000")

END_TIME=$(date +%s%N 2>/dev/null || python3 -c 'import time; print(int(time.time()*1e9))')

ELAPSED_MS=$(awk "BEGIN {printf \"%.2f\", ($END_TIME - $START_TIME) / 1000000}")

echo ""
if [ "$HTTP_CODE" -eq 200 ]; then
    echo -e "${C_GREEN}${C_BOLD}[✓ 200 OK]${C_RESET} Latencia RTT total: ${C_BOLD}${ELAPSED_MS} ms${C_RESET}"
    echo -e "${C_CYAN}Respuesta JSON del microservicio:${C_RESET}"
    if command -v jq >/dev/null 2>&1; then
        jq . "$TMP_OUT"
    else
        cat "$TMP_OUT"
    fi
else
    echo -e "${C_RED}${C_BOLD}[✗ ERROR $HTTP_CODE]${C_RESET} Tiempo transcurrido: ${ELAPSED_MS} ms"
    cat "$TMP_OUT"
    exit 1
fi
