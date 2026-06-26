#!/bin/bash
set -euo pipefail

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

# Restore positional parameters
set -- "${POSITIONAL[@]}"

# ========================
# Required arguments check
# ========================
if [ $# -ne 2 ]; then
    echo "Usage: $0 <binary_file_path> <asm_dir_path> [-pie|-nonpie] [-O0|-O1|-O2|-O3|-Os|-Ofast] [-name program]" >&2
    exit 1
fi

BINARY_PATH=$(realpath "$1")
ASM_DIR=$(realpath "$2")

# ========================
# File existence check
# ========================
[ -f "$BINARY_PATH" ] || { echo "Error: Binary file not found: $BINARY_PATH" >&2; exit 1; }
[ -d "$ASM_DIR" ] || { echo "Error: Assembly directory not found: $ASM_DIR" >&2; exit 1; }

# ========================
# Directory initialization
# ========================
rm -rf ./reassessorTmp ./gt_results ./reassessor/output ./eviTmp
mkdir -p ./reassessorTmp/bin ./gt_results

# ========================
# Logging setup
# ========================

SCRIPT_DIR=$(dirname "$(realpath "$0")")

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

log_and_echo "[*] Running threshold.sh at $(date)"
log_and_echo "Command: $0 $*"
log_and_echo "----------------------------------------"

# ========================
# Run symbolGT.sh
# ========================
chmod +x "$SCRIPT_DIR/symbolGT.sh"

log_and_echo "[*] Running symbolGT.sh and retrieving the immediate values in the ground truth that satisfy evidences..."

if ! "$SCRIPT_DIR/symbolGT.sh" "$BINARY_PATH" "$ASM_DIR" 2>&1 | tee -a "$LOG_FILE"; then
    log_and_echo "[!] symbolGT.sh failed"

    rm -rf "$LOG_DIR"
    exit 1
fi

# ========================
# Run evisymbol.py
# ========================
log_and_echo "[*] Running evisymbol.py and retrieving all immediate values that satisfy evidences..."

if ! python3 "$SCRIPT_DIR/evisymbol/evisymbol.py" "$BINARY_PATH" "$SCRIPT_DIR/eviTmp/evi.s" --mode stat 2>&1 | tee -a "$LOG_FILE"; then
    log_and_echo "[!] evisymbol.py failed"

    rm -rf "$LOG_DIR"
    exit 1
fi

# ========================
# Copy result folders
# ========================
if [ -d "$SCRIPT_DIR/gt_results" ]; then
    cp -r "$SCRIPT_DIR/gt_results" "$LOG_DIR/"
fi

if [ -d "$SCRIPT_DIR/eviTmp" ]; then
    cp -r "$SCRIPT_DIR/eviTmp" "$LOG_DIR/"
fi

if [ -d "$SCRIPT_DIR/reassessorTmp" ]; then
    cp -r "$SCRIPT_DIR/reassessorTmp" "$LOG_DIR/"
fi

log_and_echo "[✓] Done. All logs and files saved in $LOG_DIR"
