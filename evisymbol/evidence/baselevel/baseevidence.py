from capstone import CS_OP_MEM
from capstone.x86 import X86_REG_RIP
from lib.consts import MODE_WEIGHT_ANALYSIS, MODE_MAPPING

class BaseLevelEvidence:
    """
    基础证据层（Evidence Fusion Layer）

    职责：
    - 消费 ImmediateWrapper 中已填充的证据
    - 执行强反证据（R1）否决
    - 执行强正证据（R2 / R3等）确认
    - 不重新解析指令、不重新计算 target_address

    存在的问题：
    - 在基础证据层,当前目标地址计算的并不全面,因此基础证据层在后续证据补齐过程中可能被再次调用
    """

    def __init__(self, container, immediates, evidence_counts, address_range_stats):
        self.container = container
        self.immediates = immediates
        self.evidence_counts = evidence_counts
        self.address_range_stats = address_range_stats
        # 获取合法地址范围（只计算一次）
        self.valid_addr_ranges = container.get_valid_target_address()
        # 符号表缓存到container中（地址 -> (符号名, section_name)）
        if not hasattr(container, "_symtab_cache"):
            container._build_symtab_cache(container.loader.elffile)

    # ------------------ R1：强反证据 ------------------
    # R1:目标地址不在合法区间内
    def apply_r1_address_range(self, imm, mode=None):

        ev = imm.evidence
        addr = ev.target_address
        if addr is None:
            return
        
        # 计算距离最近合法区间的绝对偏离距离
        distance = self._compute_distance_to_valid_range(addr)
        in_range = any(start <= addr < end for start, end in self.valid_addr_ranges)
        # 符号化gt中目标地址为0的立即值不算做统计数值内
        if mode and MODE_MAPPING[mode] == MODE_WEIGHT_ANALYSIS and addr == 0:
            return

        # 统计 in_range
        if in_range:
            if self.not_in_UNKNOWN_REGION:
                self.evidence_counts['r1-address-range'] += 1
            self.address_range_stats['in_range'] += 1
        else:
            # 按 1KB、2KB、3KB、4KB… 分 bucket
            if distance > 4*1024:
                self.address_range_stats['out_4kb_plus'] += 1
                ev.score -= 3
                ev.explanations.append(
                    f"[R1] - 3 : Immediate is out of the valid address range 4KB+ "
                    f"at {imm.fact.asmline} (address: {imm.fact.inst_address})"
                )
            elif distance > 3*1024:
                self.address_range_stats['out_3_4kb'] += 1
                ev.score -= 3
                ev.explanations.append(
                    f"[R1] - 3 : Immediate is out of the valid address range 3KB~4KB "
                    f"at {imm.fact.asmline} (address: {imm.fact.inst_address})"
                )
            elif distance > 2*1024:
                self.address_range_stats['out_2_3kb'] += 1
                ev.score -= 1
                ev.explanations.append(
                    f"[R1] - 1 : Immediate is out of the valid address range 2KB~3KB "
                    f"at {imm.fact.asmline} (address: {imm.fact.inst_address})"
                )
            elif distance > 1*1024:
                self.address_range_stats['out_1_2kb'] += 1
                ev.score -= 1
                ev.explanations.append(
                    f"[R1] - 1 : Immediate is out of the valid address range 1KB~2KB "
                    f"at {imm.fact.asmline} (address: {imm.fact.inst_address})"
                )
            else:
                # 小于 1KB 的也可以统计
                self.address_range_stats['out_0_1kb'] += 1
                ev.score -= 0.5
                ev.explanations.append(
                    f"[R1] - 0.5 : Immediate is out of the valid address range <1KB "
                    f"at {imm.fact.asmline} (address: {imm.fact.inst_address})"
                )
    
    # 辅助方法：计算距离最近合法区间的绝对偏离
    def _compute_distance_to_valid_range(self, addr):
        """
        返回：
        - 如果在区间内：distance = 0
        - 如果不在区间内：距离最近边界的字节数
        """
        min_dist = None
        for start, end in self.valid_addr_ranges:
            if start <= addr < end:
                return 0  # 在合法区间

            if addr < start:
                dist = start - addr
            else:
                dist = addr - end

            if min_dist is None or dist < min_dist:
                min_dist = dist

        return min_dist


    # ------------------ R2：符号表强正证据 ------------------
    # R2:目标地址恰好等于符号表中某个符号的地址
    def apply_r2_symtab_evidence(self, imm, mode=None):
        """
        使用符号表为立即值打分，同时支持符号+偏移的匹配。
        # 立即值本身在机器码中是相对值，而符号表存的是绝对值会根据不同的寻址模式判断是st_value使用的绝对地址还是相对地址
        # RIP寻址、Imm的形式使用target_address判断，符号表存储的绝对地址
        # 其他模式使用自身的值判断, 符号表存储的这个符号本身的值
        """
        # 选择用于匹配符号表的值
        st_value = None
        meta = getattr(imm, "meta", None)

        if imm.fact.kind == "Imm":
            # 立即值本身就是机器码的立即值，通常用于 RIP 相对寻址
            st_value = imm.evidence.target_address
        else:
            # 检查是否为 RIP 相对寻址
            is_rip = False
            if mode and MODE_MAPPING.get(mode) == MODE_WEIGHT_ANALYSIS:
                is_rip = getattr(meta, "asm_is_pc_relative", False)
            else:
                inst_wrapper = getattr(meta, "inst_wrapper", None)
                if inst_wrapper:
                    for op in inst_wrapper.cs.operands:
                        if op.type == CS_OP_MEM and op.mem.base == X86_REG_RIP:
                            is_rip = True
                            break
            st_value = imm.evidence.target_address if is_rip else imm.fact.value

        if st_value is None:
            return


        # === 静态符号表数据匹配 ===

        # 可直接匹配符号表的情况
        if st_value in self.container._symtab_cache:
            sym_name, sym_type, _, sym_source, visibility = self.container._symtab_cache[st_value]
            if self.not_in_UNKNOWN_REGION:
                self.evidence_counts['r2-symtab'] += 1
            ev = imm.evidence
            # 隐藏符号会符号化但是不需要加后缀
            if sym_type == 'STT_OBJECT' and visibility != "STV_HIDDEN": 
                ev.may_label = "{}_{:x}".format(sym_name, st_value)
            else: 
                ev.may_label = "{}".format(sym_name)
            ev.score += 3.5
            ev.flags.append(sym_source)
            ev.explanations.append(
                f"[R2] + 3.5 : matches symbol {sym_name} "
                f"at instruction {imm.fact.asmline} (inst addr: {imm.fact.inst_address})"
            )
            return

        # 可能存在符号表st_value+偏移的情况，区间查找
        matched_symbol = None
        matched_offset = 0
        
        for start, end, name, type, sec, visibility in self.container._symtab_intervals:
            # 只有数据才会做模糊匹配，函数只做前面的入口查询
            if type == 'STT_OBJECT' and start <= st_value < end:
                matched_symbol = (name, type, sec)
                matched_offset = st_value - start
                break

        if matched_symbol:
            sym_name, sym_type, sym_sec = matched_symbol
            if self.not_in_UNKNOWN_REGION:
                self.evidence_counts['r2-symtab'] += 1
            ev = imm.evidence
            # st_value-matched_offset用于计算符号本身所在的地址
            if sym_type == 'STT_OBJECT' and visibility != "STV_HIDDEN":
                ev.may_label = "{}_{:x}+0x{:x}".format(sym_name, st_value-matched_offset, matched_offset)
            else:
                ev.may_label = "{}".format(sym_name)
            ev.score += 3.5
            ev.flags.append(sym_sec)
            ev.explanations.append(
                f"[R2] + 3.5 : matches symbol {sym_name} "
                f"(offset: {matched_offset}) "
                f"at instruction {imm.fact.asmline} (inst addr: {imm.fact.inst_address})"
            )
            return
        
        # === dynsym 数据对象匹配(符号化方式不太一样) ===
        for start, end, name, visibility in self.container._dynsym_obj_intervals:
            if start <= st_value < end:
                offset = st_value - start
                if self.not_in_UNKNOWN_REGION:
                    self.evidence_counts['r2-symtab'] += 1
                ev = imm.evidence
                if visibility != "STV_HIDDEN" and offset != 0: 
                    ev.may_label = "{}_{:x}+0x{:x}".format(name, st_value-offset, offset)
                else:
                    ev.may_label = "{}".format(name)
                ev.score += 3.5
                ev.flags.append(".dynsym")
                ev.explanations.append(
                    f"[R2] + 3.5 : matches dynsym object {name} "
                    f"(offset: {offset}) at instruction {imm.fact.asmline} "
                    f"(inst addr: {imm.fact.inst_address})"
                )
                return
        
    
    # --------------------------------------------------
    # R3: 立即值在 relocation 表中
    # --------------------------------------------------
    def apply_r3_relocation_backed(self, imm):
        ev = imm.evidence
        fact = imm.fact

        # 因为reassessor解析到得重定位项是Disp，所以这里不再限制为imm
        # if fact.kind != "Imm":
        #     return

        # 只看“全局语义 relocation”，忽略 section reloc
        global_relocs = getattr(self.container, "relocations", None)
        if not global_relocs:
            return

        # Level A: 精确到立即值
        imm_addr = getattr(fact, "imm_address", None)
        imm_size = getattr(fact, "imm_size", None)

        # Level B: 只能精确到指令
        inst_addr = getattr(fact, "inst_address", None)
        inst_size = getattr(fact, "inst_size", None)

        for reloc_sec, relocs in global_relocs.items():
            for reloc in relocs:
                reloc_off = reloc.get("offset")
                reloc_type = reloc.get("type")
                symbol_name = reloc.get("name")

                if reloc_off is None:
                    continue
                
                # 恰好完全匹配得情况
                if imm_addr is not None and imm_addr == reloc_off or inst_addr is not None and inst_addr == reloc_off:
                    if self.not_in_UNKNOWN_REGION:
                        self.evidence_counts['r3-relocation-exact'] += 1
                    ev.score += 3.5
                    ev.flags.append(f"reloc")
                    ev.flags.append(f"reloc{reloc_sec}")
                    ev.explanations.append(
                        f"[R3] + 3.5 : Immediate matches relocation exactly "
                        f"(byte-precise, type={reloc_type}) "
                        f"at .rela{reloc_sec} offset {reloc_off} "
                    )
                    # 重定位表中的部分符号可能也没有符号名
                    if ev.may_label is None:
                        ev.may_label = symbol_name
                    ev.relocation = reloc
                    return reloc_sec

                # ---------- Level A ----------
                    return reloc_sec

                # ---------- Level A ----------
                # relocation 的修补位置，是否落在这个立即值的字节范围内
                if imm_addr is not None and imm_size is not None:
                    if imm_addr <= reloc_off < imm_addr + imm_size:
                        ev.score += 3
                        ev.flags.append("reloc")
                        ev.explanations.append(
                            f"[R3] + 3 : Relocation falls within immediate  "
                            f"(byte-precise, type={reloc_type}) "
                            f"at {fact.asmline}"
                        )
                        ev.may_label = symbol_name
                        ev.relocation = reloc
                        return reloc_sec

                # ---------- Level B ----------
                # relocation 的修补位置，是否落在这个立即值所在指令的字节范围内
                if inst_size is not None:
                    if inst_addr <= reloc_off < inst_addr + inst_size:
                        ev.score += 2
                        ev.flags.append("reloc")
                        ev.explanations.append(
                            f"[R3] + 2 : Relocation falls within instruction "
                            f"(instruction-level, type={reloc_type}) "
                            f"at {fact.asmline}"
                        )
                        ev.may_label = symbol_name
                        ev.relocation = reloc
                        return reloc_sec
                    
            

    # ------------------ 运行所有证据 ------------------
    def run(self, imm, not_in_UNKNOWN_REGION, mode):
        self.not_in_UNKNOWN_REGION = not_in_UNKNOWN_REGION
        reloc_sec = self.apply_r3_relocation_backed(imm)
        if reloc_sec != '.dyn':
            self.apply_r1_address_range(imm, mode)
        self.apply_r2_symtab_evidence(imm, mode)
        return self.immediates
