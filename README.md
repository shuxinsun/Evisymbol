
## 核心功能
EviSymbol 是一款针对二进制重写场景设计的立即数符号化工具，核心解决“二进制重写中，哪些立即数必须符号化、可以不符号化、绝不能符号化”的关键问题，避免因立即数符号化不当导致的重写错误，提升二进制重写的准确性与兼容性。
- 立即数符号化决策：基于多层级证据分析（基础证据、中级证据、高级证据），判定候选立即数的符号化必要性，输出可解释、可追溯的符号化结果。
- 多基准测试支持：兼容 SPEC CPU2006、coreutils、binutils、llvm-test-suite 等主流基准测试集，支持不同编译级别（O0/O1/O2/O3/Os/Ofast）和运行模式（PIE/non-PIE、stripped/nonstripped）的测试。
- 兼容性验证：支持对符号化后的汇编文件进行编译运行，验证符号化结果的正确性。
- 
## 环境准备
Ubuntu 18.04 x64

### 依赖工具
- 操作系统：Ubuntu 18.04 LTS (x64)
- Python 版本：3.6（推荐，兼容后续 reassessor 依赖）
- capstone：反汇编、指令解析
- angr：用于函数边界识别（CFGFast），辅助证据分析。

## evisymbol.py

 - 该 Python 脚本用于分析二进制文件，并提取满足特定证据条件的立即数。

### Usage

`python3 ./evisymbol/evisymbol.py <binary_file_path> <asm_path>`

 - 输入：二进制文件 <binary_file_path> 和要生成的目标汇编文件自定义路径。
 - 输出：符号化信息文件，标记每条指令的立即数及其对应的证据类型。
 - 运行示例：`python3 ./evisymbol/evisymbol.py ./demos/cpp_demo/bin/simple_inheritance ./evi.s`


## evisymbol.sh

 - 自动化调度运行 evisymbol.py，自动创建日志目录、保存运行日志与结果文件

### Usage

`bash evisymbol.sh <stripped_binary_path> [-pie|-nonpie] [-O0|-O1|-O2|-O3|-Os|-Ofast] [-name program]`

 - 输入：已剥离二进制文件路径，可选传入编译模式、优化等级、程序名称等参数。
 - 输出：自动生成带时间戳与参数标识的日志文件夹，保存完整运行日志及分析结果。
 - 运行示例：`bash ./evisymbol.sh ./demos/switch_demo-PIC/bin/hello-stripped -pie -O2 -name switch_demo`


## symbolGT.sh

 - 生成ground truth 数据文件

### Usage

`bash symbolGT.sh <unstripped_binary_path> <asm_dir_path>`

 - 输入：未剥离二进制文件  和编译生成的汇编文件所在目录。
 - 输出：ground truth 数据文件，记录程序中每条指令对应的符号化信息。
 - 运行示例：`bash ./symbolGT.sh ./demos/switch_demo-PIC/bin/hello-nonstripped ./demos/switch_demo-PIC/asm/`


## threshhold.sh

 - 该脚本用于基于未剥离二进制文件和对应汇编目录，自动执行 symbolGT.sh 与 evisymbol.py，收集符号化相关的立即数统计结果，并按 PIE/优化级别等参数生成结构化日志目录保存所有中间结果与日志。

### Usage

`bash ./threshold.sh <unstripped_binary_path> <asm_dir_path> [-pie|-nonpie] [-O0|-O1|-O2|-O3|-Os|-Ofast] [-name program]`

 - 输入：须传入未剥离的二进制文件路径和汇编文件目录，后面的 `-pie/-nonpie`、优化等级、`-name 程序名` 均为选填参数，主要用于自动生成日志名称。
 - 输出：最终统计结果，展示各类证据的权重比例，可用于进一步分析。
 - 运行示例：`bash ./threshold.sh ./demos/switch_demo-PIC/bin/hello-nonstripped ./demos/switch_demo-PIC/asm/ -pie -name hello`

## eviaccuracy.sh

 - 该脚本用于统计每种类型识别的准确度

### Usage

`bash eviaccuracy.sh <stripped_binary_path> <unstripped_binary_path> <asm_dir_path> [-pie|-nonpie] [-O0|-O1|-O2|-O3|-Os|-Ofast] [-name program]`

 - 输入：须传入剥离二进制文件、未剥离二进制文件、编译生成的汇编文件所在目录，后面的 `-pie/-nonpie`、优化等级、`-name 程序名` 均为选填参数，主要用于自动生成日志名称。
 - 输出：对应的符号化准确率结果。
 - 运行示例：`bash ./eviaccuracy.sh ./demos/cpp_demo/bin/simple_inheritance ./demos/cpp_demo/bin/simple_inheritance ./demos/cpp_demo/asm -nonpie -O0 -name inheritance`
