#!/usr/bin/env bash
# ==============================================================================
# Auditor Familiar — Script de Benchmarking y Medición RTT para OCR API
# Invoca /upload-ocr midiendo Round-Trip Time (RTT) y telemetría del backend.
# ==============================================================================
set -euo pipefail

DEFAULT_URL="http://localhost:8551/upload-ocr"
API_URL="$DEFAULT_URL"
ENGINE="local"
FAMILIA_ID=1
IMAGE_FILE=""

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
Uso: $0 -f <RUTA_IMAGEN> [OPCIONES]

Envía una imagen al microservicio OCR midiendo latencia de red (RTT)
y telemetría de inferencia (CPU, RAM RSS, resoluciones).

Opciones:
  -f, --file RUTA          Ruta a la foto del ticket (JPG, PNG, WEBP) [REQUERIDO]
  -e, --engine MOTOR       Motor OCR a utilizar: local | auto | cloud (default: local)
  -u, --url URL            URL del endpoint (default: $DEFAULT_URL)
  -i, --familia-id ID      ID de familia (default: 1)
  -h, --help               Muestra esta ayuda y sale

Ejemplos:
  $0 -f /home/orangepi/tickets/ticket_disco.jpg
  $0 -f ticket.png -e local -u http://192.168.1.50:8551/upload-ocr
EOF
}

# Parseo de opciones
while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--file)
            IMAGE_FILE="$2"
            shift 2
            ;;
        -e|--engine)
            ENGINE="$2"
            shift 2
            ;;
        -u|--url)
            API_URL="$2"
            shift 2
            ;;
        -i|--familia-id)
            FAMILIA_ID="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${C_RED}Opción no reconocida: $1${C_RESET}" >&2
            show_help
            exit 1
            ;;
    esac
done

if [ -z "$IMAGE_FILE" ]; then
    echo -e "${C_RED}Error: Debe especificar un archivo de imagen con -f o --file${C_RESET}" >&2
    show_help
    exit 1
fi

if [ ! -f "$IMAGE_FILE" ]; then
    echo -e "${C_RED}Error: El archivo '$IMAGE_FILE' no existe.${C_RESET}" >&2
    exit 1
fi

FILE_SIZE_KB=$(awk -v size="$(wc -c < "$IMAGE_FILE")" 'BEGIN { printf "%.1f", size / 1024 }')

echo -e "\n${C_BOLD}${C_CYAN}===============================================================${C_RESET}"
echo -e "${C_BOLD}   BENCHMARK OCR API — INFERENCIA Y TELEMETRÍA (ARM64)${C_RESET}"
echo -e "${C_BOLD}${C_CYAN}===============================================================${C_RESET}"
printf " %-22s : %s (%s KB)\n" "Archivo enviado" "$IMAGE_FILE" "$FILE_SIZE_KB"
printf " %-22s : %s\n" "Motor solicitado" "$ENGINE"
printf " %-22s : %s\n" "Endpoint destino" "$API_URL"
echo -e "${C_CYAN}---------------------------------------------------------------${C_RESET}"
echo -e " Enviando petición... aguardando procesamiento de inferencia..."

TMP_OUT=$(mktemp)
TMP_TIMING=$(mktemp)
trap 'rm -f "$TMP_OUT" "$TMP_TIMING"' EXIT

HTTP_CODE=$(curl -s -S -o "$TMP_OUT" -w "%{http_code}\n%{time_namelookup}\n%{time_connect}\n%{time_starttransfer}\n%{time_total}" \
    -F "file=@${IMAGE_FILE}" \
    -F "familia_id=${FAMILIA_ID}" \
    -F "engine=${ENGINE}" \
    "$API_URL" > "$TMP_TIMING" 2>&1 || echo "000")

# Leer métricas de timing de curl
TIMINGS=()
while IFS= read -r line; do
    TIMINGS+=("$line")
done < "$TMP_TIMING"

HTTP_STATUS="${TIMINGS[0]:-000}"
T_DNS="${TIMINGS[1]:-0.000}"
T_CONNECT="${TIMINGS[2]:-0.000}"
T_TTFB="${TIMINGS[3]:-0.000}"
T_TOTAL="${TIMINGS[4]:-0.000}"

TOTAL_MS=$(awk -v t="$T_TOTAL" 'BEGIN { printf "%.1f", t * 1000 }')
TTFB_MS=$(awk -v t="$T_TTFB" 'BEGIN { printf "%.1f", t * 1000 }')

echo -e "${C_CYAN}---------------------------------------------------------------${C_RESET}"
echo -e "${C_BOLD} 1. MÉTRICAS DE RED / CLIENTE (RTT):${C_RESET}"
if [ "$HTTP_STATUS" -eq 200 ]; then
    printf " %-22s : ${C_GREEN}${C_BOLD}HTTP %s OK${C_RESET}\n" "Código HTTP" "$HTTP_STATUS"
else
    printf " %-22s : ${C_RED}${C_BOLD}HTTP %s ERROR${C_RESET}\n" "Código HTTP" "$HTTP_STATUS"
fi
printf " %-22s : %s ms (%ss)\n" "Tiempo Total RTT" "$TOTAL_MS" "$T_TOTAL"
printf " %-22s : %s ms (Tiempo hasta primer byte)\n" "TTFB" "$TTFB_MS"
printf " %-22s : %ss | Conexión TCP: %ss\n" "Resolución DNS" "$T_DNS" "$T_CONNECT"

# Si la respuesta es JSON, extraer métricas de telemetría interna
if command -v jq >/dev/null 2>&1 && jq -e . "$TMP_OUT" >/dev/null 2>&1; then
    EXEC_TIME=$(jq -r '.execution_time_ms // "N/A"' "$TMP_OUT")
    ENGINE_USED=$(jq -r '.engine_used // "N/A"' "$TMP_OUT")
    ORIG_RES=$(jq -r '.image_original_resolution // "N/A"' "$TMP_OUT")
    PROC_RES=$(jq -r '.image_processed_resolution // "N/A"' "$TMP_OUT")
    MEM_RSS=$(jq -r '.memory_rss_mb // "N/A"' "$TMP_OUT")
    SUCCESS=$(jq -r '.success // false' "$TMP_OUT")
    MONTO=$(jq -r '.monto // "N/A"' "$TMP_OUT")
    MONEDA=$(jq -r '.currency // "UYU"' "$TMP_OUT")
    COMERCIO=$(jq -r '.comercio // "N/A"' "$TMP_OUT")
    FECHA=$(jq -r '.fecha // "N/A"' "$TMP_OUT")
    CONF=$(jq -r '.confianza_ocr // 0' "$TMP_OUT")

    echo -e "${C_CYAN}---------------------------------------------------------------${C_RESET}"
    echo -e "${C_BOLD} 2. TELEMETRÍA DEL MICROSERVICIO (PROCESO PYTHON):${C_RESET}"
    printf " %-22s : ${C_YELLOW}${C_BOLD}%s ms${C_RESET}\n" "Tiempo Inferencia OCR" "$EXEC_TIME"
    printf " %-22s : %s\n" "Motor Utilizado" "$ENGINE_USED"
    printf " %-22s : ${C_BOLD}%s MB${C_RESET}\n" "RAM RSS Proceso" "$MEM_RSS"
    printf " %-22s : %s\n" "Resolución Original" "$ORIG_RES"
    printf " %-22s : %s\n" "Resolución Procesada" "$PROC_RES"

    echo -e "${C_CYAN}---------------------------------------------------------------${C_RESET}"
    echo -e "${C_BOLD} 3. EXTRACCIÓN DE NEGOCIO:${C_RESET}"
    printf " %-22s : %s %s\n" "Monto Total" "$MONEDA" "$MONTO"
    printf " %-22s : %s\n" "Comercio" "$COMERCIO"
    printf " %-22s : %s\n" "Fecha" "$FECHA"
    printf " %-22s : %s%%\n" "Confianza OCR" "$(awk -v c="$CONF" 'BEGIN { printf "%.1f", c * 100 }')"

    echo -e "${C_CYAN}---------------------------------------------------------------${C_RESET}"
    echo -e "${C_BOLD} 4. RESPUESTA JSON COMPLETA:${C_RESET}"
    jq . "$TMP_OUT"
else
    echo -e "${C_CYAN}---------------------------------------------------------------${C_RESET}"
    echo -e "${C_BOLD} RESPUESTA DEL SERVIDOR:${C_RESET}"
    cat "$TMP_OUT"
    echo ""
fi
echo -e "${C_BOLD}${C_CYAN}===============================================================${C_RESET}\n"
