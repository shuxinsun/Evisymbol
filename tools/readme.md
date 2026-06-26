`run_benchmarks_accuracy.sh`是用于论文实验批量跑coreutils和binutils的准确性的，需要做完准备工作后，放到myProject目录下运行才可以

`run_spec_accuracy.sh`是用于论文实验批量跑spec的准确性的，需要做完准备工作后，放到myProject目录下运行才可以

`organize_llvm_asm.sh`脚本用于复现证据权重统计实验编译完各个优化级别的llvm数据集之后放在 build-O0/MultiSource/Applications 目录下，自动把每个应用生成的可执行文件复制到 intermediate/binary/ 目录，并把生成的汇编文件（.s/.asm）移动到 intermediate/asm/ 目录，同时对 ALAC/decode 和 ALAC/encode 进行单独处理。


`summarize_threshold_stats.py`自动遍历所有优化级别日志(../weight-logs)，提取地址偏离、数据对齐和证据统计信息，并计算跨优化级别总计及符号化比例。



`summarize_symbolization_logs.py`脚本用于自动汇总../spec-logs目录下不同实验配置的log.txt文件，批量解析实验日志中的E1至E8类证据统计结果，自动汇总不同模式与优化级别下的TP、FN、FP数量及比例，并生成accuracy_summary.xlsx统计表。
