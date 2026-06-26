#!/bin/bash

TYPE=$1        # pie / nonpie
OPT=$2         # O0 O1 O2 O3 Os Ofast
STRIPTYPE=$3   # stripped / nonstripped

if [ $# -ne 3 ]; then
    echo "Usage: $0 <pie|nonpie> <O0|O1|O2|O3|Os|Ofast> <stripped|nonstripped>"
    exit 1
fi

# === 关键：定位 SPEC 根目录 ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR/../../accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/benchspec/CPU2006"

for bench in "$BASE_DIR"/*; do
    [ -d "$bench" ] || continue
    benchname=$(basename "$bench")
    echo "Processing $benchname"

    # ===== exe =====
    EXE_DIR="$bench/exe"
    if [ -d "$EXE_DIR" ]; then
        cd "$EXE_DIR" || continue
        mkdir -p "$TYPE/$OPT"

        bin=$(find . -maxdepth 1 -type f -executable | head -n 1)
        if [ -n "$bin" ]; then
            mv "$bin" "$TYPE/$OPT/$STRIPTYPE"
        fi
    fi

    # ===== run =====
    RUN_DIR="$bench/run"
    if [ -d "$RUN_DIR" ]; then
        cd "$RUN_DIR" || continue
        mkdir -p "$TYPE/$OPT"

        latest=$(ls -td *build* 2>/dev/null | head -n 1)
        if [ -n "$latest" ]; then
            mv "$latest" "$TYPE/$OPT/$STRIPTYPE"

            if [ "$STRIPTYPE" = "nonstripped" ]; then
                cd "$TYPE/$OPT/$STRIPTYPE"
                mkdir -p intermediate/asm
                find . -name "*.s" -exec mv {} intermediate/asm/ \;
            fi
        fi
    fi

    echo
done

echo "All SPEC benchmarks organized."

