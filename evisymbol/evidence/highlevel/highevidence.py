from capstone import CS_GRP_CALL, CS_OP_REG
from capstone.x86 import *

class HighLevelEvidence:
    """
    高级证据层（Local VSA / Def-Use）
    本质逻辑都是寄存器前向传播分析，只不过R19关注寄存器作为跳转目标的控制流语义，R20关注寄存器作为函数参数的数据流语义。
    R20: 局部值集分析（Forward），识别立即值通过寄存器传播到 call 的情况
    R21: 局部值集分析（Backward），识别立即值通过寄存器传播到函数参数的情况
    """

    def __init__(self, container, immediates, evidence_counts, max_hops=15):
        self.container = container
        self.ins_map = container.ins_map          # addr -> InstructionWrapper
        self.immediates = immediates
        self.evidence_counts = evidence_counts
        self.max_hops = max_hops
        # ABI 参数寄存器列表
        self.ABI_PARAM_REGS = [
            X86_REG_RDI,  # 第1个参数
            X86_REG_RSI,  # 第2个参数
            X86_REG_RDX,  # 第3个参数
            X86_REG_RCX,  # 第4个参数
            X86_REG_R8,   # 第5个参数
            X86_REG_R9    # 第6个参数
        ]

    # 基址寄存器是 RBP的情况
    def is_rbp_related(self, imm):
        inst_wrapper = getattr(imm.meta, "inst_wrapper", None)
        try:
            op = inst_wrapper.cs.operands[imm.fact.operand_index]
        except IndexError:
            return False
        if op.mem.base == X86_REG_RBP:
            return  True
        return False

    # --------------------------------------------------
    # R20: forward local VSA 是否传输到了控制流里面
    # --------------------------------------------------
    def apply_r20_forward_vsa(self, imm):
        ev = imm.evidence
        inst_wrapper = getattr(imm.meta, "inst_wrapper", None)
        if inst_wrapper is None:
            return
        cur_cs = inst_wrapper.cs

        # 排除基址寄存器是 RBP的情况
        if self.is_rbp_related(imm):
            return
        # if imm.fact.asmline == r'movl $0x60f140, %edi':
        #     print(cur_cs.operands[1].reg)
        # ① 找立即值“定义”的寄存器
        start_reg = self.get_written_reg(cur_cs)

        if start_reg is None:
            return

        start_reg = self.canon(start_reg)
        cur_addr = cur_cs.address
        hops = 0
        # 临时路径记录
        path_explanations = [f"Start reg=0x{start_reg:x} at 0x{cur_cs.address:x}"]


        # 如果是从内存加载到寄存器，切断立即数依赖(从表达式读出来并且又赋值给同一个寄存器，意味着基址并非立即数，而是寄存器中的值，意味着立即数并非基址，阻断)
        if cur_cs.id == X86_INS_MOV:
            ops = cur_cs.operands
            if len(ops) == 2 and ops[0].type == CS_OP_MEM and ops[0].mem.base != X86_REG_INVALID:
                written = self.canon(ops[1].reg)
                if written == start_reg:
                    ev.score -= 3
                    ev.source = "r20-forward-vsa"
                    path_explanations.append(
                        f"dependency killed by memory load at 0x{cur_cs.address:x}"
                    )
                    ev.explanations.append(
                        f"[R20 stop] - 3: " + " => ".join(path_explanations)
                    )
                    return
    
        while hops < self.max_hops:
            next_addr = self._get_next_ins_addr(
                cur_addr, imm.fact.function_address
            )
            
            if next_addr is None:
                return

            next_ins = self.ins_map.get(next_addr)
            if next_ins is None:
                return

            # 在ImmediateWrapper叫cs
            next_cs = getattr(next_ins, "cs", None)
            if next_cs is None:
                return

            # ② 寄存器被重新定义 → 停止
            for r in next_cs.regs_write:
                if self.canon(r) == start_reg:
                    ev.score -= 2
                    ev.source = "r20-forward-vsa"
                    path_explanations.append(f"reg overwritten at 0x{next_cs.address:x}")
                    ev.explanations.append(
                        f"[R20 stop] - 2 : " + " => ".join(path_explanations)
                    )
                    return

            # ③ 命中 call（寄存器作为调用目标）
            if self.is_indirect_cf(next_cs):
                ops = next_cs.operands
                if len(ops) == 1:
                    op = ops[0]
                    target_reg = None

                    if op.type == CS_OP_REG:
                        target_reg = self.canon(op.reg)
                    elif op.type == CS_OP_MEM and op.mem.base:
                        target_reg = self.canon(op.mem.base)

                    if target_reg == start_reg:
                        # print("immediate propagated to indirect call/jmp target:")
                        # print(imm.fact.asmline, start_reg)
                        # print(next_ins, next_cs.regs_read)
                        ev.score += 6
                        ev.source = "r20-forward-vsa"
                        path_explanations.append(f"propagated to indirect call/jmp at 0x{next_cs.address:x}(hops={hops})")
                        ev.explanations.append(
                            f"[R20] + 6 : " + " => ".join(path_explanations)
                        )
                        return

            # 拦截start_reg 参与非 mov/lea 的算术、逻辑指令（寄存器被污染）
            if start_reg in map(self.canon, next_cs.regs_read):
                if next_cs.id not in (X86_INS_MOV, X86_INS_LEA):
                    ev.score -= 1
                    ev.source = "r20-forward-vsa"
                    path_explanations.append(f"reg tainted by non-linear op at 0x{next_cs.address:x}")
                    ev.explanations.append(
                        f"[R20 stop] - 1 : " + " => ".join(path_explanations)
                    )
                    return
            
            # 寄存器传递的情况
            new_reg = self.propagate_register(next_cs, start_reg)
            if new_reg:
                path_explanations.append(f"propagated {start_reg:x} -> {new_reg:x} at 0x{next_cs.address:x}")
                start_reg = new_reg


            # ⑤ RIP-relative LEA（构造地址）
            if next_cs.id == X86_INS_LEA:
                ops = next_cs.operands
                if (
                    len(ops) == 2
                    and ops[0].type == CS_OP_REG
                    and self.canon(ops[0].reg) == start_reg
                    and ops[1].mem.base == X86_REG_RIP
                ):
                    # print("immediate propagated to RIP-relative address:")
                    # print(imm.fact.asmline, start_reg)
                    # print(next_ins, next_cs.regs_read)
                    disp = ops[1].mem.disp
                    target = next_cs.address + next_cs.size + disp
                    ev.score += 6
                    ev.target_address = target
                    ev.source = "r20-forward-vsa"
                    path_explanations.append(f"immediate propagated to RIP-relative address 0x{target:x} at 0x{next_cs.address:x}")
                    ev.explanations.append(
                        f"[R20] + 6 : " + " => ".join(path_explanations)
                    )
                    return

            cur_addr = next_addr
            hops += 1

    # --------------------------------------------------
    # helpers
    # --------------------------------------------------
    def propagate_register(self, cs_ins, start_reg):
        """
        检查当前指令是否是寄存器传递形式，如果是则更新 start_reg。
        支持：
            1. mov reg, reg
            2. xchg reg, reg
            3. movsx / movzx reg, reg
            4. lea reg, [base + index*scale + disp]
        返回：
            updated start_reg 或 None（未传播）
        """
        propagated = False
        ops = cs_ins.operands

        # MOV reg, reg
        if cs_ins.id == X86_INS_MOV and len(ops) == 2:
            if ops[0].type == CS_OP_REG and ops[1].type == CS_OP_REG:
                if self.canon(ops[0].reg) == start_reg:
                    start_reg = self.canon(ops[1].reg)
                    propagated = True

        # XCHG reg, reg_交换两个寄存器的值
        elif cs_ins.id == X86_INS_XCHG and len(ops) == 2:
            if ops[0].type == CS_OP_REG and ops[1].type == CS_OP_REG:
                if self.canon(ops[0].reg) == start_reg:
                    start_reg = self.canon(ops[1].reg)
                    propagated = True
                elif self.canon(ops[1].reg) == start_reg:
                    start_reg = self.canon(ops[0].reg)
                    propagated = True

        # MOVZX / MOVSX_直接把源寄存器映射到目标寄存器
        elif cs_ins.id in (X86_INS_MOVZX, X86_INS_MOVSX) and len(ops) == 2:
            if ops[0].type == CS_OP_REG and ops[1].type == CS_OP_REG:
                if self.canon(ops[0].reg) == start_reg:
                    start_reg = self.canon(ops[1].reg)
                    propagated = True

        # 通用 LEA_LEA 参与传播
        elif cs_ins.id == X86_INS_LEA and len(ops) == 2:
             if ops[1].type == CS_OP_REG and ops[0].type == CS_OP_MEM:
                dst_reg = self.canon(ops[1].reg)  # 目标寄存器
                mem = ops[0].mem                   # 源操作数是内存表达式
                base_match = mem.base and self.canon(mem.base) == start_reg
                index_match = mem.index and self.canon(mem.index) == start_reg
                if base_match or index_match:
                    start_reg = dst_reg
                    propagated = True

        if propagated:
            return start_reg
        return None

    def is_indirect_cf(self, cs_ins):
        """
        是否是间接控制流转移（call reg / jmp reg / jmp [mem]）
        """
        if cs_ins.id in (X86_INS_CALL, X86_INS_JMP):
            # 直接 jmp imm / call imm 不算
            for op in cs_ins.operands:
                if op.type in (CS_OP_REG, CS_OP_MEM):
                    return True
        return False

    def get_written_reg(self, cs_ins):
        """
        只处理最基本的 def：
        mov imm, reg
        lea mem, reg
        """
        if cs_ins.id in (X86_INS_MOV, X86_INS_LEA):
            if cs_ins.operands:
                dst = cs_ins.operands[1] # 只处理目标寄存器,operands[0] 是源操作数
                # 不依赖 dst.type → 避免 32 位寄存器解析问题
                if getattr(dst, 'reg', 0):  # 有寄存器就返回
                    return dst.reg
        return None

    def canon(self, reg):
        """
        寄存器归一化：任意子寄存器 → 64位主寄存器
        """
        table = {
            # RAX
            X86_REG_AL: X86_REG_RAX, X86_REG_AH: X86_REG_RAX,
            X86_REG_AX: X86_REG_RAX, X86_REG_EAX: X86_REG_RAX,
            X86_REG_RAX: X86_REG_RAX,

            # RBX
            X86_REG_BL: X86_REG_RBX, X86_REG_BH: X86_REG_RBX,
            X86_REG_BX: X86_REG_RBX, X86_REG_EBX: X86_REG_RBX,
            X86_REG_RBX: X86_REG_RBX,

            # RCX
            X86_REG_CL: X86_REG_RCX, X86_REG_CH: X86_REG_RCX,
            X86_REG_CX: X86_REG_RCX, X86_REG_ECX: X86_REG_RCX,
            X86_REG_RCX: X86_REG_RCX,

            # RDX
            X86_REG_DL: X86_REG_RDX, X86_REG_DH: X86_REG_RDX,
            X86_REG_DX: X86_REG_RDX, X86_REG_EDX: X86_REG_RDX,
            X86_REG_RDX: X86_REG_RDX,

            # RDI
            X86_REG_DIL: X86_REG_RDI, X86_REG_DI: X86_REG_RDI,
            X86_REG_EDI: X86_REG_RDI, X86_REG_RDI: X86_REG_RDI,

            # RSI
            X86_REG_SIL: X86_REG_RSI, X86_REG_SI: X86_REG_RSI,
            X86_REG_ESI: X86_REG_RSI, X86_REG_RSI: X86_REG_RSI,

            # R8
            X86_REG_R8B: X86_REG_R8, X86_REG_R8W: X86_REG_R8,
            X86_REG_R8D: X86_REG_R8, X86_REG_R8: X86_REG_R8,

            # R9
            X86_REG_R9B: X86_REG_R9, X86_REG_R9W: X86_REG_R9,
            X86_REG_R9D: X86_REG_R9, X86_REG_R9: X86_REG_R9,
        }
        return table.get(reg, reg)

    def _get_next_ins_addr(self, inst_addr, fn_addr):
        """
        顺序扫描：只在函数内 forward
        """
        insts = self.container.functions[fn_addr].cache
        for i, ins in enumerate(insts):
            if ins.address == inst_addr and i + 1 < len(insts):
                return insts[i + 1].address
        return None

    def _get_prev_ins_addr(self, inst_addr, fn_addr):
        """
        顺序向前扫描：只在函数内 backward
        """
        insts = self.container.functions[fn_addr].cache
        for i, ins in enumerate(insts):
            if ins.address == inst_addr and i - 1 >= 0:
                return insts[i - 1].address
        return None


    # --------------------------------------------------
    # 公共函数：检查寄存器是否传播到 ABI 参数寄存器
    # --------------------------------------------------
    def _propagated_to_abi_reg(self, imm, start_reg, cur_addr, fn_addr, max_hops=6):
        """
        检查 start_reg 是否在函数内传播到 ABI 参数寄存器并可能被调用使用
        返回 (score_increment, path_explanations)
        """
        ev = imm.evidence
        hops = 0
        path_explanations = [f"reg 0x{start_reg:x} start at 0x{cur_addr:x}"]
        seen_eax_zero = False
        propagated_to_ABIcall = False

        while hops < max_hops:
            next_addr = self._get_next_ins_addr(cur_addr, fn_addr)
            if next_addr is None:
                break

            next_ins = self.ins_map.get(next_addr)
            if not next_ins:
                break

            next_cs = getattr(next_ins, "cs", None)
            if not next_cs:
                break


            # 检测 EAX 清零（可变参数函数调用约定的线索证据）,其他数是非可变参数函数调用约定
            if next_cs.id in (X86_INS_MOV, X86_INS_XOR):
                ops = next_cs.operands
                if len(ops) == 2 and ops[0].type == CS_OP_REG and self.canon(ops[0].reg) == X86_REG_EAX:
                    if (next_cs.id == X86_INS_MOV and ops[1].type == CS_OP_IMM and ops[1].imm == 0) or \
                    (next_cs.id == X86_INS_XOR and ops[1].type == CS_OP_REG and self.canon(ops[1].reg) == X86_REG_EAX):
                        seen_eax_zero = True
                        path_explanations.append(f"EAX cleared at 0x{next_cs.address:x}")


            # 寄存器被覆盖 → 停止
            for r in next_cs.regs_write:
                if self.canon(r) == start_reg:
                    ev.score -= 10
                    path_explanations.append(f"ABI reg overwritten at 0x{next_cs.address:x}")
                    ev.explanations.append(
                        f"[R21 stop] -10 : " + " => ".join(path_explanations)
                    )
                    return path_explanations, seen_eax_zero, propagated_to_ABIcall

            # 寄存器传递给 ABI 参数寄存器
            if next_cs.id in (X86_INS_MOV, X86_INS_MOVABS):
                ops = next_cs.operands
                if len(ops) == 2 and ops[0].type == CS_OP_REG and ops[1].type == CS_OP_REG:
                    if self.canon(ops[0].reg) == start_reg and self.canon(ops[1].reg) in self.ABI_PARAM_REGS:
                        path_explanations.append(
                            f"reg propagated to ABI param reg 0x{ops[1].reg:x} at 0x{next_cs.address:x}"
                        )
                        ev.score += 2
                        start_reg = self.canon(ops[1].reg)  # 继续追踪

            # 如果是 call 指令 → 强证据
            if next_cs.id == X86_INS_CALL:
                propagated_to_ABIcall = True
                ev.score += 4
                path_explanations.append(f"may used as call argument at 0x{next_cs.address:x}")
                # 可变参数函数调用约定的线索 强证据
                if seen_eax_zero:
                    ev.score += 2
                    path_explanations.append("vararg calling convention detected")

                return path_explanations, seen_eax_zero, propagated_to_ABIcall

            cur_addr = next_addr
            hops += 1

        return path_explanations, seen_eax_zero, propagated_to_ABIcall



    # --------------------------------------------------
    # R21: ABI-aware call argument evidence(立即值直接被存入参数寄存器然后被调用得情况imm → ABI 参数寄存器 → call → 很可能是字符串指针)
    # --------------------------------------------------
    def apply_r21_abi_call_arg(self, imm):
        ev = imm.evidence
        inst_wrapper = getattr(imm.meta, "inst_wrapper", None)
        if inst_wrapper is None:
            return

        cur_cs = inst_wrapper.cs

        # (1)仅考虑 mov imm -> reg
        if cur_cs.id not in (X86_INS_MOV, X86_INS_MOVABS):
            return

        ops = cur_cs.operands
        if len(ops) != 2 or ops[0].type != CS_OP_IMM or ops[1].type != CS_OP_REG:
            return

        imm_val = ops[0].imm
        start_reg = self.canon(ops[1].reg)

        # (2) 必须是 ABI 参数寄存器
        if start_reg not in self.ABI_PARAM_REGS:
            return

        # 调用复用函数
        path_explanations, seen_eax_zero, propagated_to_ABIcall = self._propagated_to_abi_reg(imm, start_reg, cur_cs.address, imm.fact.function_address)
        
        secname = self.container.get_section_by_address(imm_val)
        if secname:
            ev.score += 2
            ev.target_address = imm_val
            path_explanations.append(f"imm located in {secname}")
        

        ev.source = "r21-abi-call-arg"
        ev.explanations.append(
            f"[R21]"
            + (" +4" if propagated_to_ABIcall else "")
            + (" +2" if seen_eax_zero else "")
            + (" +2" if secname else "")
            + ": " + " => ".join(path_explanations)
        )



    # --------------------------------------------------
    # R22: struct array base (立即数被当作一个结构体/对象数组的基址，通过索引计算出元素地址并通过寄存器传播到ABI参数寄存器)
    # --------------------------------------------------
    def apply_r22_struct_array_base(self, imm):
        ev = imm.evidence
        inst_wrapper = getattr(imm.meta, "inst_wrapper", None)
        if not inst_wrapper:
            return

        cs = inst_wrapper.cs

        # 当前必须是 add reg, imm
        if cs.id != X86_INS_ADD:
            return

        ops = cs.operands
        if len(ops) != 2 or ops[0].type != CS_OP_IMM or ops[0].imm != imm.fact.value or ops[1].type != CS_OP_REG:
            return

        base_reg = self.canon(ops[1].reg)
        fn_addr = imm.fact.function_address

        # 向前确认 index*stride 构造
        prev_addr = cs.address
        hops = 0
        seen_scaled_index = False
        while hops < 5:
            prev_addr = self._get_prev_ins_addr(prev_addr, fn_addr)
            if prev_addr is None:
                break

            ins = self.ins_map.get(prev_addr)
            if not ins:
                break
            prev_cs = ins.cs
            prev_ops = prev_cs.operands

            # 如果 base_reg 在这里被某个不一样的寄存器重定义，停止（意味着是数据构造的开始点）
            if prev_cs.id == X86_INS_MOV and len(prev_ops) == 2 and prev_ops[1].type == CS_OP_REG:
                dst = self.canon(prev_ops[1].reg)
                if dst == base_reg and prev_ops[0].type == CS_OP_REG:
                    break

            # index scale 构造特征
            if len(prev_ops) == 2 and prev_ops[1].type == CS_OP_REG and base_reg == self.canon(prev_ops[1].reg):
                if prev_cs.id in (X86_INS_SHL, X86_INS_IMUL, X86_INS_ADD, X86_INS_LEA):
                    seen_scaled_index = True
            hops += 1

        if not seen_scaled_index:
            return

        # 向后确认最终被当作内存 base 或传递到 ABI 寄存器
        cur_addr = cs.address
        hops = 0
        while hops < 6:
            next_addr = self._get_next_ins_addr(cur_addr, fn_addr)
            if next_addr is None:
                return

            ins = self.ins_map.get(next_addr)
            if not ins:
                return

            next_cs = ins.cs
            ops2 = next_cs.operands

            # 从寄存器取出作为内存地址(从第一个操作数还是第二个操作数取是一样得）
            if next_cs.id in (X86_INS_MOV, X86_INS_LEA):
                for op in next_cs.operands:
                    if op.type == CS_OP_MEM:
                        mem = op.mem
                        if self.canon(mem.base) == base_reg:
                            ev.score += 3.5
                            ev.explanations.append(
                                f"[R22] + {ev.score} : immediate forms STRUCT/ARRAY base with scaled index → memory dereference at 0x{next_cs.address:x}"
                            )
                            return

            # 传递给 ABI 参数寄存器(寄存器中得值被传递ABI参数寄存器然后被调用得情况)
            if len(ops2) == 2 and ops2[0].type == CS_OP_REG and ops2[1].type == CS_OP_REG:
                if self.canon(ops2[0].reg) == base_reg and self.canon(ops2[1].reg) in self.ABI_PARAM_REGS:
                    path_explanations, seen_eax_zero, propagated_to_ABIcall  = self._propagated_to_abi_reg(imm, base_reg, next_cs.address, fn_addr)
                    ev.explanations.append(
                        f"[R22]"
                        + (" +4" if propagated_to_ABIcall else "")
                        + (" +2" if seen_eax_zero else "") 
                        + ": " + " => ".join(path_explanations)
                        + ("(immediate forms STRUCT/ARRAY base with scaled index propagated to ABI parameter register for function call)" if propagated_to_ABIcall else "")
                    )
                    return

            cur_addr = next_addr
            hops += 1

    
    # 立即数被直接作为函数返回值(eax)
    def apply_r23_return_pointer_constant(self, imm):
        ev = imm.evidence
        inst_wrapper = getattr(imm.meta, "inst_wrapper", None)
        if not inst_wrapper:
            return

        cs = inst_wrapper.cs
        # Step 1: mov imm → RAX/EAX
        if cs.id not in (X86_INS_MOV, X86_INS_MOVABS):
            return

        ops = cs.operands
        if len(ops) != 2:
            return

        if ops[0].type != CS_OP_IMM or ops[0].imm != imm.fact.value:
            return

        if ops[1].type != CS_OP_REG:
            return

        dst = self.canon(ops[1].reg)
        if dst not in (X86_REG_RAX, X86_REG_EAX):
            return

        # Step 2: forward scan
        cur_addr = cs.address
        fn_addr = imm.fact.function_address
        hops = 0

        while hops < 4:
            next_addr = self._get_next_ins_addr(cur_addr, fn_addr)
            if next_addr is None:
                return

            ins = self.ins_map.get(next_addr)
            if not ins:
                return

            next_cs = ins.cs

            # 2.2 RAX 被破坏 → 失败
            for r in next_cs.regs_write:
                if self.canon(r) in (X86_REG_RAX, X86_REG_EAX):
                    return

            # 2.3 命中 ret → 成功
            if next_cs.id in (X86_INS_RET, X86_INS_RETF, X86_INS_CALL):
                ev.score += 5
                ev.source = "r23-return-pointer-constant"
                ev.target_address = imm.fact.value
                ev.explanations.append(
                    f"[R23] +5 : immediate 0x{imm.fact.value:x} is directly returned via RAX "
                    f"→ function-level pointer semantic"
                )
                return

            cur_addr = next_addr
            hops += 1

    
    # --------------------------------------------------
    # run
    # --------------------------------------------------
    def run(self, imm, mode=None):
        self.apply_r20_forward_vsa(imm)
        self.apply_r21_abi_call_arg(imm)
        self.apply_r22_struct_array_base(imm)
        self.apply_r23_return_pointer_constant(imm)
        return self.immediates
