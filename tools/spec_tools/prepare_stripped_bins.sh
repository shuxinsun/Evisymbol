#!/bin/bash
set -e

# === 定位 SPEC 根目录 ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR/../../accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/benchspec/CPU2006"

OPT_LEVELS=("O0" "O1" "O2" "O3" "Os" "Ofast")
BUILD_TYPES=("pie" "nonpie")   # 新增：统一处理 pie 和 nonpie

echo "BASE_DIR = $BASE_DIR"
echo "--------------------------------------"

for bench in "$BASE_DIR"/*; do
    [ -d "$bench" ] || continue
    bench_name=$(basename "$bench")
    echo ">>> Processing $bench_name"

    for build in "${BUILD_TYPES[@]}"; do
        echo "  --- build type: $build ---"

        for opt in "${OPT_LEVELS[@]}"; do

            dir="$bench/exe/$build/$opt"
            src="$dir/nonstripped"
            dst="$dir/stripped"

            if [ -f "$src" ]; then
                echo "    [$opt] Copying nonstripped → stripped"
                cp "$src" "$dst"

                echo "    [$opt] Stripping symbols"
                strip --strip-unneeded "$dst"
            else
                echo "    [$opt] Skip (no nonstripped)"
            fi

        done
    done

    echo ""
done

echo "All done."

