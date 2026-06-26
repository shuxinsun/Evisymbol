#!/bin/bash

set -uo pipefail

# ====================================================
# SPEC CPU2006 Accuracy Runner
# ====================================================

SPEC_ROOT="./accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/benchspec/CPU2006"
SCRIPT="./eviaccuracy.sh"
LOG_ROOT="./logs"

MODES=("pie" "nonpie")
OPTS=("O0" "O1" "O2" "O3" "Os" "Ofast")

mkdir -p "$LOG_ROOT"

# ====================================================
# 检查 eviaccuracy.sh
# ====================================================

if [ ! -f "$SCRIPT" ]; then
    echo "[FATAL] Cannot find $SCRIPT"
    exit 1
fi

echo "========================================"
echo "SPEC CPU2006 Accuracy Runner"
echo "SPEC root: $SPEC_ROOT"
echo "Log root : $LOG_ROOT"
echo "========================================"

# ====================================================
# 遍历 benchmark（473.astar 等）
# ====================================================

for BENCH_DIR in "$SPEC_ROOT"/*; do

    [ -d "$BENCH_DIR" ] || continue

    BENCH_NAME=$(basename "$BENCH_DIR")

    echo
    echo "========================================"
    echo "Benchmark: $BENCH_NAME"
    echo "========================================"

    EXE_ROOT="$BENCH_DIR/exe"
    RUN_ROOT="$BENCH_DIR/run"

    [ -d "$EXE_ROOT" ] || {
        echo "[SKIP] Missing exe dir"
        continue
    }

    # ====================================================
    # 遍历 pie / nonpie
    # ====================================================

    for MODE in "${MODES[@]}"; do

        echo
        echo "MODE: $MODE"

        for OPT in "${OPTS[@]}"; do

            echo "OPT: $OPT"

            STRIPPED="$EXE_ROOT/$MODE/$OPT/stripped"
            UNSTRIPPED="$EXE_ROOT/$MODE/$OPT/nonstripped"
            ASM_DIR="$RUN_ROOT/$MODE/$OPT/nonstripped/intermediate/asm"

            # 检查文件存在
            if [ ! -f "$STRIPPED" ]; then
                echo "[SKIP] Missing stripped"
                continue
            fi

            if [ ! -f "$UNSTRIPPED" ]; then
                echo "[SKIP] Missing nonstripped"
                continue
            fi

            if [ ! -d "$ASM_DIR" ]; then
                echo "[SKIP] Missing asm dir"
                continue
            fi

            PROG_NAME=$(echo "$BENCH_NAME" | cut -d'.' -f2)

            LOG_FOLDER="${MODE}-${OPT}-${PROG_NAME}-logs"
            LOG_DIR="${LOG_ROOT}/${LOG_FOLDER}"
            LOG_FILE="${LOG_DIR}/log.txt"

            # ====================================================
            # 跳过已完成任务
            # ====================================================

            if [ -f "$LOG_FILE" ]; then

                if grep -q "\[✓\] Done" "$LOG_FILE"; then

                    echo "[SKIP] already done: $PROG_NAME ($MODE $OPT)"
                    continue

                else

                    echo "[RETRY] failed task: $PROG_NAME ($MODE $OPT)"

                fi
            fi

            # ====================================================
            # 执行任务
            # ====================================================

            echo "[RUN ] $PROG_NAME ($MODE $OPT)"

            bash "$SCRIPT" \
                "$STRIPPED" \
                "$UNSTRIPPED" \
                "$ASM_DIR" \
                "-$MODE" \
                "-$OPT" \
                -name "$PROG_NAME"

            STATUS=$?

            if [ $STATUS -ne 0 ]; then

                echo "[FAIL] $PROG_NAME ($MODE $OPT)"

            else

                echo "[ OK ] $PROG_NAME ($MODE $OPT)"

            fi

        done
    done
done

echo
echo "========================================"
echo "ALL SPEC TASKS FINISHED"
echo "========================================"

