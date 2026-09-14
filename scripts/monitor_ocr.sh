#!/usr/bin/env bash
# ==============================================================================
# Auditor Familiar — Script de Telemetría y Monitoreo en Tiempo Real (OCR API)
# Diseñado para Orange Pi 5 Plus ARM64 y entornos Docker Linux.
# ==============================================================================
set -u

CONTAINER_NAME="auditor_familiar_ocr_api"
INTERVAL=0.5
LOG_FILE=""

# Colores ANSI (si es terminal interactiva)
if [ -t 1 ]; then
    COLOR_RESET="\033[0m"
    COLOR_BOLD="\033[1m"
    COLOR_CYAN="\033[36m"
    COLOR_GREEN="\033[32m"
    COLOR_YELLOW="\033[33m"
    COLOR_RED="\033[31m"
    COLOR_BLUE="\033[34m"
    COLOR_MAGENTA="\033[35m"
else
    COLOR_RESET=""
    COLOR_BOLD=""
    COLOR_CYAN=""
    COLOR_GREEN=""
    COLOR_YELLOW=""
    COLOR_RED=""
    COLOR_BLUE=""
    COLOR_MAGENTA=""
fi

show_help() {
    cat << EOF
Uso: $0 [OPCIONES]

Monitorea en tiempo real (cada 0.5s) el uso de CPU, memoria RAM (actual y pico),
e I/O del contenedor Docker de OCR en la Orange Pi 5 Plus.

Opciones:
  -c, --container NOMBRE   Nombre del contenedor (default: auditor_familiar_ocr_api)
  -i, --interval SEGUNDOS  Frecuencia de refresco en segundos (default: 0.5)
  -l, --log ARCHIVO        Registra métricas en archivo CSV (ej: -l ocr_bench.csv)
  -h, --help               Muestra esta ayuda y sale

Ejemplos:
  $0
  $0 --container auditor_familiar_ocr_api --log /tmp/ocr_test.csv
  $0 -i 1.0
EOF
}

# Parseo de argumentos
while [[ $# -gt 0 ]]; do
    case "$1" in
        -c|--container)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        -i|--interval)
            INTERVAL="$2"
            shift 2
            ;;
        -l|--log)
            LOG_FILE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${COLOR_RED}Opción desconocida: $1${COLOR_RESET}" >&2
            show_help
            exit 1
            ;;
    esac
done

# Verificar docker
if ! command -v docker >/dev/null 2>&1; then
    echo -e "${COLOR_RED}Error: El comando 'docker' no está instalado o no está en el PATH.${COLOR_RESET}" >&2
    exit 1
fi

# Verificar si el contenedor existe
if ! docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
    echo -e "${COLOR_RED}Error: No se encontró el contenedor '$CONTAINER_NAME'.${COLOR_RESET}" >&2
    echo "Verificá con 'docker ps' los contenedores activos." >&2
    exit 1
fi

# Función para convertir unidades de memoria a MB numérico con punto decimal
to_mb() {
    local val_unit="$1"
    # Normalizar espacios y mayúsculas
    val_unit=$(echo "$val_unit" | tr -d ' ' | tr '[:lower:]' '[:upper:]')
    
    if [[ "$val_unit" =~ ^([0-9.]+)(GIB|GB)$ ]]; then
        awk -v val="${BASH_REMATCH[1]}" 'BEGIN { printf "%.2f", val * 1024 }'
    elif [[ "$val_unit" =~ ^([0-9.]+)(MIB|MB)$ ]]; then
        awk -v val="${BASH_REMATCH[1]}" 'BEGIN { printf "%.2f", val }'
    elif [[ "$val_unit" =~ ^([0-9.]+)(KIB|KB)$ ]]; then
        awk -v val="${BASH_REMATCH[1]}" 'BEGIN { printf "%.2f", val / 1024 }'
    elif [[ "$val_unit" =~ ^([0-9.]+)(B)$ ]]; then
        awk -v val="${BASH_REMATCH[1]}" 'BEGIN { printf "%.2f", val / 1048576 }'
    else
        echo "0.00"
    fi
}

# Inicializar encabezado CSV si corresponde
if [ -n "$LOG_FILE" ]; then
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
    echo "timestamp,cpu_percent,mem_used_mb,mem_limit_mb,mem_percent,net_io,block_io" > "$LOG_FILE"
    echo -e "${COLOR_GREEN}Métricas registrándose en: $LOG_FILE${COLOR_RESET}"
fi

# Variables de estadísticas acumuladas
START_TIME=$(date +%s)
SAMPLE_COUNT=0
CPU_SUM="0.0"
PEAK_CPU="0.0"
PEAK_MEM_MB="0.0"
LAST_MEM_LIMIT_MB="0.0"

# Función de resumen al salir con Ctrl+C
summary_on_exit() {
    local end_time=$(date +%s)
    local elapsed=$((end_time - START_TIME))
    local minutes=$((elapsed / 60))
    local seconds=$((elapsed % 60))

    local avg_cpu="0.00"
    if [ "$SAMPLE_COUNT" -gt 0 ]; then
        avg_cpu=$(awk -v sum="$CPU_SUM" -v count="$SAMPLE_COUNT" 'BEGIN { printf "%.2f", sum / count }')
    fi

    echo -e "\n"
    echo -e "${COLOR_BOLD}${COLOR_CYAN}===============================================================${COLOR_RESET}"
    echo -e "${COLOR_BOLD}         RESUMEN CONSOLIDADO DE TELEMETRÍA (OCR API)${COLOR_RESET}"
    echo -e "${COLOR_BOLD}${COLOR_CYAN}===============================================================${COLOR_RESET}"
    printf " %-24s : %s\n" "Contenedor" "$CONTAINER_NAME"
    printf " %-24s : %02dm:%02ds\n" "Duración del monitoreo" "$minutes" "$seconds"
    printf " %-24s : %d muestras (frecuencia %.1fs)\n" "Muestras registradas" "$SAMPLE_COUNT" "$INTERVAL"
    echo -e "${COLOR_CYAN}---------------------------------------------------------------${COLOR_RESET}"
    printf " %-24s : %s%%\n" "CPU Promedio" "$avg_cpu"
    printf " %-24s : ${COLOR_YELLOW}%s%%${COLOR_RESET}\n" "CPU Pico Máximo" "$PEAK_CPU"
    printf " %-24s : ${COLOR_RED}${COLOR_BOLD}%s MB${COLOR_RESET} (High Water Mark)\n" "RAM Pico Máximo" "$PEAK_MEM_MB"
    if [ "$(awk -v lim="$LAST_MEM_LIMIT_MB" 'BEGIN { print (lim > 0) }')" -eq 1 ]; then
        printf " %-24s : %s MB\n" "RAM Límite Asignado" "$LAST_MEM_LIMIT_MB"
    fi
    if [ -n "$LOG_FILE" ]; then
        printf " %-24s : %s (%d registros)\n" "Archivo CSV" "$LOG_FILE" "$SAMPLE_COUNT"
    fi
    echo -e "${COLOR_BOLD}${COLOR_CYAN}===============================================================${COLOR_RESET}\n"
    exit 0
}

trap summary_on_exit SIGINT SIGTERM

# Bucle principal de monitoreo en tiempo real
while true; do
    # Capturar estadísticas en una sola llamada no bloqueante
    STATS_LINE=$(docker stats "$CONTAINER_NAME" --no-stream --format "{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}" 2>/dev/null || true)

    if [ -z "$STATS_LINE" ]; then
        # Contenedor probablemente detenido o reiniciando
        STATUS=$(docker inspect -f '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "not_found")
        printf "\r${COLOR_RED}[ALERTA] Contenedor %s en estado: %s... aguardando${COLOR_RESET}   " "$CONTAINER_NAME" "$STATUS"
        sleep "$INTERVAL"
        continue
    fi

    IFS=$'\t' read -r RAW_CPU RAW_MEM RAW_MEM_PERC RAW_NET RAW_BLOCK <<< "$STATS_LINE"

    # Limpiar CPU (%)
    CPU_NUM=$(echo "$RAW_CPU" | tr -d '%' | tr -d ' ')
    [[ -z "$CPU_NUM" ]] && CPU_NUM="0.0"

    # Parsear Memoria: "150.2MiB / 2GiB"
    MEM_USED_RAW=$(echo "$RAW_MEM" | awk -F'/' '{print $1}')
    MEM_LIMIT_RAW=$(echo "$RAW_MEM" | awk -F'/' '{print $2}')
    MEM_USED_MB=$(to_mb "$MEM_USED_RAW")
    MEM_LIMIT_MB=$(to_mb "$MEM_LIMIT_RAW")
    LAST_MEM_LIMIT_MB="$MEM_LIMIT_MB"

    # Actualizar acumuladores
    SAMPLE_COUNT=$((SAMPLE_COUNT + 1))
    CPU_SUM=$(awk -v sum="$CPU_SUM" -v val="$CPU_NUM" 'BEGIN { printf "%.2f", sum + val }')

    # Actualizar picos
    PEAK_CPU=$(awk -v peak="$PEAK_CPU" -v val="$CPU_NUM" 'BEGIN { printf "%.2f", (val > peak ? val : peak) }')
    PEAK_MEM_MB=$(awk -v peak="$PEAK_MEM_MB" -v val="$MEM_USED_MB" 'BEGIN { printf "%.2f", (val > peak ? val : peak) }')

    # Timestamp ISO
    NOW_ISO=$(date +"%Y-%m-%dT%H:%M:%S")

    # Registro en archivo de log/CSV si está configurado
    if [ -n "$LOG_FILE" ]; then
        echo "$NOW_ISO,$CPU_NUM,$MEM_USED_MB,$MEM_LIMIT_MB,$RAW_MEM_PERC,$RAW_NET,$RAW_BLOCK" >> "$LOG_FILE"
    fi

    # Tiempo transcurrido
    CURR_TIME=$(date +%s)
    RUNNING_SECS=$((CURR_TIME - START_TIME))

    # Construcción visual de barra de memoria (20 chars)
    MEM_PERC_NUM=$(echo "$RAW_MEM_PERC" | tr -d '%' | tr -d ' ')
    [[ -z "$MEM_PERC_NUM" ]] && MEM_PERC_NUM="0.0"
    BAR_SLOTS=$(awk -v p="$MEM_PERC_NUM" 'BEGIN { s = int(p / 5); if (s > 20) s = 20; if (s < 0) s = 0; print s }')
    EMPTY_SLOTS=$((20 - BAR_SLOTS))
    BAR_STR=""
    for ((i=0; i<BAR_SLOTS; i++)); do BAR_STR="${BAR_STR}█"; done
    for ((i=0; i<EMPTY_SLOTS; i++)); do BAR_STR="${BAR_STR}░"; done

    # Color de alerta según uso de memoria
    MEM_COLOR="$COLOR_GREEN"
    if [ "$(awk -v p="$MEM_PERC_NUM" 'BEGIN { print (p >= 80.0) }')" -eq 1 ]; then
        MEM_COLOR="$COLOR_RED"
    elif [ "$(awk -v p="$MEM_PERC_NUM" 'BEGIN { print (p >= 50.0) }')" -eq 1 ]; then
        MEM_COLOR="$COLOR_YELLOW"
    fi

    # Actualizar pantalla (ANSI cursor a inicio)
    printf "\033[H\033[J"
    echo -e "${COLOR_BOLD}${COLOR_CYAN}===============================================================${COLOR_RESET}"
    echo -e "${COLOR_BOLD}   AUDITOR FAMILIAR — OCR API TELEMETRY MONITOR (ARM64)${COLOR_RESET}"
    echo -e "${COLOR_BOLD}${COLOR_CYAN}===============================================================${COLOR_RESET}"
    printf " ${COLOR_BOLD}%-15s${COLOR_RESET} : %s\n" "Contenedor" "$CONTAINER_NAME"
    printf " %-15s : %s  |  Muestras: %d  |  Tiempo: %02dm:%02ds\n" "Frecuencia" "${INTERVAL}s" "$SAMPLE_COUNT" "$((RUNNING_SECS / 60))" "$((RUNNING_SECS % 60))"
    echo -e "${COLOR_CYAN}---------------------------------------------------------------${COLOR_RESET}"
    printf " ${COLOR_BOLD}%-15s${COLOR_RESET} : %8s%%  ${COLOR_YELLOW}(Pico: %s%%)${COLOR_RESET}\n" "Uso de CPU" "$CPU_NUM" "$PEAK_CPU"
    printf " ${COLOR_BOLD}%-15s${COLOR_RESET} : ${MEM_COLOR}[%s]${COLOR_RESET} %s MB / %s MB (%s)\n" "Memoria RAM" "$BAR_STR" "$MEM_USED_MB" "$MEM_LIMIT_MB" "$RAW_MEM_PERC"
    printf " ${COLOR_BOLD}%-15s${COLOR_RESET} : ${COLOR_RED}${COLOR_BOLD}%s MB${COLOR_RESET} (High Water Mark)\n" "Pico RAM" "$PEAK_MEM_MB"
    printf " %-15s : Red: %s  |  I/O Disco: %s\n" "Transferencia" "$RAW_NET" "$RAW_BLOCK"
    echo -e "${COLOR_CYAN}---------------------------------------------------------------${COLOR_RESET}"
    if [ -n "$LOG_FILE" ]; then
        printf " %-15s : %s\n" "Log CSV" "$LOG_FILE"
    fi
    echo -e "${COLOR_MAGENTA} [Presioná Ctrl+C para detener y ver el reporte consolidado]${COLOR_RESET}"
    echo -e "${COLOR_BOLD}${COLOR_CYAN}===============================================================${COLOR_RESET}"

    sleep "$INTERVAL"
done
