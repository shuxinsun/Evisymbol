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
            PIE_MODE="${1#-}"   # remove leading dash
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
if [ $# -ne 3 ]; then
    echo "Usage: $0 <stripped_binary> <unstripped_binary> <asm_dir> [-pie|-nonpie] [-O0|-O1|-O2|-O3|-Os|-Ofast] [-name program]" >&2
    exit 1
fi

STRIPPED_BINARY=$(realpath "$1")
UNSTRIPPED_BINARY=$(realpath "$2")
ASM_DIR=$(realpath "$3")

# ========================
# File existence check
# ========================
[ -f "$STRIPPED_BINARY" ] || { echo "Error: Stripped binary not found" >&2; exit 1; }
[ -f "$UNSTRIPPED_BINARY" ] || { echo "Error: Unstripped binary not found" >&2; exit 1; }
[ -d "$ASM_DIR" ] || { echo "Error: Assembly directory not found" >&2; exit 1; }

# ========================
# Directory initialization
# ========================
rm -rf ./reassessorTmp ./gt_results ./reassessor/output ./eviTmp
mkdir -p ./reassessorTmp/bin ./gt_results

# ========================
# Logging setup
# ========================

# 获取脚本所在目录（myProject目录）
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

# 强制 logs 在 myProject/logs 下
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

log_and_echo "[*] Running symbolGT.sh..."
if ! "$SCRIPT_DIR/symbolGT.sh" "$UNSTRIPPED_BINARY" "$ASM_DIR" 2>&1 | tee -a "$LOG_FILE"; then
    log_and_echo "[!] symbolGT.sh failed"

    # 删除失败的log目录
    #cd "$SCRIPT_DIR"
    #rm -rf "$LOG_DIR"

    exit 1
fi

# ========================
# Run evisymbol.py
# ========================
log_and_echo "[*] Running evisymbol.py..."
if ! python3 "$SCRIPT_DIR/evisymbol/evisymbol.py" "$STRIPPED_BINARY" "$SCRIPT_DIR/eviTmp/evi.s" --mode test 2>&1 | tee -a "$LOG_FILE"; then
    log_and_echo "[!] evisymbol.py failed"

    # 删除失败的log目录
    cd "$SCRIPT_DIR"
    rm -rf "$LOG_DIR"

    exit 1
fi

# ========================
# Copy result folders
# ========================
#for dir in gt_results eviTmp reassessorTmp; do
#    if [ -d "$SCRIPT_DIR/$dir" ]; then
#        cp -r "$SCRIPT_DIR/$dir" "$LOG_DIR/"
#    fi
#done

log_and_echo "[✓] Done. All logs saved in $LOG_DIR"
