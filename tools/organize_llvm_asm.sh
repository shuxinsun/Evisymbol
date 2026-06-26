#!/bin/bash
# 假设当前路径在 MultiSource/Applications
APPS_DIR="$(pwd)"

# ==============================
# 一、普通 Applications（一级目录）
# ==============================
for app in "$APPS_DIR"/*; do
    if [ -d "$app" ]; then
        echo "Processing application: $(basename "$app")"

        INTERMEDIATE_DIR="$app/intermediate"
        BINARY_DIR="$INTERMEDIATE_DIR/binary"
        ASM_DIR="$INTERMEDIATE_DIR/asm"
        mkdir -p "$BINARY_DIR" "$ASM_DIR"

        # 复制二进制文件
        for bin in "$app"/*; do
            if [ -f "$bin" ] && [ -x "$bin" ]; then
                cp "$bin" "$BINARY_DIR/"
            fi
        done

        # 移动汇编文件
        for asm in "$app"/*.s "$app"/*.asm; do
            if [ -f "$asm" ]; then
                mv "$asm" "$ASM_DIR/"
            fi
        done
    fi
done

# ==============================
# 二、特殊处理 ALAC/decode 和 ALAC/encode
# ==============================
ALAC_DIR="$APPS_DIR/ALAC"

for sub in decode encode; do
    TARGET="$ALAC_DIR/$sub"
    if [ -d "$TARGET" ]; then
        echo "Processing ALAC/$sub"

        INTERMEDIATE_DIR="$TARGET/intermediate"
        BINARY_DIR="$INTERMEDIATE_DIR/binary"
        ASM_DIR="$INTERMEDIATE_DIR/asm"
        mkdir -p "$BINARY_DIR" "$ASM_DIR"

        # 复制二进制文件
        for bin in "$TARGET"/*; do
            if [ -f "$bin" ] && [ -x "$bin" ]; then
                cp "$bin" "$BINARY_DIR/"
            fi
        done

        # 只移动 .s 结尾的汇编文件
        for asm in "$TARGET"/*.s; do
            if [ -f "$asm" ]; then
                mv "$asm" "$ASM_DIR/"
            fi
        done
    fi
done
echo "All applications processed."
