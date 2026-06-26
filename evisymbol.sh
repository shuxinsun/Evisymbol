#!/bin/bash
set -euo pipefail

# ========================
# Logging setup 提前，防止变量未绑定错误
# ========================
SCRIPT_DIR=$(dirname "$(realpath "$0")")

# ========================
# Default optional params
# ========================
PIE_MODE=""
OPT_LEVEL=""
PROG_NAME=""

# ========================
# Parse optional flags first
# ========================
POSITIONAL=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        -pie|-nonpie)
            PIE_MODE="${1#-}"
            shift
            ;;
        -O0|-O1|-O2|-O3|-Os|-Ofast)
            OPT_LEVEL="${1#-}"
            shift
            ;;
        -name)
            PROG_NAME="$2"
            shift 2
            ;;
        *)
            POSITIONAL+=("$1")
            shift
            ;;
    esac
done

set -- "${POSITIONAL[@]}"

# ========================
# Required arguments check
# ========================
if [ $# -ne 1 ]; then
    echo "Usage: $0 <stripped_binary> [-pie|-nonpie] [-O0|-O1|-O2|-O3|-Os|-Ofast] [-name program]" >&2
    exit 1
fi

STRIPPED_BINARY=$(realpath "$1")

# ========================
# File existence check
# ========================
[ -f "$STRIPPED_BINARY" ] || { echo "Error: Stripped binary not found" >&2; exit 1; }

# ========================
# Directory initialization
# ========================
rm -rf "$SCRIPT_DIR/eviTmp"
mkdir -p "$SCRIPT_DIR/eviTmp"

# ========================
# Log folder name
# ========================
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

NAME_PARTS=()
[ -n "$PIE_MODE" ] && NAME_PARTS+=("$PIE_MODE")
[ -n "$OPT_LEVEL" ] && NAME_PARTS+=("$OPT_LEVEL")
[ -n "$PROG_NAME" ] && NAME_PARTS+=("$PROG_NAME")

if [ ${#NAME_PARTS[@]} -eq 0 ]; then
    LOG_FOLDER_NAME="$TIMESTAMP"
else
    LOG_FOLDER_NAME="$(IFS=-; echo "${NAME_PARTS[*]}")-logs"
fi

LOG_BASE_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_BASE_DIR"
LOG_DIR="$LOG_BASE_DIR/$LOG_FOLDER_NAME"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/log.txt"

# ========================
# Helper function
# ========================
log_and_echo() {
    echo -e "$@" | tee -a "$LOG_FILE"
}

log_and_echo "[*] Running evisymbol only at $(date)"
log_and_echo "Command: $0 $*"
log_and_echo "----------------------------------------"

# ========================
# ONLY RUN evisymbol.py
# ========================
log_and_echo "[*] Running evisymbol.py..."
if ! python3 "$SCRIPT_DIR/evisymbol/evisymbol.py" "$STRIPPED_BINARY" "$SCRIPT_DIR/eviTmp/evi.s" 2>&1 | tee -a "$LOG_FILE"; then
    log_and_echo "[!] evisymbol.py failed"
    rm -rf "$LOG_DIR"
    exit 1
fi

# ========================
# Save results to log dir
# ========================
# cp -r "$SCRIPT_DIR/eviTmp" "$LOG_DIR/"

log_and_echo "[✓] Done. All logs & results saved in: $LOG_DIR"

