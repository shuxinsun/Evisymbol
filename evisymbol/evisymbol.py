#!/usr/bin/env python3

import argparse
import json
import os
from elftools.elf.elffile import ELFFile
from lib.consts import DATASECTIONS, MODE_WEIGHT_ANALYSIS, MODE_MAPPING, MODE_ACCURACY_BENCHMARK, ROOT_DIR, UNKNOWN_REGION

from lib.test.match import match_label

# asan插桩使用
def load_analysis_cache(loader, outfile):
    with open(outfile + ".analysis_cache") as fd:
        analysis = json.load(fd)
    print("[*] Loading analysis cache")
    for func, info in analysis.items():
        for key, finfo in info.items():
            loader.container.functions[int(func)].analysis[key] = dict()
            for k, v in finfo.items():
                try:
                    addr = int(k)
                except ValueError:
                    addr = k
                loader.container.functions[int(func)].analysis[key][addr] = v

# asan插桩使用
def save_analysis_cache(loader, outfile):
    analysis = dict()

    for addr, func in loader.container.functions.items():
        analysis[addr] = dict()
        analysis[addr]["free_registers"] = dict()
        for k, info in func.analysis["free_registers"].items():
            analysis[addr]["free_registers"][k] = list(info)

    with open(outfile + ".analysis_cache", "w") as fd:
        json.dump(analysis, fd)


# asan插桩使用
def analyze_registers(loader, args):
    StackFrameAnalysis.analyze(loader.container)
    # if args.cache:
    #     try:
    #         load_analysis_cache(loader, args.outfile)
    #     except IOError:
    #         RegisterAnalysis.analyze(loader.container)
    #         save_analysis_cache(loader, args.outfile)
    # else:
    # eviSymbol无需存储分析结果
    RegisterAnalysis.analyze(loader.container)

# 这四个函数均用于插桩asan
def asan(rw, loader, args):
    analyze_registers(loader, args)

    instrumenter = Instrument(rw)
    instrumenter.do_instrument()
    instrumenter.dump_stats()

# stat mode:以表格的形式打印证据权重统计结果(某一类证据，在“候选立即值中”被最终证明“真的值得符号化”的能力（判别力 / 有效性）)
def save_evidence_counts(evidence_counts, gt_evidence_counts, keys, outfile, gt_address_range_stats, gt_data_align_stats):
    lines = []

    # 表头
    header = f"{'Evidence':30} {'Immediate':12} {'Symbolized':12}{'ratios(%)':12}"
    sep = "-" * len(header)

    lines.append(header)
    lines.append(sep)

    for k in keys:
        imm_cnt = evidence_counts.get(k, 0)
        sym_cnt = gt_evidence_counts.get(k, 0)
        lines.append(f"{k:30} {imm_cnt:<12} {sym_cnt:<12}{(sym_cnt / imm_cnt * 100) if imm_cnt != 0 else 0:<12}")
    
    # --- GT Address Range 统计 ---
    if gt_address_range_stats:
        lines.append("\nGT Address Range Stats:")
        for bucket, count in gt_address_range_stats.items():
            lines.append(f"{bucket:30} {count}")
    
     # --- GT Data Alignment 统计 ---
    if gt_data_align_stats:
        lines.append("\nGT Data Alignment Stats:")
        for align_type, count in gt_data_align_stats.items():
            lines.append(f"{align_type:30} {count}")
    
    # 打印到终端
    print("\nEvidence statistics (comparison):")
    for line in lines:
        print(line)
    
    # 写入文件
    with open(outfile, "w", encoding="utf-8") as fd:
        for line in lines:
            fd.write(line + "\n")

# test模式，仅统计ground truth中满足证据的立即值比例使用
def run_accuracy_benchmark(immediates, gt_immediates, uncertain_symbol_set, dump_dir=None):
    """
    新评测逻辑：
    GT存在 → 本应符号化 (Type1–7)
    GT不存在 → 本应是常量

    分类：
        TP  : GT有 + 预测有 + final_label匹配
        FN  : GT有 + 预测无
        FP  : GT有 + 预测有 + final_label不匹配
        E8  : GT无 + 预测有   （误符号化常量）
    """

    # ========= 1. 构建 GT 映射 =========
    gt_map = {
        gt["instAddress"]: gt
        for gt in gt_immediates
        if gt["instAddress"] is not None
    }

    # ========= 2. 构建 Pred 映射（只保留 S+） =========
    pred_map = {}
    for imm in immediates:
        dec = imm.decision
        inst_addr = getattr(imm.fact, "inst_address", None)
        if inst_addr is None:
            inst_addr = getattr(imm.fact, "imm_address", None)
        if inst_addr is None:
            continue

        if dec.must_symbolize == "S+":
            pred_map[inst_addr] = imm

    # ========= 3. 初始化统计 =========
    by_type = {
        t: {
            "gt_total": 0,
            "predicted_total": 0,
            "TP": 0,
            "FP": 0,
            "FN": 0,
        }
        for t in range(1, 9)   # 1–7 正常类型，8 = E8
    }

    overall = {
        "gt_total": 0,
        "predicted_total": 0,
        "TP": 0,
        "FP": 0,
        "FN": 0,
        "FN-S?": 0,
        "E8": 0,
        "E8-symtab": 0,
        "E8-unknown_region": 0
    }

    false_positive = [] # GT有 + 预测有 + final_label不匹配
    false_negative = [] # GT有 + 预测无
    false_E8 = []       # GT无 + 预测有   （误符号化常量）
    false_E8_case = {'.symtab': 0}  # GT无 + 预测有   （误符号化常量）的详细情况(有一部分时reassessor本身没有识别出来的问题数量统计)
    false_E8_case['unknown_region'] = 0 # 一部分反汇编了reassessor的未知区域代码导致的E8问题

    # ========= 4. 遍历“所有出现过的位置” =========
    all_addrs = set(gt_map.keys()).union(pred_map.keys())# 所有“GT认为应该符号化”的指令地址 + 所有“系统预测为符号化”的指令地址

    for inst_addr in all_addrs:
        gt = gt_map.get(inst_addr)
        pred_imm = pred_map.get(inst_addr)

        gt_exists = gt is not None
        pred_exists = pred_imm is not None

        # --------------------------
        # 情况 A：GT存在 → 本应符号化
        # --------------------------
        # 这种方式final_label一定需要存在，否则也有可能没识别出final_label但是归类到FP的情况
        if gt_exists:
            gt_type = gt["type"]
            overall["gt_total"] += 1
            by_type[gt_type]["gt_total"] += 1

            if pred_exists:
                by_type[gt_type]["predicted_total"] += 1
                overall["predicted_total"] += 1

                # 结构匹配检查
                pred_label = pred_imm.decision.final_label
                gt_label = gt["final_label"]
                is_match = match_label(pred_label, gt_label)

                if is_match:
                    by_type[gt_type]["TP"] += 1
                    overall["TP"] += 1
                else:
                    # FP（结构错误）
                    by_type[gt_type]["FP"] += 1
                    overall["FP"] += 1
                    false_positive.append({
                        "instAddress": inst_addr,
                        "gt_label": gt_label,
                        "pred_label": pred_label,
                        "type": gt_type
                    })
            else:
                # FN
                by_type[gt_type]["FN"] += 1
                overall["FN"] += 1
                false_negative.append({
                    "instAddress": inst_addr,
                    "ground_truth": gt
                })
                if inst_addr in uncertain_symbol_set:
                    overall["FN-S?"] += 1

        # --------------------------
        # 情况 B：GT不存在 → 本应是常量
        # --------------------------
        else:
            if pred_exists:
                # Type8 错误
                by_type[8]["FP"] += 1
                by_type[8]["predicted_total"] += 1
                overall["E8"] += 1
                overall["predicted_total"] += 1

                false_E8.append({
                    "instAddress": inst_addr,
                    "type": "E8",
                    "pred_label": pred_imm.decision.final_label
                })

                # 统计reassessor统计的缺少 符号表中存在但在汇编层只表现为单个原子数据项 的情况数量
                if '.symtab' in pred_imm.evidence.flags:
                    false_E8_case['.symtab'] += 1
                    overall['E8-symtab'] += 1
                elif any(
                    addr in UNKNOWN_REGION 
                    for addr in (pred_imm.fact.inst_address, imm.fact.imm_address) 
                    if addr
                ):
                    false_E8_case['unknown_region'] += 1
                    overall['E8-unknown_region'] += 1

    
    # ========= 5. 计算 per-type Precision / Recall / F1 =========
    for t in range(1, 9):
        tp = by_type[t]["TP"]
        fp = by_type[t]["FP"]
        fn = by_type[t]["FN"]

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )

        by_type[t]["precision"] = precision
        by_type[t]["recall"] = recall
        by_type[t]["f1"] = f1

    # ========= 6. 计算 overall =========
    tp = overall["TP"]
    fp = overall["FP"]
    fn = overall["FN"]

    overall["precision"] = tp / (tp + fp) if (tp + fp) else 0.0
    overall["recall"] = tp / (tp + fn) if (tp + fn) else 0.0
    overall["f1"] = (
        2 * overall["precision"] * overall["recall"]
        / (overall["precision"] + overall["recall"])
        if (overall["precision"] + overall["recall"])
        else 0.0
    )

    return {
        "overall": overall,
        "by_type": by_type,
    }, false_positive, false_negative, false_E8



# 导出错误分类样例，方便人工分析
def dump_misclassified_cases(
    false_positive,
    false_negative,
    false_E8,
    out_dir,
    prefix="symbolization_error"
):

    os.makedirs(out_dir, exist_ok=True)
  
    # ---------- 写 JSON ----------
    def dump(path, objs):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                objs,
                f,
                indent=4,
                ensure_ascii=False,
                default=lambda o: o.__dict__
            )

    dump(os.path.join(out_dir, f"{prefix}_FP.json"), false_positive)
    dump(os.path.join(out_dir, f"{prefix}_FN.json"), false_negative)
    dump(os.path.join(out_dir, f"{prefix}_E8.json"), false_E8)
    # dump(os.path.join(out_dir, f"{prefix}_ambiguous.json"), ambiguous)

    print("\n[*] Misclassified cases dumped:")
    print(f"   FP : {len(false_positive)}")
    print(f"   FN : {len(false_negative)}")
    print(f"   E8 : {len(false_E8)}")
    # print(f"    S? : {len(ambiguous)}")

# 统一打印准确率基准测试结果
def print_accuracy_benchmark(stats):
    """
    统一打印：
    1. Overall 指标
    2. 按 type(1~8) 的 TP / FP / FN / Precision / Recall / F1
    """

    print("\n=== Symbolization Accuracy Benchmark (Overall) ===")
    o = stats["overall"]
    print(f"GT total symbols        : {o['gt_total']}")         # 真实存在的符号化目标总数
    print(f"Predicted (S+) total    : {o['predicted_total']}")  # 算法预测为必须符号化的立即值总数
    print(f"True Positive (TP)      : {o['TP']}")               # 真正正确预测为 S+ 的数量
    print(f"False Positive (FP)     : {o['FP']}")               # 符号化结构错误的数量
    print(f"False Negative (FN)     : {o['FN']}")               # 漏报的数量 (真实存在但未被预测为 S+)
    print(f"FN-S?                   : {o['FN-S?']}")            # 漏报的数量中，有多少是 S?
    print(f"E8                      : {o['E8']}")               # 错误预测为 S+ 的数量
    print(f"E8-symtab               : {o['E8-symtab']}")        # 错误预测为 S+ 的数量中，有多少是符号表中存在但在汇编层只表现为单个原子数据项的
    print(f"E8-unknown_region       : {o['E8-unknown_region']}")           # 错误预测为 S+ 的数量中，有多少是PC相对的, 落入reassessor的未知区域的
    print(f"Precision               : {o['precision']:.4f}")    # 预测为 S+ 的立即值中，有多少是真正应该符号化的
    print(f"Recall                  : {o['recall']:.4f}")       # GT 中的立即值，有多少被预测为 S+
    print(f"F1-score                : {o['f1']:.4f}")           # 综合考虑精确率和召回率的指标

    print("\n=== Per-Type Statistics ===")
    header = (
        f"{'Type':<5}"
        f"{'GT':>8}"
        f"{'Pred':>8}"
        f"{'TP':>8}"
        f"{'FP':>8}"
        f"{'FN':>8}"
        f"{'Prec':>10}"
        f"{'Recall':>10}"
        f"{'F1':>10}"
    )
    print(header)
    print("-" * len(header))

    for t in sorted(stats["by_type"].keys()):
        s = stats["by_type"][t]
        print(
            f"{t:<5}"
            f"{s['gt_total']:>8}"
            f"{s['predicted_total']:>8}"
            f"{s['TP']:>8}"
            f"{s['FP']:>8}"
            f"{s['FN']:>8}"
            f"{s['precision']:>10.4f}"
            f"{s['recall']:>10.4f}"
            f"{s['f1']:>10.4f}"
        )


if __name__ == "__main__":
    argp = argparse.ArgumentParser(description='')

    argp.add_argument("bin", type=str, help="Input binary to load")
    argp.add_argument("outfile", type=str, help="Symbolized ASM output")
    # 统计模式不对外开放，仅仅统计ground truth中满足证据的立即值比例使用
    argp.add_argument(
    "--mode",
    type=str,
    choices=["analyze", "stat", "test"],
    default="analyze",
    help=(
            "Running mode:\n"
            "  analyze : default, perform symbol resolution and statistics\n"
            "  stat    : only perform statistics based on provided symbolization results\n"
            "  test    : run tests and benchmarks\n"
        )
    )

    args = argp.parse_args()


    print(f"[*] Analyzing {args.bin} into {args.outfile}...")

    elffile = ELFFile(open(args.bin, "rb"))
    arch = elffile.get_machine_arch()

    symtools_path = "symtools"

    # 控制是否需要asan插桩
    is_asan = False

    if arch == "x64":
        from lib.loader import Loader
        from lib.immcollector import ImmediateCollector
        from evidence.fusionevidence import FusionEvidence
        from lib.container import Container
        from rw.rw import AssemblyRewriter
        if is_asan:
            from rw.rw import Rewriter
            from retrowrite.analysis.register import RegisterAnalysis
            from retrowrite.analysis.stackframe import StackFrameAnalysis
            from retrowrite.rwtools_x64.asan.instrument import Instrument
    else:
        print(f"Architecture {arch} not supported!")
        exit(1)

    loader = Loader(args.bin)   # 加载二进制文件

    # 判断是不是非PIE文件
    # if loader.is_nonpie() == False:
    #     print("It looks like %s is position independent" % args.bin)
    #     sys.exit(1)
    
    slist = loader.slist_from_elffile() # 获取各个段的基本信息

    if loader.has_symbol_table():
        loader.identify_imports()   # 收集动态符号表中已定义的全局数据对象
        flist = loader.flist_from_symtab()  # 根据符号表获取函数
    else:
        flist = loader.flist_from_cfgfast()
    
    loader.load_functions(flist) # 加载函数到container
    loader.load_data_sections(slist, lambda x: x in DATASECTIONS) # 加载数据段到container

    reloc_list = loader.reloc_list_from_symtab() # 从符号表中获取重定位信息
    loader.load_relocations(reloc_list) # 加载重定位信息到container

    global_list = loader.global_data_list_from_symtab()
    loader.load_globals_from_glist(global_list) # 添加全局数据对象到container
    
    loader.container.attach_loader(loader)  # 让container和loader两个实例互相关联

    # 收集符号化的候选立即值
    immcollector = ImmediateCollector(loader.container)
    
    # ssx:打印container
    TMP_DIR = ROOT_DIR / "eviTmp"
    os.makedirs(TMP_DIR, exist_ok=True)
    container_bin = os.path.join(TMP_DIR, "container.json")
    with open(container_bin, 'w', encoding='utf-8') as f:
        json.dump(loader.container, f, indent=4, ensure_ascii=False, default=Container.safe_detailed_container_serializer)
    
    
    immediates = immcollector.collect()
    fusionevi = FusionEvidence(loader.container, immediates)
    evidence_counts, _, _, uncertain_symbol_set = fusionevi.run()
    # 将证据评价过程也保存到文本中
    immcollector.save_immediates_to_txt(TMP_DIR)
    
    # 暂时还未跑通
    if is_asan:
        rw = Rewriter(loader.container, args.outfile)
        asan(rw, loader, args)
    
    # 生成汇编文件（可生成汇编文件用于后续插桩，解除下面两行注释即可）
    # assemrw = AssemblyRewriter(loader.container)
    # assemrw.dump(args.outfile)
    
    # 统计各证据相关权重时使用
    if args.mode and MODE_MAPPING[args.mode] == MODE_WEIGHT_ANALYSIS:
        keys = sorted(evidence_counts.keys())  # 保证 r1-r16 顺序一致
        evidence_counts_bin = os.path.join(TMP_DIR, "evidence_counts.txt")

        gt_path = os.path.join(
            ROOT_DIR,
            "gt_results",
            "gt_symbol_with_instAddr_ImmediateWrapper.json"
        )
        if not os.path.exists(gt_path):
            raise FileNotFoundError(
                f"GT result file not found: {gt_path}"
            )
        with open(gt_path, "r", encoding="utf-8") as f:
            gt_immediates_list = json.load(f)
        

        from lib.immcollector import ImmediateWrapper
        gt_immediates = []
        for gt_immediate in gt_immediates_list:
            gt_immediates.append(ImmediateWrapper(gt_immediate))

        gt_fusionevi = FusionEvidence(loader.container, gt_immediates)
        gt_evidence_counts, gt_address_range_stats, gt_data_align_stats, _ = gt_fusionevi.run(args.mode)

        save_evidence_counts(evidence_counts, gt_evidence_counts, keys, evidence_counts_bin, gt_address_range_stats, gt_data_align_stats)
    
    # 准确率基准测试模式
    if args.mode and MODE_MAPPING[args.mode] == MODE_ACCURACY_BENCHMARK:
        print("[*] Running accuracy benchmark...")
        # 读取 GT
        gt_path = os.path.join(
            ROOT_DIR,
            "gt_results",
            "gt_symbol_with_instAddr.json"
        )
        if not os.path.exists(gt_path):
            raise FileNotFoundError(f"GT result file not found: {gt_path}")

        with open(gt_path, "r", encoding="utf-8") as f:
            gt_immediates = json.load(f)

        # 跑评测
        stats, false_positive, false_negative, false_E8 = run_accuracy_benchmark(immediates, gt_immediates, uncertain_symbol_set)
        print_accuracy_benchmark(stats)
    
        # 导出错误分类样例，方便人工分析
        error_dir = os.path.join(TMP_DIR, "misclassified_cases")
        # 输出错误用例
        dump_misclassified_cases(false_positive, false_negative, false_E8, error_dir)