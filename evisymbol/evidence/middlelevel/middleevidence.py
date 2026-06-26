from capstone import (
    CS_GRP_JUMP,  # 指令分组：跳转类指令（jmp / je / jne 等）
    CS_OP_MEM,
    CS_GRP_CALL,
)
from capstone.x86 import X86_INS_LEA, X86_REG_RIP, X86_REG_RBP, X86_REG_INVALID, X86_REG_EBP, X86_REG_RSP, X86_REG_ESP
from lib.consts import DATASECTIONS
from lib.consts import MODE_WEIGHT_ANALYSIS, MODE_MAPPING, UNKNOWN_REGION

class MiddleLevelEvidence:
    """
    中级证据层：代码段中的其他立即值证据

    职责：
    - 基于指令语义、典型编译器模式，提供弱 / 中等正负证据
    - 不做 CFG / 数据流（高级证据层再做）
    """

    def __init__(self, container, immediates, evidence_counts, data_align_stats):
        """
        初始化方法
        :param container: 容器对象，包含函数等信息
        :param immediates: 即时值集合
        """
        self.container = container  # 保存传入的容器对象
        self.immediates = immediates
        self.target_address_rip_stat = set()
        self.evidence_counts = evidence_counts
        self.data_align_stats = data_align_stats
        # 函数入口集合（来自符号表 / 自动分析）
        self.func_entries = set(container.functions.keys())
    
    # ------------------ R4：call 指令强正证据 ------------------
    # R4: call 指令调用的立即值
    def apply_r4_call_evidence(self, imm, mode=None):
        ev = imm.evidence
        fact = imm.fact
        meta = imm.meta

        # 证据数值统计模式下，gt来的符号没有inst_wrapper属性，使用之前处理过的属性
        is_call = False
        if mode and MODE_MAPPING[mode] == MODE_WEIGHT_ANALYSIS:
            is_call = meta.asm_is_call if meta.asm_is_call  else False
        else:
            inst_wrapper = getattr(meta, "inst_wrapper", None)
            if inst_wrapper is None:
                return
            is_call = CS_GRP_CALL in inst_wrapper.cs.groups
        # 是否属于 call 类控制流指令
        if is_call:
            if self.not_in_UNKNOWN_REGION:     
                self.evidence_counts['r4-call'] += 1
            ev.score += 3.5
            ev.flags.append("call")
            ev.explanations.append(
                f"[R4] + 3.5 : Immediate corresponds to a call instruction "
                f"at {fact.asmline} (address: {fact.inst_address})"
            )

    # --------------------------------------------------
    # R5: 被 jmp 控制流类指令引用
    # --------------------------------------------------
    def apply_r5_jmp_reference(self, imm, mode=None):
        ev = imm.evidence
        fact = imm.fact
        meta = imm.meta

        # 证据数值统计模式下，gt来的符号没有cs_ins属性，使用之前处理过的属性
        is_jmp = False
        if mode and MODE_MAPPING[mode] == MODE_WEIGHT_ANALYSIS:
            is_jmp = meta.asm_is_jmp if meta.asm_is_jmp  else False
        else:
            inst_wrapper = getattr(meta, "inst_wrapper", None)
            if inst_wrapper is None:
                return
            is_jmp = CS_GRP_JUMP in inst_wrapper.cs.groups

        # 是否属于 jump 类控制流指令
        if is_jmp:
            if self.not_in_UNKNOWN_REGION:
                self.evidence_counts['r5-jmp-reference'] += 1
            ev.score += 3.5
            ev.flags.append("jmp")
            ev.explanations.append(
                f"[R5] + 3.5 : Immediate referenced by jump instruction "
                f"at {fact.asmline} (address: {fact.inst_address})"
            )

    # --------------------- -----------------------------
    # R6: 目标地址位于某个函数入口
    # --------------------------------------------------
    def apply_r6_function_entry(self, imm, mode=None):
        ev = imm.evidence
        addr = ev.target_address
        if addr is None:
            return
        
        if addr in self.func_entries:
            if self.not_in_UNKNOWN_REGION:
                self.evidence_counts['r6-function-entry'] += 1
            ev.score += 3.5
            ev.flags.append("func_entry")
            ev.explanations.append(
                f"[R6] + 3.5 : target address matches function entry (0x{addr:x}) "
                f"at {imm.fact.asmline} (address: {imm.fact.inst_address})"
            )

    # --------------------------------------------------
    # R7: 简单识别浮点数（反证据）
    # --------------------------------------------------
    def apply_r7_non_float_constant(self, imm):
        ev = imm.evidence
        fact = imm.fact
        val = fact.value

        # 简单浮点特征（IEEE754）
        if isinstance(val, int):
            # NaN / Inf 常见模式（粗糙版）
            if (val & 0x7f800000) == 0x7f800000:
                if self.not_in_UNKNOWN_REGION:
                    self.evidence_counts['r7-non-float-constant'] += 1
                ev.score -= 0.5
                ev.explanations.append(
                    f"[R7] - 0.5 : Immediate looks like floating-point constant "
                    f"at {imm.fact.asmline} (address: {imm.fact.inst_address})"
                )
                return
    
    # --------------------------------------------------
    # R8: 简单识别字符串（反证据）
    # --------------------------------------------------
    def apply_r8_non_string_constant(self, imm):
        ev = imm.evidence
        fact = imm.fact
        val = fact.value

        # 简单 ASCII 判断（非常保守）
        try:
            # 按小端序还原字节布局
            b = val.to_bytes(fact.size, "little", signed=False)
            # 判断每个字节是不是“可打印 ASCII”
            # 0x20 - 0x7e 范围内的字节都认为是可打印字符, 包括字母、数字、各种标点符号
            if all(0x20 <= c <= 0x7e for c in b):
                if self.not_in_UNKNOWN_REGION:
                    self.evidence_counts['r8-non-string-constant'] += 1
                ev.score -= 1
                ev.explanations.append(
                    f"[R8] - 1 : Immediate looks like ASCII/string constant "
                    f"at {imm.fact.asmline} (address: {imm.fact.inst_address})"
                )
        except Exception:
            pass
    
    # --------------------------------------------------
    # R9: 用于 LEA 的基址 + 偏移
    # --------------------------------------------------
    def apply_r9_lea_base_offset(self, imm, mode=None):
        """
        R9: 用于 LEA 指令的 基址 + 偏移
        子规则用于额外加一点分，lea指令是主规则
        子规则：
          - LEA + RIP : +6, 编译器通过 RIP-relative LEA 构造全局或静态对象地址，地址语义明确、确定性最高
          - LEA + RBP : +3, LEA 基于栈帧基址计算局部对象地址，体现地址构造语义但不对应可符号化的全局地址
          - LEA + 通用寄存器 : +1, LEA 在已有寄存器值基础上加偏移，既可能是指针运算也可能是纯算术，需结合上下文进一步判断
        """
        ev = imm.evidence
        fact = imm.fact
        meta = imm.meta

        is_lea = False
        if mode and MODE_MAPPING[mode] == MODE_WEIGHT_ANALYSIS:
            is_lea = meta.asm_is_lea if meta.asm_is_lea  else False
        else:
            inst_wrapper = getattr(meta, "inst_wrapper", None)
            if inst_wrapper is None:
                return
            cs_ins = inst_wrapper.cs
            is_lea = inst_wrapper.cs.id == X86_INS_LEA


        # 1. 必须是 LEA 指令
        if is_lea == False:
            return
        
        # lea操作数主规则加分,无需进行子规则的加分，因为只需要统计数目即可
        if self.not_in_UNKNOWN_REGION:
            self.evidence_counts['r9-lea-base-offset'] += 1
        ev.score += 0.5
        ev.flags.append("lea")
        ev.explanations.append(
            f"[R9] + 0.5 : LEA constructs "
            f"at {imm.fact.asmline} (address: {imm.fact.inst_address})"
        )

        # 证据数值统计模式下,
        if mode and MODE_MAPPING[mode] == MODE_WEIGHT_ANALYSIS:
            return

        # 2. operand_index 必须指向内存操作数
        try:
            # 取出那个 operand 的完整语义
            op = cs_ins.operands[fact.operand_index]
        except IndexError:
            return

        # 这个 operand 是什么类型
        if op.type != CS_OP_MEM:
            return
        
        mem = op.mem
        # 表示内存地址表达式中的 基址寄存器 和 偏移量
        base = mem.base
        disp = mem.disp

        if disp == 0:
            return

        # --------------------------------------------------
        # 子规则 1：LEA + RIP（可确定目标地址）
        # --------------------------------------------------
        if base == X86_REG_RIP:
            # x86-64: RIP 指向“下一条指令”
            next_ip = cs_ins.address + cs_ins.size
            target_addr = next_ip + disp
            ev.source = "lea_rip_relative"
            ev.score += 1
            ev.target_address = target_addr
            ev.explanations.append(
                f"[R9] + 1 : RIP-relative LEA constructs global/static address "
                f"(base=RIP, disp={disp:+#x})"
                f"at {imm.fact.asmline} (address: {imm.fact.inst_address})"
            )
            return

        # --------------------------------------------------
        # 子规则 2：LEA + RBP（栈对象地址，不可静态确定）
        # --------------------------------------------------
        if base == X86_REG_RBP:
            ev.source = "lea_rbp_relative"
            ev.score += 0.0
            ev.explanations.append(
                f"[R9] + 0.0 : RBP-relative LEA constructs stack object address "
                f"(base=RBP, disp={disp:+#x})"
                f"at {imm.fact.asmline} (address: {imm.fact.inst_address})"
            )
            return

        # --------------------------------------------------
        # 子规则 3：LEA + 通用寄存器（地址 or 算术，待确认）
        # --------------------------------------------------
        if base != X86_REG_INVALID:
            ev.source = "lea_base_offset"
            ev.score += 0.5
            ev.explanations.append(
                f"[R9] + 0.5 : LEA uses base register + offset, possible address construction "
                f"(base={cs_ins.reg_name(base)}, disp={disp:+#x}) "
                f"at {imm.fact.asmline} (address: {imm.fact.inst_address})"
            )
            return
    
    # --------------------------------------------------
    # R10: 匹配 .got 条目
    # --------------------------------------------------
    def apply_r10_got(self, imm):
        '''
        R10: 匹配 .got 条目
        '''
        ev = imm.evidence
        addr = ev.target_address
        if addr is None:
            return
        if not getattr(self.container, "got_base", None) or not getattr(self.container, "got_sz", None):
            return

        if not (self.container.got_base <= addr <
                self.container.got_base + self.container.got_sz):
            return

        # 遍历 GOT 条目
        for entry in self.container.got_entries:
            entry_addr = entry["address"]
            if addr == entry_addr:
                if self.not_in_UNKNOWN_REGION:
                    self.evidence_counts['r10-got-entry'] += 1
                ev.score += 1.5
                ev.flags.append("got_entry")
                ev.explanations.append(
                    f"[R10] + 1.5 : target address {addr} matches .GOT entry "
                    f"at {imm.fact.asmline} (inst: {imm.fact.inst_address})"
                )
    
    # --------------------------------------------------
    # R11: 匹配 .got.plt 条目
    # --------------------------------------------------
    def apply_r11_gotplt(self, imm):
        """
        检查 Immediate 的 target_address 是否落在 GOTPLT 条目中
        并增加中级证据分值
        """
        ev = imm.evidence
        addr = ev.target_address
        if addr is None:
            return
        if not getattr(self.container, "gotplt_base", None) or not getattr(self.container, "gotplt_sz", None):
            return


        if not (self.container.gotplt_base <= addr <
                self.container.gotplt_base + self.container.gotplt_sz):
            return

        # 遍历 GOTPLT 条目
        for entry in self.container.gotplt_entries:
            entry_addr = entry.address
            if addr == entry_addr:
                if self.not_in_UNKNOWN_REGION:
                    self.evidence_counts['r11-gotplt-entry'] += 1
                ev.score += 1.5
                ev.flags.append("gotplt_entry")
                ev.explanations.append(
                    f"[R11] + 1.5 : target address {addr} matches .GOT.PLT entry "
                    f"at {imm.fact.asmline} (inst: {imm.fact.inst_address})"
                )
                return

    # --------------------------------------------------
    # R12: 匹配 PLT 条目
    # --------------------------------------------------
    def apply_r12_plt(self, imm):
        """
        检查 Immediate 的 target_address 是否落在 PLT 条目中
        并增加中级证据分值
        """
        ev = imm.evidence
        addr = ev.target_address
        if addr is None:
            return

        # 遍历 PLT 条目
        for plt_addr_str, sym_name in self.container.plt.items():
            plt_addr = int(plt_addr_str)
            if addr == plt_addr:
                if self.not_in_UNKNOWN_REGION:  
                    self.evidence_counts['r12-plt-entry'] += 1
                ev.score += 3.5
                ev.may_label = sym_name
                ev.flags.append("plt_entry")
                ev.explanations.append(
                    f"[R12] + 3.5 : target address {addr} matches PLT symbol {sym_name} "
                    f"at {imm.fact.asmline} (inst: {imm.fact.inst_address})"
                )
                return

    # --------------------------------------------------
    # R13: PC-relative 加载
    # --------------------------------------------------
    def apply_r13_pc_relative(self, imm, mode=None):
        ev = imm.evidence
        fact = imm.fact
        meta = imm.meta

        # 证据数值统计模式下，gt来的符号没有inst_wrapper属性，使用之前处理过的属性
        is_rip = False
        if mode and MODE_MAPPING[mode] == MODE_WEIGHT_ANALYSIS:
            is_rip = meta.asm_is_pc_relative if meta.asm_is_pc_relative  else False
        else:
            inst_wrapper = getattr(meta, "inst_wrapper", None)
            if inst_wrapper is None:
                return
            # 遍历操作数，查找 base 是 RIP 的内存访问
            for op in inst_wrapper.cs.operands:
                if op.type == CS_OP_MEM and op.mem.base == X86_REG_RIP:
                    is_rip = True
                    break
        if is_rip == True:
            if self.not_in_UNKNOWN_REGION:
                self.evidence_counts['r13-pc-relative'] += 1
            ev.score += 3.5
            ev.flags.append("pc_relative")
            ev.explanations.append(
                f"[R13] + 3.5 : PC-relative memory access detected (excluding LEA) "
                f"at {fact.asmline} (address: {fact.inst_address})"
            )
    
    # --------------------------------------------------
    # R14: RBP-relative 栈访问
    # --------------------------------------------------
    # （rbp未被reassessor算到ground truth中，因为编译器生成的汇编文件中不存在这个rbp的符号）
    def apply_r14_stack_offset(self, imm):
        ev = imm.evidence
        fact = imm.fact
        meta = imm.meta
        inst_wrapper = getattr(meta, "inst_wrapper", None)
        if inst_wrapper is None:
            return

        # 获取指令操作数索引
        try:
            op = inst_wrapper.cs.operands[fact.operand_index]
        except IndexError:
            return

        # 必须是内存操作数
        if op.type != CS_OP_MEM:
            return

        mem = op.mem
        base = mem.base
        disp = mem.disp

        # 基址寄存器是 RBP
        if base == X86_REG_RBP:
            if self.not_in_UNKNOWN_REGION:
                self.evidence_counts['r14-rbp-relative'] += 1
            ev.score -= 10
            ev.flags.append("rbp_relative")
            ev.explanations.append(
                f"[R14] - 10 : RBP-relative stack access (disp: {disp}) "
                f"at {fact.asmline} (address: {fact.inst_address})"
            )

    
    # --------------------------------------------------
    # R15: 跳转表（跳转表项作为从属判断）
    # --------------------------------------------------
    def apply_r15_jumptable(self, imm, mode=None):
        # 由于跳转表是在收集候选立即值的时候处理的，所以对于gt符号来说需要单独验证处理
        if mode and MODE_MAPPING[mode] == MODE_WEIGHT_ANALYSIS and imm.meta.is_jumptable_base == True:
            rodata = self.container.sections.get(".rodata", None)
            if not rodata:
                return
            # 判断地址是否在.rodata段
            if not (rodata.base <= imm.fact.value <= (rodata.base + rodata.sz)):
                return
            # 判断地址是否被.text段中某个rip形式的汇编指令访问
            if self.not_in_UNKNOWN_REGION:
                self.evidence_counts['r15-jumptable-base'] += 1

        if imm.evidence.source in ['jumptable_base']: 
            if self.not_in_UNKNOWN_REGION:
                self.evidence_counts['r15-jumptable-base'] += 1
            imm.evidence.score += 3
            imm.evidence.flags.append("jumptable_base")
            imm.evidence.explanations.append(
                f"[R15] + 5 : target address {imm.fact.value} is a jump table base "
                f"at {imm.fact.imm_address} "
            )
        if imm.evidence.source in ['jumptable_offset']:
            imm.evidence.score += 3
            imm.evidence.flags.append("jumptable_offset")
            imm.evidence.explanations.append(
                f"[R15] + 3 : target address {imm.evidence.target_address} is a jump table entry "
                f"at {imm.fact.imm_address} "
            )
        
    
    # --------------------------------------------------
    # R16: 数据段中指向代码段的立即值（非偏移）位于指令起始地址
    # --------------------------------------------------
    def apply_r16_code_pointer(self, imm):
        ev = imm.evidence
        fact = imm.fact
        addr = ev.target_address
        if addr is None:
            return

        if fact.kind != "imm":
            return

        # 遍历所有函数，检查目标地址是否为指令起始地址
        for fn in self.container.functions.values():
            if fn.is_valid_instruction(addr) == False:
                if self.not_in_UNKNOWN_REGION:
                    self.evidence_counts['r16-code-pointer'] += 1
                ev.score -= 2
                ev.explanations.append(
                    f"[R16] - 2 : Immediate at {fact.asmline} points to instruction "
                    f"at {addr:#x} in function {fn.name}"
                )
                return
    
    

    # --------------------------------------------------
    # R17: 目标为数据地址 + 对齐
    # --------------------------------------------------
    def apply_r17_alignment_check(self, imm, mode=None):
        ev = imm.evidence
        addr = ev.target_address
        if not addr:
            return

        target_section = ev.target_section if ev.target_section else self.container.get_section_by_address(ev.target_address)
        
        # 只对指向数据段的立即值进行检查
        if target_section in DATASECTIONS:
            if mode and MODE_MAPPING[mode] == MODE_WEIGHT_ANALYSIS:
                # 更新总计数
                self.data_align_stats['total'] += 1
                # 检查对齐情况 - 使用互斥分类
                if addr % 8 == 0:
                    self.data_align_stats['aligned_8'] += 1
                elif addr % 4 == 0:
                    self.data_align_stats['aligned_4'] += 1
                elif addr % 2 == 0:
                    self.data_align_stats['aligned_2'] += 1
                else:
                    self.data_align_stats['misaligned'] += 1
            if addr % 8 == 0:
                if self.not_in_UNKNOWN_REGION:
                    self.evidence_counts['r17-aligned'] += 1
                ev.score += 1  # 8字节对齐加1分
                ev.explanations.append(
                    f"[R17] + 1 : target address in data segment is 8-byte aligned"
                )
            elif addr % 4 == 0:
                if self.not_in_UNKNOWN_REGION:
                    self.evidence_counts['r17-aligned'] += 1
                ev.score += 0.5  # 4字节对齐加0.5分
                ev.explanations.append(
                    f"[R17] + 0.5 : target address in data segment is 4-byte aligned"
                )
            else:
                ev.score -= 0.5  # 2字节对齐或不对齐扣0.5分
                ev.explanations.append(
                    f"[R17] - 0.5 : target address in data segment is NOT 4-byte aligned"
                )

    
    # 统计下所有目标地址且需要恰好满足rip访问的情况
    def get_target_address_rip_stat(self):
        # 统计下所有目标地址且需要恰好满足rip访问的情况
        for imm in self.immediates:
            if imm.evidence.target_address and imm.meta.asm_is_pc_relative == True:
                self.target_address_rip_stat.add(imm.evidence.target_address)


    def apply_r18_special_sections(self, imm, mode=None):
        if mode and MODE_MAPPING[mode] == MODE_WEIGHT_ANALYSIS:
            sec = self.container.get_section_by_address(imm.fact.inst_address)
        else:
            sec = imm.evidence.source
        if sec in ['.init_array']:
            if imm.evidence.may_label == 'frame_dummy':
                # frame_dummy是GCC默认输出的一个函数，属于libc的一部分，通常不需要被符号化。
                imm.evidence.score -= 100
                imm.evidence.explanations.append(
                    f"[R18] - 100 : Immediate at {imm.fact.asmline} points to frame_dummy in .init_array"
                )
                return
            if self.not_in_UNKNOWN_REGION:
                self.evidence_counts['r18-special-sections'] += 1
            imm.evidence.score += 3.5
            imm.evidence.explanations.append(
                f"[R18] + 3.5 : Immediate address {imm.fact.imm_address} comes from special section {sec} "
                f"at {imm.fact.imm_address} "
            )
    
    
    # R19:被当作数组基址的立即数
    def apply_r19_indexed_table_base(self, imm):
        ev = imm.evidence
        inst_wrapper = getattr(imm.meta, "inst_wrapper", None)
        if not inst_wrapper:
            return

        cs = inst_wrapper.cs

        imm_val = imm.fact.value
        # 过滤“布局偏移常量” 常见字段/元素内部偏移（极强误报源）
        SMALL_LAYOUT_OFFSETS = {0, 1, 2, 4, 8, 16, 24, 32, 40, 48, 56, 64}

        # 额外规则：小于 0x80 且 8 字节对齐，也极可能是 layout
        def is_layout_constant(v):
            if v in SMALL_LAYOUT_OFFSETS:
                return True
            if 0 <= v <= 0x2a4 and v % 4 == 0:
                return True
            return False

        if is_layout_constant(imm_val):
            return

        for op in cs.operands:
            if op.type != CS_OP_MEM:
                continue

            mem = op.mem
            disp = mem.disp

            # 只匹配 disp(, index, scale)的情况
            if (
                mem.base == X86_REG_INVALID      # 没有 base
                and mem.index != X86_REG_INVALID # 有 index
                and mem.scale in (2, 4, 8)       # 典型表项大小
            ):
                if disp == imm.fact.value:
                    if self.not_in_UNKNOWN_REGION:
                        self.evidence_counts['r19-indexed-table-base'] += 1

                    ev.score += 3.5   # 比普通 mem_disp 强
                    ev.target_address = disp
                    ev.source = "r19-table-base"

                    ev.explanations.append(
                        f"[R19] + 3.5 : immediate is TABLE BASE in indexed addressing "
                        f"at 0x{cs.address:x}"
                    )
                    return


    # 处理call基于寄存器间接寻址偏移较小得数值
    def apply_r25_indirect_call_field_offset(self, imm):
        inst_wrapper = getattr(imm.meta, "inst_wrapper", None)
        if not inst_wrapper:
            return
        cs = inst_wrapper.cs
        if CS_GRP_CALL not in cs.groups:
            return

        for op in cs.operands:
            if op.type != CS_OP_MEM:
                continue
            
            mem = op.mem

            # 立即数是 displacement
            if mem.disp != imm.fact.value:
                continue

            # 必须是 base 寄存器存在（对象访问）
            if mem.base == X86_REG_INVALID:
                continue
            
            # 不是 RIP-relative（那是符号）
            if mem.base == X86_REG_RIP:
                continue

            # 小偏移 = 结构字段
            if abs(mem.disp) <= 0x200:
                if self.not_in_UNKNOWN_REGION:
                    self.evidence_counts['r25-indirect-call-offset'] += 1
                ev = imm.evidence
                ev = imm.evidence
                ev.score -= 6
                ev.explanations.append(
                    "[r25] - 6: immediate is OBJECT FIELD OFFSET used to fetch function pointer"
                )
                return

    
    # --------------------------------------------------
    # 运行所有中级证据规则
    # --------------------------------------------------
    def run(self, imm, not_in_UNKNOWN_REGION ,mode):

        self.not_in_UNKNOWN_REGION = not_in_UNKNOWN_REGION
        if mode and MODE_MAPPING[mode] == MODE_WEIGHT_ANALYSIS:
            self.get_target_address_rip_stat()
            
        # 代码段的立即值
        if imm.fact.section == ".text":
            self.apply_r4_call_evidence(imm, mode)
            self.apply_r5_jmp_reference(imm, mode)
            self.apply_r6_function_entry(imm, mode)
            self.apply_r7_non_float_constant(imm)
            self.apply_r8_non_string_constant(imm)
            self.apply_r9_lea_base_offset(imm, mode) 
            self.apply_r10_got(imm)
            self.apply_r11_gotplt(imm)
            self.apply_r12_plt(imm)
            self.apply_r13_pc_relative(imm, mode)
            self.apply_r14_stack_offset(imm)
            self.apply_r19_indexed_table_base(imm)
            self.apply_r25_indirect_call_field_offset(imm)
        # 数据段中的立即值
        if imm.fact.section in DATASECTIONS:
            self.apply_r15_jumptable(imm, mode)
            self.apply_r16_code_pointer(imm)
        self.apply_r17_alignment_check(imm, mode)
        self.apply_r18_special_sections(imm, mode)
        return self.immediates