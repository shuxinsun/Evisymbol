from elftools.elf.enums import ENUM_RELOC_TYPE_x64
from lib.consts import DATASECTIONS, PTR_SIZE
class Symbolizer:
    def __init__(self, container):
        self.container = container
        self.defined_labels = set()

    def symbolize(self, imm):
        suffix = ''
        flags = imm.evidence.flags
        # 目标地址在.plt里面或命中了**重定位表项**带有@PLT的符号
        if 'reloc.plt' in flags or 'plt_entry' in flags:
            suffix = '@PLT'
        # 目标地址在GOT中且重定位偏移匹配且是PC寻址
        elif ("got_entry" in flags or 'gotplt_entry' in flags) and 'reloc' in flags and 'pc_relative' in flags:
            suffix = '@GOTPCREL'
    
        # 数据段中命中重定位表的立即值
        if imm.fact.section in DATASECTIONS and 'reloc' in imm.evidence.flags:
            reloc_label = self.resolve_relocation_label(imm)
            if reloc_label:
                imm.evidence.may_label = reloc_label

        may_label = imm.evidence.may_label
        if may_label:
            # 动态符号表的中的全局变量也会在这里进行处理
            imm.decision.final_label = f"{may_label}{suffix}"
        else:
            if 'jumptable_base' in flags:
                # 跳转表基址需要单独生成一个锚点（retrowritedump的时候对数据段中的每个字节都生成了锚点）
                pass
            # 跳转表项
            elif 'jumptable_offset' in flags:
                imm.decision.final_label = f".LC{imm.evidence.target_address:x}-.LC{imm.evidence.jumptable_base:x}"
            # 其他
            else:
                if imm.evidence.target_address:
                    imm.decision.final_label = f".LC{imm.evidence.target_address:x}"
                elif imm.fact.value:
                    imm.decision.final_label = f".LC{imm.fact.value:x}"
                else:
                    imm.decision.reason = f"Cannot be symbolized because no target address/value is available."
        
        # 替换container中的符号化建模
        # 存储现有定义的label
        if imm.decision.final_label and imm.decision.final_label not in self.defined_labels:
            self.defined_labels.add(imm.decision.final_label)

        # 代码段替换
        if imm.fact.section == '.text' and imm.decision.final_label and imm.fact.value and imm.meta.inst_wrapper:
            inst = imm.meta.inst_wrapper
            inst.op_str = inst.op_str.replace(
                        hex(imm.fact.value), imm.decision.final_label)
        
        
        # 数据引用的替换
        if imm.fact.section in DATASECTIONS and imm.decision.final_label and imm.fact.imm_address:
            # 包括跳转表在内，所有数据引用都替换为final_label
            imm_size = imm.fact.imm_size if imm.fact.imm_size else PTR_SIZE
            imm_section = self.container.sections.get(imm.fact.section, None)
            if not imm_section:
                return
            imm_section.replace(imm.fact.imm_address, imm_size, imm.decision.final_label)
        

    def resolve_relocation_label(self, imm):
        ev = imm.evidence
        reloc = getattr(ev, "relocation", None)
        if not reloc:
            return None

        rtype  = reloc.get("type")
        st_val = reloc.get("st_value", 0)
        addend = reloc.get("addend", 0)
        sym    = reloc.get("name")
        offset = reloc.get("offset")

        # ---------------- PC32 ----------------
        if rtype == ENUM_RELOC_TYPE_x64["R_X86_64_PC32"]:
            swbase = None
            for base in sorted(self.container.bases):
                if base > offset:
                    break
                swbase = base
            if swbase is None:
                return None

            value = st_val + addend - (offset - swbase)
            imm.fact.imm_size = 4
            return ".LC%x-.LC%x" % (value, swbase)

        # ---------------- ABS64 ----------------
        elif rtype == ENUM_RELOC_TYPE_x64["R_X86_64_64"]:
            if st_val:
                return ".LC%x" % (st_val + addend)
            return f"{sym}+{addend}" if addend else sym

        # ---------------- RELATIVE ----------------
        elif rtype == ENUM_RELOC_TYPE_x64["R_X86_64_RELATIVE"]:
            return ".LC%x" % addend

        return None
