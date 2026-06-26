# from elftools.elf.sections import SymbolTableSection
# from elftools.elf.relocation import RelocationSection
from collections import defaultdict
import struct
import json
from capstone import (
    CS_OP_IMM,    # 操作数类型：立即值（如 mov rax, 0x401000）
    CS_OP_MEM,    # 操作数类型：内存操作数（如 [rip + 0x1234]）
    CS_GRP_JUMP,  # 指令分组：跳转类指令（jmp / je / jne 等）
    CS_GRP_CALL   # 指令分组：函数调用指令（call）
)
from capstone.x86_const import X86_REG_RIP  # x86-64 的 RIP 寄存器（用于 RIP-relative 寻址）
from elftools.elf.enums import ENUM_RELOC_TYPE_x64
from lib.consts import SWITCH_ITEM_SIZE, PTR_SIZE, DATASECTIONS, GCC_FUNCTIONS

class ImmediateCollector():
    def __init__(self, container):
        self.container = container # ssx: 一个容器对象，包含节区和函数等信
        self.immediates = []  # ssx:记录所有候选立即值对象
        self.pot_sw_bases = defaultdict(set) # ssx:记录潜在的switch跳转表基地址

        # ssx:对每个数据段中的每个字节生成一个DataCell(DataSection.load)
        for sec, section in self.container.sections.items():
            section.load()

        # 反汇编函数，收集代码段中候选立即值
        # ssx: 反汇编除了GCC内部函数外识别出的所有函数,指令存储到self.cache中
        for _, function in self.container.functions.items():
            if function.name in GCC_FUNCTIONS:
                continue
            function.disasm(container)

    def dedup_by_fact(self, immediates):
        """
        按 fact 去重 ImmediateWrapper 列表，保留顺序
        不做 deepcopy，只保留原始对象
        """
        seen = set()
        unique_list = []

        for imm in immediates:
            # 假设 fact 是 dataclass 且可 hash
            fact_key = tuple(sorted(imm.fact.__dict__.items()))

            if fact_key not in seen:
                seen.add(fact_key)
                unique_list.append(imm)  # 直接用原对象

        return unique_list


    def collect(self):
        print("[*] Collecting potential symbolic immediates...")
        # immpool = ImmediatePool()
        # 收集代码段中的候选立即值
        self.collect_text_immediates(self.container)
        # 收集数据段中的候选立即值
        self.collect_data_immediates(self.container)
        # 收集重定位表中的候选立即值
        self.collect_reloc_immediates(self.container)
        # ssx:对列表中的立即值字典按 fact 字段去重，保留顺序
        self.immediates = self.dedup_by_fact(self.immediates)
        return self.immediates

    
    def _fill_common_fact(self, fact, function_address, instr, operand_index):
        fact.section = ".text"
        fact.function_address = function_address
        fact.asmline = f"{instr.mnemonic} {instr.op_str}"
        fact.instr_mnemonic = instr.mnemonic
        fact.operand_index = operand_index

    # ssx: 处理代码段中的候选符号化立即值(可以和前面识别的时候直接筛选合并，后续做优化)
    def collect_text_immediates(self, container):
        for fn_address, function in container.functions.items():
            # ssx:跳过GCC内部函数
            if function.name in GCC_FUNCTIONS:
                continue
            instructations = function.cache
            if not instructations:
                continue
            
            for instr in instructations:
                cs_ins = instr.cs
                is_call = CS_GRP_CALL in cs_ins.groups
                is_jmp = CS_GRP_JUMP in cs_ins.groups
                
                for idx, op in enumerate(cs_ins.operands):
                    # ---------- Case 1: 立即值 ----------
                    if op.type == CS_OP_IMM:
                        fact = ImmediateFact(
                            value=op.imm,
                            imm_size=op.size,
                            inst_address=instr.address,
                            inst_size=instr.sz,
                            imm_address=None,
                            imm_offset=None,
                            kind="Imm"
                        )
                        self._fill_common_fact(fact, fn_address, instr, idx)
                        imm = ImmediateWrapper(fact)
                        imm.meta.inst_wrapper = instr   # ssx:保存capstone指令对象
                        # 立即值的目标地址是他本身
                        imm.evidence.target_address = op.imm
                        imm.evidence.target_section = container.get_section_by_address(imm.evidence.target_address)
                        # R2：call 立即值
                        if is_call:
                            imm.evidence.source = "call"
                            imm.evidence.address_from = "CALL"
                        # jmp  立即值
                        elif is_jmp:
                            imm.evidence.source = "jmp"
                            imm.evidence.address_from = "JMP"
                            
                        self.immediates.append(imm)

                    # ---------- Case 2: 内存位移 ----------
                    elif op.type == CS_OP_MEM and op.mem.disp != 0:
                        fact = ImmediateFact(
                            value=op.mem.disp,
                            imm_size=op.size,
                            inst_address=instr.address,
                            inst_size=instr.sz,
                            imm_address=None,
                            imm_offset=None,
                            kind="Disp"
                        )
                        self._fill_common_fact(fact, fn_address, instr, idx)
                        imm = ImmediateWrapper(fact)
                        imm.meta.inst_wrapper = instr   # ssx:保存capstone指令对象
                        # RIP-relative（只是事实，不直接 S+）
                        if op.mem.base == X86_REG_RIP:
                            imm.evidence.source = "pc_relative"
                            imm.evidence.address_from = "PC_REL"
                            imm.evidence.target_address = (
                                instr.address + instr.sz + op.mem.disp
                            )
                            imm.evidence.target_section = container.get_section_by_address(imm.evidence.target_address)
                            # 寻找跳转表基址
                            rodata = container.sections.get(".rodata", None)
                            if rodata:
                                if rodata.base <= imm.evidence.target_address <= (rodata.base + rodata.sz):
                                    container.bases.add(imm.evidence.target_address)
                                    self.pot_sw_bases[function.start].add(imm.evidence.target_address)
                        # R2：call 内存地址
                        if is_call:
                            imm.evidence.source = "call"
                            imm.evidence.address_from = "CALL"
                        # jmp  立即值
                        elif is_jmp:
                            imm.evidence.source = "jmp"
                            imm.evidence.address_from = "JMP"
                        self.immediates.append(imm)
    
    def save_switch_base_imm(self, swbase, sec_name):
        fact = ImmediateFact(
            value=swbase,
            imm_size=PTR_SIZE,
            inst_address=None,      # 数据段没有指令
            inst_size=None,
            imm_address=swbase,
            imm_offset=None,
            kind="Imm"
        )
        imm = ImmediateWrapper(fact)
        imm.fact.section = sec_name
        imm.evidence.source = "jumptable_base"
        self.immediates.append(imm)
    
    # 存储跳转表项的立即值
    def save_switch_item_imm(self, slot, table_base, section, function):
        value = section.read_at(slot, SWITCH_ITEM_SIZE)   # 默认了跳转表项是4位偏移
        if not value:
            return False

        # 计算跳转表项实际的跳转目标地址（PC相对寻址）
        target_address = (value + table_base) & 0xffffffff
        # 验证是否为函数内的有效指令地址
        if not function.is_valid_instruction(target_address):
            return False
        
        fact = ImmediateFact(
            value=value,
            imm_size=SWITCH_ITEM_SIZE,
            inst_address=None,      # 数据段没有指令
            inst_size=None,
            imm_address=slot,
            imm_offset=None,
            kind="Disp"
        )
        imm = ImmediateWrapper(fact)
        imm.fact.section = section.name
        imm.evidence.target_address = target_address
        imm.evidence.target_section = self.container.get_section_by_address(imm.evidence.target_address)
        imm.evidence.source = "jumptable_offset"
        imm.evidence.jumptable_base = table_base

        self.immediates.append(imm)
        return True

        

    # 根据可能的跳转表基址计算可能的跳转表项
    def collect_swtich_items(self, container):
        # 获取.rodata只读数据段
        rodata = container.sections.get(".rodata", None)
        if not rodata:
            return

        # 收集的所有可能的switch表基址
        all_bases = set([x for _, y in self.pot_sw_bases.items() for x in y])

        # 遍历每个函数及其对应的switch表基址
        for faddr, swbases in self.pot_sw_bases.items():
            fn = container.functions[faddr]
            # 按地址降序遍历每个switch表基址
            for swbase in sorted(swbases, reverse=True):
                # 存储第一个跳转表项
                if self.save_switch_item_imm(swbase, swbase, rodata, fn) == False:
                    continue
                # 存储跳转表的基址（根据retrowrite的标签插入思想，这里无需单独对跳转表基址进行建模）
                # self.save_switch_base_imm(swbase, rodata.name)

                # 继续符号化后续的跳转表项
                for slot in range(swbase + 4, rodata.base + rodata.sz, 4):
                    # 检查当前槽位是否与其他switch表基址冲突
                    if any([x in all_bases for x in range(slot, slot + 4)]):
                        break
                    # 存储剩余的跳转表项
                    if self.save_switch_item_imm(slot, swbase, rodata, fn) == False:
                        break

    
    # ssx: 处理数据段中的候选符号化立即值
    def collect_data_immediates(self, container):
        """
        扫描数据段及扩展区域，收集可能的候选符号化立即值
        返回 ImmediateWrapper 列表
        """
        addr_ranges = container.get_valid_target_address()
        def is_in_valid_range(val):
            for start, end in addr_ranges:
                if start <= val < end:
                    return True
            return False
        
        for sec_name in DATASECTIONS:
            sec = self.container.get_section(sec_name)
            if not sec:
                continue

            data = sec.data()       # 返回该节区的原始字节内容
            base = sec['sh_addr']

            for offset in range(0, len(data) - PTR_SIZE + 1, PTR_SIZE):
                raw = data[offset:offset + PTR_SIZE]
                val = struct.unpack("<Q", raw)[0] # 小端解析64位值
                # NULL指针直接跳过
                if val == 0:
                    continue
                # 检查是否落在有效区域
                if not is_in_valid_range(val):
                    continue
                fact = ImmediateFact(
                    value=val,
                    imm_size=PTR_SIZE,
                    inst_address=None,      # 数据段没有指令
                    inst_size=None,
                    imm_address=base + offset,
                    imm_offset=None, # 为了和重定位表中收集的立即值保持一致，暂时不需要offset这个属性
                    kind="Imm"
                )
                imm = ImmediateWrapper(fact)
                imm.fact.section = sec.name
                imm.evidence.target_address = val
                imm.evidence.target_section = container.get_section_by_address(imm.evidence.target_address)
                if sec_name == ".init_array":
                    imm.evidence.source = ".init_array"
                    # imm.evidence.target_address = None  # init_array中的地址通常不是直接的目标地址

                self.immediates.append(imm)

        self.collect_swtich_items(container)

    # 依靠重定位表的目标位置收集补充一部分候选立即值,重复收集的后面会去重
    def collect_reloc_immediates(self, container):
        """
        收集重定位表中的候选立即值

        返回 ImmediateWrapper 列表
        """
        for sec_name, relocs in container.relocations.items():  # sec_name: ".dyn", ".plt"
            for reloc_item in relocs:
                reloc_type = reloc_item['type']
                # 跳过某些特定的重定位类型
                # R_X86_64_COPY: 复制重定位，由动态链接器处理
                # R_X86_64_REX_GOTPCRELX: 优化后的GOTPCRELX重定位
                # R_386_COPY: 32位版本的复制重定位
                if reloc_type in [ENUM_RELOC_TYPE_x64['R_X86_64_COPY'], ENUM_RELOC_TYPE_x64['R_X86_64_REX_GOTPCRELX']]:
                    continue
                # 初始化一个立即值
                fact = ImmediateFact(
                    value=reloc_item['addend'],
                    imm_size=PTR_SIZE,
                    inst_address=None,      # 重定位表没有指令
                    inst_size=None,
                    imm_address=reloc_item['offset'],
                    imm_offset=None,
                    kind="Imm"
                )
                imm = ImmediateWrapper(fact)
                section_name = container.get_section_by_address(reloc_item['offset'])
                imm.fact.section = section_name
                # reloc_item['addend']并非目标地址，而是个修正值
                # imm.evidence.target_address = reloc_item['addend'] 
                # imm.evidence.target_section = container.get_section_by_address(imm.evidence.target_address)
                imm.evidence.source = "reloc"

                # 根据重定位类型计算目标地址
                # 非 PIC 文件，直接计算绝对地址
                if reloc_type in [ENUM_RELOC_TYPE_x64["R_X86_64_64"], ENUM_RELOC_TYPE_x64["R_X86_64_PC32"]]:
                    # 目标绝对地址 = 符号地址 + 加数
                    imm.evidence.target_address = reloc_item['st_value'] + reloc_item['addend']
                    imm.evidence.target_section = container.get_section_by_address(imm.evidence.target_address)
                # 没有符号地址的情况其目标地址等于addend
                elif reloc_type == ENUM_RELOC_TYPE_x64["R_X86_64_RELATIVE"] or reloc_item['st_value'] == None:
                    # 目标地址 = 加数 (非 PIC, 静态基址通常是 0)
                    imm.evidence.target_address = reloc_item['addend']
                    imm.evidence.target_section = container.get_section_by_address(imm.evidence.target_address)


                self.immediates.append(imm)

                

    def save_immediates_to_txt(self, folder_path):
        import os
        os.makedirs(folder_path, exist_ok=True)

        file_path = os.path.join(folder_path, "eviImmediates.json")
        # 写入 JSON 文件
        with open(file_path, "w") as f:
            json.dump([imm.to_dict() for imm in self.immediates], f, indent=4) 
        print(f"[*] Saved {len(self.immediates)} immediates to {file_path}")


# 不可变事实
class ImmediateFact:
    def __init__(self, value, imm_size, inst_address, imm_address, inst_size, imm_offset, kind):
        self.value = value  # 立即值值（偏移或绝对值）
        self.imm_size = imm_size    # 立即值大小（字节数） 4 / 8
        self.inst_address = inst_address    # 立即值所在指令的起始地址
        self.inst_size = inst_size          # 立即值所在指令的大小
        self.imm_address = imm_address    # 立即值本身的地址
        self.imm_offset = imm_offset     # 立即值相对于所在段的偏移
        self.kind = kind    # 立即值来源类型 "Imm", "Disp"


        # 上下文事实
        self.section = None                 
        self.function_address = None                # 所在函数起始地址 
        self.asmline = ''                   # 包含该立即值的汇编指令行
        self.basicblock = None              # 所在基本块
        self.instr_mnemonic = None          # 包含该立即值的汇编指令助记符
        self.operand_index = None           # 立即值在指令操作数中的索引
    
    def to_dict(self):
        return {
            "value": self.value,
            "imm_size": self.imm_size,
            "kind": self.kind,
            "inst_address": self.inst_address,
            "inst_size": self.inst_size,
            "imm_address": self.imm_address,
            "imm_offset": self.imm_offset,
            "section": self.section,
            "function_address": self.function_address,
            "instr_mnemonic": self.instr_mnemonic,
            "operand_index": self.operand_index,
            "asmline": self.asmline,
        }

class ImmediateMeta:
    def __init__(self):

        """
        初始化方法
        初始化 Capstone 指令对象为 None
        """
        self.inst_wrapper = None          # 存储container中inst对象，包括.cs-Capstone 指令对象，初始值为 None
        # 下面的asm_is_属性用于reassessor过来的gt数据
        self.asm_is_call = None
        self.asm_is_jmp = None
        self.asm_is_lea = None
        self.asm_is_pc_relative = None
        self.asm_is_rbp_based = None
        self.is_jumptable_base = None
        self.is_jumptable_item = None
# 分析产生
class ImmediateEvidence:
    def __init__(self):
        self.target_address = None    # 立即值参与计算后的最终地址
        self.target_section = None    # 立即值参与计算后的最终地址所在的section
        self.address_from = None      # call / PC_REL / RIP_REL
        self.source = None            # 立即值来源描述 pc / got/ plt / global
        self.jumptable_base = None      # 如果时跳转表的偏移，用于记录跳转表地址
        self.relocation = None     # 如果立即值may_label来源于reloc，存储relocation相关信息
        self.flags = []            # {"R2", "R11"}
        self.explanations = []     # 证据解释说明
        self.score = 0.0              # 置信度/评分
        self.may_label = None         # 符号化名字

    def to_dict(self):
        return {
            "source": self.source,
            "address_from": self.address_from,
            "target_address": self.target_address,
            "target_section": self.target_section,
            'jumptable_base': self.jumptable_base,
            "flags": list(self.flags),
            "explanations": list(self.explanations),
            "score": self.score,
            "may_label": self.may_label,
        }

# 最终裁决
class ImmediateDecision:
    def __init__(self):
        self.must_symbolize = "S?"    # S+ / S- / S? 是否必须符号化
        self.final_label = None         # 实际立即值符号化后的结果，即解析后的“符号”或者“抽象表示”
        self.type = None
        self.reason = []                
    
    def to_dict(self):
        return {
            "must_symbolize": self.must_symbolize,
            "final_label": self.final_label,
            "type": self.type,
            "reason": self.reason,
        }

# new
class ImmediateWrapper():
    """
    ImmediateWrapper：立即值的统一抽象对象
    - fact      : 客观事实（不可变）
    - evidence  : 分析证据（可变）
    - decision  : 最终裁决（仅融合阶段写）
    """
    def __init__(self, data):
        """
        data 可以是：
        - ImmediateFact 对象（原始方式）
        - dict 对象，包含 fact/meta/evidence/decision 四部分(用于reasessor过来的gt dict数据)
        """
        if isinstance(data, dict):
            fact_dict = data.get("fact", {})
            meta_dict = data.get("meta", {})
            evidence_dict = data.get("evidence", {})
            decision_dict = data.get("decision", {})

            # 初始化 fact
            self.fact = ImmediateFact(
                value=fact_dict.get("value"),
                imm_size=fact_dict.get("imm_size"),
                inst_address=fact_dict.get("inst_address"),
                inst_size=fact_dict.get("inst_size"),
                imm_address=fact_dict.get("imm_address"),
                imm_offset=fact_dict.get("imm_offset"),
                kind=fact_dict.get("kind")
            )
            # 额外字段
            self.fact.section = fact_dict.get("section")
            self.fact.function_address = fact_dict.get("function_address")
            self.fact.asmline = fact_dict.get("asmline", "")
            self.fact.basicblock = fact_dict.get("basicblock")
            self.fact.instr_mnemonic = fact_dict.get("instr_mnemonic")
            self.fact.operand_index = fact_dict.get("operand_index")

            # 初始化 meta
            self.meta = ImmediateMeta()
            for k, v in meta_dict.items():
                setattr(self.meta, k, v)

            # 初始化 evidence
            self.evidence = ImmediateEvidence()
            self.evidence.target_address = evidence_dict.get("target_address")
            self.evidence.address_from = evidence_dict.get("address_from")
            self.evidence.source = evidence_dict.get("source")
            flags = evidence_dict.get("flags")
            self.evidence.flags = list(flags) if flags else []
            explanations = evidence_dict.get("explanations")
            self.evidence.explanations = list(explanations) if explanations else []
            self.evidence.score = evidence_dict.get("score", 0.0)

            # 初始化 decision
            self.decision = ImmediateDecision()
            self.decision.must_symbolize = decision_dict.get("must_symbolize", "S?")
            self.decision.final_label = decision_dict.get("final_label")
            self.decision.reason = decision_dict.get("reason", [])

        elif isinstance(data, ImmediateFact):
            # 原始初始化方式
            self.fact = data
            self.meta = ImmediateMeta()
            self.evidence = ImmediateEvidence()
            self.decision = ImmediateDecision()

    def to_dict(self):
        return {
            "fact": self.fact.to_dict(),
            "evidence": self.evidence.to_dict(),
            "decision": self.decision.to_dict(),
        }