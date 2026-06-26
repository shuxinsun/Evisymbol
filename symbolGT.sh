#!/bin/bash
set -euo pipefail

# ========================
# Project root
# ========================
PROJECT_ROOT=$(pwd)
export PROJECT_ROOT
export PYTHONPATH="$PROJECT_ROOT"

# ========================
# Argument check
# ========================
if [ $# -ne 2 ]; then
    echo "Usage: $0 <binary_file_path> <asm_dir_path>" >&2
    exit 1
fi

BINARY_PATH=$(realpath "$1")
ASM_DIR=$(realpath "$2")

# ========================
# File existence check
# ========================
if [ ! -f "$BINARY_PATH" ]; then
    echo "Error: Binary file not found: $BINARY_PATH" >&2
    exit 1
fi

if [ ! -d "$ASM_DIR" ]; then
    echo "Error: Assembly directory not found: $ASM_DIR" >&2
    exit 1
fi

# ========================
# Directory initialization
# ========================
echo "[*] Initializing directories"
rm -rf ./reassessorTmp ./gt_results ./reassessor/output
mkdir -p ./reassessorTmp/bin ./gt_results

# ========================
# Copy binary only
# ========================
BINARY_NAME=$(basename "$BINARY_PATH")
cp "$BINARY_PATH" "./reassessorTmp/bin/$BINARY_NAME"

# ========================
# Run reassessor
# ========================
echo "[*] Running reassessor"
cd reassessor
python3 -m reassessor.reassessor \
    "../reassessorTmp/bin/$BINARY_NAME" \
    "$ASM_DIR" \
    "./output"
cd ..

# ========================
# Generate ground truth
# ========================
echo "[*] Generating ground truth..."
python3 ./tools/gt_load.py

# ========================
# Cleanup
# ========================
# rm -rf ./reassessorTmp

echo "[✓] Done"

