organize_spec_binaries.sh:批量遍历当前目录下所有 benchmark 文件夹（如 473.astar），把 exe 里的二进制和 run 里最新 build 目录，按 PIE类型 + 优化级别 + strip状态 归档。


prepare_stripped_bins.sh:用于批量复制并剥离 SPEC CPU2006 中各基准nonPIE 和 PIE 可执行文件的符号信息，生成可用于二进制分析实验的 stripped 版本。



buildtools:解决spec的Ubuntu 18.04兼容性问题修改后的编译文件
