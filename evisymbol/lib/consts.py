# sections_consts.py
import os
from pathlib import Path
# 数据段候选符号化立即值扫描的节区
DATASECTIONS = [
    ".rodata",
    ".data",
    ".bss",
    ".data.rel.ro",
    ".init_array",
]

# 扫描有效的代码/数据地址区域（含GOT/PLT）
VALID_TARGET_SECTIONS = [
    ".text",
    ".rodata",
    ".init_array",
    ".data",
    ".bss",
    ".got",
    ".got.plt",
    ".data.rel.ro",
    ".plt"
]

PTR_SIZE = 8  # x86-64 架构下的指针大小（字节）
SWITCH_ITEM_SIZE = 4  # x86-64 架构下的 switch case 项大小（字节）

TMP_FOLDER = "./eviTmp"  # 临时文件夹路径

# ==================== 配置区域 ====================
# 模式常量定义（内部使用，保持清晰）
MODE_SYMBOLIZE = "analyze"           # 默认模式：符号化
MODE_WEIGHT_ANALYSIS = "weight_analysis"   # 证据权重分析
MODE_ACCURACY_BENCHMARK = "accuracy_benchmark"  # 准确率基准测试

# 命令行参数到内部模式的映射（你要的映射关系）
MODE_MAPPING = {
    "analyze": MODE_SYMBOLIZE, 
    "stat": MODE_WEIGHT_ANALYSIS,      # 命令行参数"stat"对应权重分析
    "test": MODE_ACCURACY_BENCHMARK,   # 命令行参数"test"对应准确率测试
}

# 所有支持的命令行模式列表（用于参数验证）
SUPPORTED_CLI_MODES = ["analyze", "stat", "test"]

# ssx: GCC编译器生成的内部函数列表，这些函数通常不需要进行符号化处理
GCC_FUNCTIONS = [
    "_start",
    "__libc_start_main",
    "__libc_csu_fini",
    "__libc_csu_init",
    "__lib_csu_fini",
    "_init",
    "__libc_init_first",
    "_fini",
    "_rtld_fini",
    "_exit",
    "__get_pc_think_bx",
    "__do_global_dtors_aux",
    "__gmon_start",
    "frame_dummy",
    "__do_global_ctors_aux",
    "__register_frame_info",
    "deregister_tm_clones",
    "register_tm_clones",
    "__do_global_dtors_aux",
    "__frame_dummy_init_array_entry",
    "__init_array_start",
    "__do_global_dtors_aux_fini_array_entry",
    "__init_array_end",
    "__stack_chk_fail",
    "__cxa_atexit",
    "__cxa_finalize",
    "__cxa_begin_catch",
    "__cxa_end_catch",
    "__cxa_allocate_exception",
    "__gxx_personality_v0",
]

WORK_DIR = Path(__file__).resolve().parent.parent       # eviSymbol当前文件目录
ROOT_DIR = WORK_DIR.parent                              # myProject根目录
# reassessor生成的unknown_region区域的内容
UNKNOWN_REGION_PATH = os.path.join(
    ROOT_DIR,
    "reassessorTmp",
    "unknown_region.txt"
)

if os.path.exists(UNKNOWN_REGION_PATH):
    with open(UNKNOWN_REGION_PATH, "r") as f:
        UNKNOWN_REGION = {int(line.strip()) for line in f if line.strip()}
else:
    UNKNOWN_REGION = set()
