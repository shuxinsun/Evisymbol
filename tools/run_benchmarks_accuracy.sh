#!/bin/bash
set -uo pipefail
# 不使用 set -e，避免单个失败导致全部停止

# =========================
# 配置区域
# =========================

BASES=(
    "accuracy_database/benchmark/dataset/coreutils-8.30/x64/gcc"
    "accuracy_database/benchmark/dataset/binutils-2.31.1/x64/gcc"
)

SCRIPT="./eviaccuracy.sh"
LOG_ROOT="./logs"

# =========================
# 检查脚本存在
# =========================

if [ ! -f "$SCRIPT" ]; then
    echo "[FATAL] Cannot find $SCRIPT"
    exit 1
fi

mkdir -p "$LOG_ROOT"

echo "========================================"
echo "EviSymbol Accuracy Batch Runner"
echo "Log root: $LOG_ROOT"
echo "========================================"

# =========================
# 遍历 BASE
# =========================

for BASE in "${BASES[@]}"; do

    echo
    echo "========================================"
    echo "BASE: $BASE"
    echo "========================================"

    [ -d "$BASE" ] || {
        echo "[WARNING] BASE not found: $BASE"
        continue
    }

    # =========================
    # 遍历 pie / nonpie
    # =========================

    for MODE_DIR in "$BASE"/*; do

        [ -d "$MODE_DIR" ] || continue

        MODE=$(basename "$MODE_DIR")

        if [[ "$MODE" != "pie" && "$MODE" != "nonpie" ]]; then
            continue
        fi

        echo
        echo "MODE: $MODE"

        # =========================
        # 遍历 O0-bfd O2-coreutils 等
        # =========================

        for CONF_DIR in "$MODE_DIR"/*; do

            [ -d "$CONF_DIR" ] || continue

            CONF_NAME=$(basename "$CONF_DIR")

            OPT_LEVEL="${CONF_NAME%%-*}"
            PROG_CLASS="${CONF_NAME#*-}"

            STRIPBIN_DIR="$CONF_DIR/stripbin"
            BIN_DIR="$CONF_DIR/bin"
            ASM_DIR="$CONF_DIR/asm"

            if [ ! -d "$STRIPBIN_DIR" ]; then
                echo "[SKIP] Missing stripbin: $CONF_NAME"
                continue
            fi

            echo
            echo "Config: $CONF_NAME"

            # =========================
            # 遍历每个程序
            # =========================

            for STRIPPED in "$STRIPBIN_DIR"/*; do

                [ -f "$STRIPPED" ] || continue

                FILE_NAME=$(basename "$STRIPPED")

                UNSTRIPPED="$BIN_DIR/$FILE_NAME"

                if [ ! -f "$UNSTRIPPED" ]; then
                    echo "[ERROR] Missing unstripped: $FILE_NAME"
                    continue
                fi

                FULL_NAME="${PROG_CLASS}_${FILE_NAME}"

                # =========================
                # 日志路径（核心逻辑）
                # =========================

                LOG_FOLDER="${MODE}-${OPT_LEVEL}-${FULL_NAME}-logs"
                LOG_DIR="${LOG_ROOT}/${LOG_FOLDER}"
                LOG_FILE="${LOG_DIR}/log.txt"

                # =========================
                # 跳过已成功完成任务
                # =========================

                if [ -f "$LOG_FILE" ]; then

                    if grep -q "\[✓\] Done" "$LOG_FILE"; then

                        echo "[SKIP] $FULL_NAME ($MODE $OPT_LEVEL)"

                        continue

                    else

                        echo "[RETRY] $FULL_NAME ($MODE $OPT_LEVEL)"

                    fi
                fi

                # =========================
                # 执行任务
                # =========================

                echo "[RUN ] $FULL_NAME ($MODE $OPT_LEVEL)"

                bash "$SCRIPT" \
                    "$STRIPPED" \
                    "$UNSTRIPPED" \
                    "$ASM_DIR" \
                    "-$MODE" \
                    "-$OPT_LEVEL" \
                    -name "$FULL_NAME"

                STATUS=$?

                if [ $STATUS -ne 0 ]; then

                    echo "[FAIL] $FULL_NAME"

                else

                    echo "[ OK ] $FULL_NAME"

                fi

            done
        done
    done
done

echo
echo "========================================"
echo "ALL TASKS FINISHED"
echo "========================================"

