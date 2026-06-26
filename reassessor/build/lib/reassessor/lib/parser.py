from abc import abstractmethod
from collections import namedtuple
import re
from .types import Label, LblTy, DataType, InstType
import capstone
from capstone.x86 import X86_OP_REG, X86_OP_MEM, X86_OP_IMM, X86_REG_RIP

# 所有x86寄存器列表，用于在解析表达式时过滤掉寄存器引用
REGISTERS = ['RAX', 'RBX', 'RCX', 'RDX', 'RSI', 'RDI', 'RBP', 'RSP', 'R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15',
        'EAX', 'EBX', 'ECX', 'EDX', 'ESI', 'EDI', 'EBP', 'ESP','R8D', 'R9D', 'R10D', 'R11D', 'R12D', 'R13D', 'R14D', 'R15D',
        'AX', 'BX', 'CX', 'DX', 'BP', 'SI', 'DI', 'SP', 'R8W', 'R9W', 'R10W', 'R11W', 'R12W', 'R13W', 'R14W', 'R15W',
        'AH', 'BH', 'CH', 'DH',
        'AL', 'BL', 'CL', 'DL', 'BPL', 'SIL', 'DIL', 'SPL', 'R8B', 'R9B', 'R10B', 'R11B', 'R12B', 'R13B', 'R14B', 'R15B',
        'XMM0', 'XMM1', 'XMM2', 'XMM3', 'XMM4', 'XMM5', 'XMM6', 'XMM7', 'XMM8', 'XMM9', 'XMM10',
        'XMM11', 'XMM12', 'XMM13', 'XMM14', 'XMM15',
        'RIP',
        'CS', 'DS', 'ES', 'FS', 'GS', 'SS',
        'MM0', 'MM1', 'MM2', 'MM3', 'MM4', 'MM5', 'MM6', 'MM7'
]

# 数据定义指令列表（如.quad, .long等）
DATA_DIRECTIVE = ['.byte', '.asciz', '.quad', '.ascii', '.long', '.short', '.string', '.zero']
# 需要跳过的指令（如对齐指令、全局声明等）
SKIP_DIRECTIVE = ['.align', '.globl', '.type']
# 跳转指令列表，用于识别需要符号化的跳转目标
jump_instrs =  ["jo","jno","js","jns","je", "jz","jne", "jnz","jb", "jna", "jc","jnb", "jae", "jnc","jbe", "jna","ja", "jnb","jl", "jng","jge", "jnl","jle", "jng","jg", "jnl","jp", "jpe","jnp", "jpo","jcx", "jec", 'jmp', 'jmpl', 'jmpq']

# 命名元组定义：用于表示不同类型的汇编元素
# 指令
ReasmInst = namedtuple('ReasmInst', ['asm_line', 'opcode', 'operand_list', 'addr', 'idx'])
# 数据定义
ReasmData = namedtuple('ReasmData', ['asm_line', 'directive', 'expr', 'addr', 'idx'])
# 普通标签
ReasmLabel = namedtuple('ReasmLabel', ['label', 'addr', 'idx'])
# .set定义的标签(.set指令用于定义一个符号等于某个表达式)
ReasmSetLabel = namedtuple('ReasmSetLabel', ['label', 'addr', 'num', 'idx'])


def parse_set_directive(line, label_to_addr):
    """
    解析.set指令，如: .set FUN_804a3f0, . - 10
    .set指令用于定义一个符号等于某个表达式(.是当前地址)
    """
    label = line.split(',')[0].split()[1] # 提取标签名
    exprs = line.split(',')[1].split() # 提取表达式部分

    new_exprs = []
    new_labels = []
    for expr in exprs:
        if expr.isdigit() or expr in ['+', '-', '*'] or expr.startswith('0x'):
            new_exprs.append(expr)  # 数字或运算符
        elif expr[0] in ['.'] or expr[0].isalpha():
            new_exprs.append('0')   # 标签占位为0
            new_labels.append(expr) # 记录标签名
        else:
            assert False, 'Unknown expression'

    # 计算表达式中的数值部分
    num = eval(''.join(new_exprs))

    assert len(new_labels) < 2, 'Invalid expression'

    xaddr = -1
    if new_labels:
        if '.' == new_labels[0]:
            # .set FUN_804a3f0, . - 10
            # FUN_804a3f0 = . - 10
            # . = FUN_804a3f0 - (- 10)

            # .set FUN_804a3f0, . - 10 这种情况
            # FUN_804a3f0 = 当前地址 - 10
            # 所以 当前地址 = FUN_804a3f0 + 10
            xaddr = label_to_addr(label) - num
        else:
            xaddr = label_to_addr(new_labels[0])
    # ssx debug
    # print("new_labels:" + str(new_labels))
    # print("new_exprs:" + str(new_exprs))
    # print("xaddr:" + str(xaddr))
    # print("num:" + str(num))
    return xaddr, num



class AsmTokenizer:
    """汇编代码分词器，将汇编行解析为结构化数据"""
    def __init__(self, syntax):
        self.syntax = syntax

    def parse(self, asm_line, addr=0, idx=0):
        """解析指令行"""
        terms = asm_line.split()
        opcode = terms[0]
        
        # 处理特殊指令前缀
        if opcode.startswith('nop'):
            op_str = ''
        elif opcode.startswith('rep'):
            opcode = ' '.join(terms[:2])    # rep前缀与操作码合并
            op_str = ' '.join(terms[2:])
        elif opcode in ['lock', 'bnd']:
            # ddisasm反汇编错误处理
            #ddisasm disassembl error
            opcode = ' '.join(terms[:2])
            op_str = ' '.join(terms[2:])
        else:
            op_str = ' '.join(terms[1:])

        # 根据语法风格解析操作数
        if self.syntax == capstone.CS_OPT_SYNTAX_ATT:
            operand_list = self._parse_att_operands(op_str)
        else:
            operand_list = self._parse_intel_operands(op_str)

        return ReasmInst(asm_line, opcode, operand_list, addr, idx)

    def parse_data(self, asm_line, addr=0, idx=0):
        """解析数据定义行"""
        terms = asm_line.split()
        directive = terms[0]    # 如.quad, .long等
        expr = terms[1]         # 表达式部分
        return ReasmData(asm_line, directive, expr, addr, idx)

    def _parse_intel_operands(self, op_str):
        """Intel语法操作数解析：逗号分隔"""
        if op_str.strip():
            return op_str.split(',')
        return []

    def _parse_att_operands(self, op_str):
        """AT&T语法操作数解析：处理括号和逗号"""
        token = ''
        lpar = False    # 是否在括号内
        operand_list = []
        for char in op_str:
            if lpar:
                token += char
                if char == ')':
                    lpar = False
                continue
            if char == ',':
                operand_list.append(token)
                token = ''
                continue
            if char == ' ':
                continue

            token += char
            if char == '(':
                lpar = True
        if token:
            operand_list.append(token)

        return operand_list



def parse_intel_asm_line(line):
    prev = line.split(',')[0]
    args = line.split(',')[1:]

    if line in ['nop']:
        opcode = 'nop'
        arg1 = ''
        return ['nop', []]
    elif prev.split()[0] in ['rep', 'repe', 'repz', 'repne', 'repnz']:
        opcode = ' '.join(prev.split()[:2])
        arg1 = ' '.join(prev.split()[2:])
    elif prev.split()[0] in ['lock']:
        #ddisasm disassembl error
        opcode = ' '.join(prev.split()[:2])
        arg1 = ' '.join(prev.split()[2:])
    else:
        opcode = prev.split()[0]
        arg1 = ' '.join(prev.split()[1:])

    ret = [opcode,[]]
    if arg1:
        ret[1].append(arg1)
        for arg in args:
            ret[1].append(arg)
    return ret


def parse_att_asm_line(line):
    if line.lower().startswith("nop"):
        return []

    prev = line.split(',')[0]
    opcode_len = 1
    if prev.split()[0].lower().startswith('rep'):
        opcode_len = 2
    opcode = ' '.join(prev.split()[:opcode_len])
    arg_str = ' '.join(line.split()[opcode_len:])
    ret = [opcode, []]

    token = ''
    lpar = False
    for char in arg_str:
        if lpar:
            token += char
            if char == ')':
                lpar = False
            continue
        if char == ',':
            ret[1].append(token)
            token = ''
            continue
        if char == ' ':
            continue

        token += char
        if char == '(':
            lpar = True
    if token:
        ret[1].append(token)

    return ret


class Factor:
    """表达式因子，表示表达式中的一个组成部分（标签或数字）"""
    def __init__(self, op, data):
        self.op = op
        self.data = data

    def get_str(self):
        """获取因子字符串表示"""
        if self.op == '+':
            return self.data
        elif self.op == '-':
            return self.op + self.data

        raise SyntaxError('Unexpected operator')

class CompGen:
    """
    符号生成器：核心类，负责从汇编中提取符号信息
    主要功能：
    1. 解析指令和数据定义中的表达式
    2. 识别标签引用
    3. 处理GOT/PLT等特殊符号
    """
    def __init__(self, label_dict = None, syntax = capstone.CS_OPT_SYNTAX_ATT, got_addr = 0, label_func=None, set_label_dict = None):
        self.label_dict = dict()
        if label_dict:
            self.label_dict = label_dict    # 标签名到地址的映射

        self.set_label_dict = dict()
        if set_label_dict:
            self.set_label_dict = set_label_dict    # .set定义的标签

        self.label_func = label_func     # 外部标签解析函数

        self.syntax = syntax     # 外部标签解析函数
        # 根据语法选择表达式解析器
        if syntax == capstone.CS_OPT_SYNTAX_INTEL:
            self.ex_parser = IntelExParser()
        else:
            self.ex_parser = ATTExParser()

        self.got_addr = got_addr    # GOT基地址

    def get_data(self, addr, asm_path, line, idx , value=0, additional_dict=None, r_type=None):
        """
        处理数据定义指令，提取符号信息
        例如: .quad function_name+0x10
        """
        expr = ''.join(line.split()[1:])
        tokens = self.ex_parser.parse(expr)

        # 处理GOTOFF引用
        if len(tokens) == 1 and expr.endswith('@GOTOFF'):
            value = (value + self.got_addr) & 0xffffffff

        if additional_dict:
            factors = FactorList(tokens, value, additional_dict)
        else:
            factors = FactorList(tokens, value, self.label_dict, self.label_func, set_label_dict = self.set_label_dict)
        # 创建数据类型对象，包含符号化信息
        return DataType(addr, asm_path, line, idx, factors, r_type = r_type)
        #return Component(factors)

    def rearrange_operands(self, addr, asm_path, asm_token, insn):
        #op_str_list = []
        """
        使用Capstone的IR重新排列操作数，处理更复杂的符号引用
        主要处理跳转/调用指令和内存/立即数操作数中的符号
        """
        # 处理跳转和调用指令
        if insn.group(capstone.CS_GRP_JUMP) or insn.group(capstone.CS_GRP_CALL):
            op_str = asm_token.operand_list[0]
            tokens = self.ex_parser.parse(op_str)
            # 计算目标地址值
            if insn.operands[0].type == X86_OP_MEM:
                if insn.operands[0].mem.base == X86_REG_RIP:
                    # RIP相对寻址：disp + RIP + 指令长度
                    value = insn.operands[0].mem.disp + insn.address + insn.size
                elif '@GOTOFF' in op_str:
                    value = insn.operands[0].mem.disp
                    value = (value + self.got_addr) & 0xffffffff
                else:
                    value = insn.operands[0].mem.disp
            else:
                # 立即数
                value = insn.operands[0].imm
            # 创建符号列表
            factors = FactorList(tokens, value, is_pcrel=True, set_label_dict = self.set_label_dict)
            if factors.has_label():
                # 如果有标签，创建带立即数符号的指令类型
                return InstType(addr, asm_path, asm_token, imm = factors)
            return InstType(addr, asm_path, asm_token)

        # get the value of relocatable expression
        # 获取可重定位表达式的值
        disp_list = []  # 位移值列表
        imm_list = []   # 立即数值列表
        for operand in insn.operands:
            if operand.type == X86_OP_MEM:
                if operand.mem.base == X86_REG_RIP:
                    value = operand.mem.disp + insn.address + insn.size
                else:
                    value = operand.mem.disp
                disp_list.append(value)
            elif operand.type == X86_OP_IMM:
                imm_list.append(operand.imm)

        # 如果没有可重定位的值，返回基本指令
        if len(disp_list)+len(imm_list) == 0: # or asm_token.opcode.startswith('rep'):
            return InstType(addr, asm_path, asm_token)


        #match reloc expressions to values
        # 将重定位表达式与值匹配
        disp = None
        imm = None
        for op_str in asm_token.operand_list:
            tokens = self.ex_parser.parse(op_str)
            factors = FactorList(tokens)
            if factors.has_label():
                if self.ex_parser.is_imm:
                    # 立即数操作数
                    assert len(imm_list) == 1 and imm is None, 'Unexpected operand type'
                    imm = self.create_component(addr, op_str, imm_list[0])
                else:
                    # 内存操作数
                    if len(disp_list) == 0 and len(imm_list) == 1:
                        # assembler might change RIP-relativea addressing to absolute addressing
                        # movq ext_ncd_write_field_@GOTPCREL(%rip), %rdi
                        #  ->  mov    $0x8c4340,%rdi
                        # 处理汇编器优化：RIP相对寻址 -> 绝对寻址
                        if '(%rip)' in op_str:
                            assert len(imm_list) == 1 and imm is None, 'Unexpected operand type'
                            imm = self.create_component(addr, op_str.split('(%rip)')[0], imm_list[0])
                            continue
                        elif '@GOT(' in op_str:
                            assert len(imm_list) == 1 and imm is None, 'Unexpected operand type'
                            imm = self.create_component(addr, op_str.split('(')[0], imm_list[0])
                            continue

                    assert len(disp_list) == 1 and disp is None, 'Unexpected operand type'


                    disp = self.create_component(addr, op_str, disp_list[0])

        return InstType(addr, asm_path, asm_token, disp=disp, imm=imm)

    def create_component(self, addr, op_str, value = 0):
        """
        创建符号化组件，将操作数字符串转换为符号列表
        """
        tokens = self.ex_parser.parse(op_str)
        is_pcrel = self.ex_parser.has_rip

        if value:   #in case of GT # 有具体值的情况（如来自二进制分析）
            if '@GOTOFF' in op_str:
                value = (value + self.got_addr) & 0xffffffff
            elif '@GOT' in op_str and '@GOTPCREL' not in op_str:
                value = (value + self.got_addr) & 0xffffffff
            elif '_GLOBAL_OFFSET_TABLE_' in op_str:
                value = self.got_addr

            factors = FactorList(tokens, value, is_pcrel = is_pcrel)
        else:       #in case of TOOLs # 无具体值的情况（如来自工具分析）
            factors = FactorList(tokens, label_dict = self.label_dict, is_pcrel = is_pcrel, label_func = self.label_func, set_label_dict= self.set_label_dict)

        if factors.has_label():
            # 处理_GLOBAL_OFFSET_TABLE_特殊情况
            if len(factors.terms) == 3 and factors.terms[0].get_name() == '_GLOBAL_OFFSET_TABLE_':
                factors.terms[0].Address = self.got_addr
                factors.terms[1].Address = addr
                factors.terms[2].Address = self.got_addr - value
            return factors

        return None


    def get_instr(self, addr, asm_path, asm_token, insn=None):
        """
        获取指令的符号化表示
        """
        if asm_token.opcode.startswith('nop'):
            return InstType(addr, asm_path, asm_token)

        # GT uses capstone IR
        # 使用Capstone IR（如果有的话）
        if insn:
            return self.rearrange_operands(addr, asm_path, asm_token, insn)

        # 处理调用和跳转指令
        if asm_token.opcode.startswith('call') or asm_token.opcode in jump_instrs:
            op_str = asm_token.operand_list[0]
            tokens = self.ex_parser.parse(op_str)
            factors = FactorList(tokens, label_dict = self.label_dict, is_pcrel=True, label_func = self.label_func, set_label_dict= self.set_label_dict)
            if factors.has_label():
                return InstType(addr, asm_path, asm_token, imm = factors)
            return InstType(addr, asm_path, asm_token)

        # 处理其他指令中的符号引用
        imm = None
        disp = None
        for op_str in asm_token.operand_list:
            tokens = self.ex_parser.parse(op_str)
            is_pcrel = self.ex_parser.has_rip
            factors = FactorList(tokens, label_dict = self.label_dict, is_pcrel = is_pcrel, label_func = self.label_func, set_label_dict = self.set_label_dict)
            if factors.has_label():
                if self.ex_parser.is_imm:
                    imm = self.create_component(addr, op_str)
                else:
                    disp = self.create_component(addr, op_str)

        return InstType(addr, asm_path, asm_token, disp=disp, imm=imm)


class FactorList:
    """
    符号列表类：核心符号化处理类
    负责：
    1. 将表达式分解为标签和数字部分
    2. 为每个标签查找地址
    3. 对符号进行分类
    4. 输出到all_symbols.txt(存储了所有计算过符号类型的符号。注意，这些符号并非ground truth（基准事实），而是包含了在分析retrowrite、ddisasm或ramblr反汇编产生的汇编文件时所计算出的所有符号)
    """
    def __init__(self, factors, value=0, label_dict=None, label_func=None, is_pcrel=False, set_label_dict=None):
        self.labels = []    # 存储标签名列表
        self.num = 0        # 数值部分（偏移量）
        self.value = value  # 实际值（如果有）
        self._label_dict = label_dict   # 标签名->地址映射
        self._set_label_dict = set_label_dict   # .set标签映射
        self._label_func = label_func   # 外部标签解析函数
        #self.gotoff = gotoff
        self.is_pcrel = is_pcrel    # 是否RIP相对寻址

        # 将因子分解为标签和数字部分
        for factor in factors:
            if factor.data.isdigit() or factor.data.startswith('0x'):
                # 数字部分：累加到self.num
                self.num += eval(factor.get_str())
            else:
                # 标签部分：添加到self.labels
                self.labels.append(factor.get_str())
        
        # 根据标签数量选择不同的处理方式
        if len(self.labels) == 2:
            # exclude ddisasm bugs
            # 排除ddisasm的错误格式
            if self.labels[-1] in ['-_GLOBAL_OFFSET_TABLE_']:#, '-.L_0']:
                self.terms = self.get_ddisasm_got_terms()
            else:
                self.terms = self.get_table_terms() # 处理标签-标签格式
        elif self.has_label():
            self.terms = self.get_terms()   # 获取标签项
        else:
            self.terms = []
        # 清理临时数据
        self._label_dict = None
        self._set_label_dict = None
        self._label_func = None
        # 获取符号类型（这是关键！决定如何写入all_symbols.txt）
        self.type = self.get_type()
        
        # ssx debug
        # 这部分代码负责将符号信息写入all_symbols.txt文件
        if len(self.labels) == 2:
            symbol = {'label1': '','label2':'', 'addr1': 0, 'addr2': 0, 'type': 0}
            symbol['label1'] = self.labels[0]
            symbol['addr1'] = self.terms[0].Address
            symbol['label2'] = self.labels[1]
            symbol['addr2'] = self.terms[1].Address
            symbol['type'] = self.type
            with open("./new_ssx/output/normal_symbolization_result/all_symbols.txt", "a") as file:
                file.write("%s\n" % str(symbol))

        elif len(self.labels) == 1 and self.labels[0]:
            symbol = {'label': '', 'addr': 0, 'type': 0}
            symbol['label'] = self.labels[0]
            symbol['addr'] = self.terms[0].Address
            '''
             type = 1: Absolute + Atomic
             type = 2: Absolute + Composite
             type = 3: PCRelative + Atomic
             type = 4: PCRelative + Composite
             type = 5: GOTRelative + Atomic
             type = 6: GOTRelative + Composite
             type = 7: LabelRelative + Composite
             type = 8: other
            '''
            symbol['type'] = self.type
            with open("./new_ssx/output/normal_symbolization_result/all_symbols.txt", "a") as file:
                file.write("%s\n" % str(symbol))
                

    def get_type(self):
        """
        确定符号类型，这是决定如何写入all_symbols.txt的关键
        类型决定了符号的寻址方式和复杂性
        """
        # ssx debug
        # if len(self.labels) == 2 and self.labels[0] == '.LC1171':
        #     print("self.labels:" + str(self.labels))
        #     print("self.type:" + str(self.label_to_addr()))
        #     print("self.is_pcrel:" + str(self.is_pcrel))
        #     print("self.num:" + str(self.num))
        #     if len(self.terms) > 0:
        #         print("self.terms[0].Name:" + str(self.terms[0].Name))
        #         print("self.terms[0].Address:" + str(self.terms[0].Address))
        #         print("self.terms[0].Num:" + str(self.terms[0].Num))
        #         print("self.terms[0].Ty:" + str(self.terms[0].Ty))
        #     print("self.value:" + str(self.value))
        #     print("self._label_dict:" + str(self._label_dict))
        #     print("self._label_func:" + str(self._label_func))
        #     print("self._set_label_dict:" + str(self._set_label_dict))

        if len(self.labels) == 2:
            #ddisasm makes type 5/6 symbol like XXX-_GLOBAL_OFFSET_TABLE_
            # 两个标签的情况，如：FUNC_40b230-.L_0 或 XXX-_GLOBAL_OFFSET_TABLE_
            if self.labels[1] == '-_GLOBAL_OFFSET_TABLE_':

                #if self.terms[0].Address == -1:
                #    return 0
                # ddisasm生成的GOT相对符号
                if self.is_composite():
                    return 6    # GOTRelative + Composite
                else:
                    return 5    # GOTRelative + Atomic
            # .quad FUN_40b230-.L_0
            elif self.terms[1].Address == -1 and self.terms[1].Num == 0:
                return 1    # Absolute + Atomic
            else:
                return 7    # LabelRelative + Composite
        elif len(self.labels) == 1:

            #if self.terms[0].Address == -1:
            #    return 0
            # 单个标签的情况
            if ('@GOTOFF' in self.labels[0] or '@GOT' in self.labels[0]) and '@GOTPCREL' not in self.labels[0]:
                # GOT相关符号
                if self.is_composite():
                    return 6    # GOTRelative + Composite
                else:
                    return 5    # GOTRelative + Atomic
            elif self.is_pcrel:
                # RIP相对寻址
                if self.is_composite():
                    return 4    # PCRelative + Composite
                else:
                    return 3    # PCRelative + Atomic
            else:
                # 绝对寻址
                if self.is_composite():
                    return 2    # Absolute + Composite
                else:
                    return 1    # Absolute + Atomic
        elif len(self.labels) == 3 and '_GLOBAL_OFFSET_TABLE_' in self.labels[0]:
            return 7    # LabelRelative + Composite
        return 8    # 其他类型

    def has_label(self):
        """检查是否有标签"""
        return len(self.labels) > 0

    def is_composite(self):
        """
        检查是否为复合符号（带偏移量）
        复合符号 = 有标签 AND (有多个项 OR 有数值偏移 OR 标签本身有隐式偏移)
        """
        return self.has_label() and (len(self.terms) > 1 or self.num != 0 or (self.terms[0].Num != 0 and self.terms[0].Address != -1))

    def get_norm_str(self):
        ret = ''
        for term in self.terms:
            if isinstance(term, Label):
                if ret:
                    if term.get_name()[0] == '-':
                        ret += '-' + str(term)
                    else:
                        ret += '+' + str(term)
                else:
                    ret = str(term)
            elif term < 0:
                ret += '-%s'%(hex(-term))
            else:
                ret += '+%s'%(hex(term))
        return ret


    def get_str(self):
        ret = ''
        for label in self.labels:
            if ret and label[0] != '-':
                ret += '+'
            ret += label
        if self.num > 0:
            ret += '+%s'%(hex(self.num))
        elif self.num < 0:
            ret += '%s'%(hex(self.num))

        return ret

    def label_to_addr(self, label):
        """
        将标签名转换为地址
        这是符号化的核心：通过标签名查找对应的内存地址
        """
        if self._label_dict is None:
            return 0

        keyword = label.split('@')[0]   # 去除@GOT等后缀
        if keyword in self._label_dict:
            res = self._label_dict[keyword]
            if isinstance(res, list):
                if len(self._label_dict[keyword]) == 1:
                    return self._label_dict[keyword][0]
                else:
                    #if there is duplicated label, we nullify the label
                    # 如果有重复标签，将地址设为-2表示无效
                    return -2
            return self._label_dict[keyword]
        elif self._label_func:
            addr = self._label_func(keyword)
            if addr > 0:
                return addr

        return -1   # 未找到标签


    def is_set_label(self, keyword):
        if not self._set_label_dict:
            return False
        if keyword in self._set_label_dict:
            return True
        return False



    def get_ddisasm_got_terms(self):
        assert len(self.labels) == 2 and self.labels[1] == '-_GLOBAL_OFFSET_TABLE_'

        result = []

        addr = self.label_to_addr(self.labels[0])
        label_type = LblTy.GOTOFF
        lbl = Label(self.labels[0], label_type, addr, 0)
        result.append(lbl)

        if self.num:
            return result + [self.num]
        return result

    def get_terms(self):
        """
        获取符号项列表，为每个标签创建Label对象
        这是生成最终符号化表示的关键步骤
        """
        result = []

        for label in self.labels:
            keyword = ''
            implicit_num = 0

            if '_GLOBAL_OFFSET_TABLE_' in label:
                #addr = self.gotoff
                addr = 0    # GOT基地址
                label_type = LblTy.LABEL
            #elif '@GOTOFF' in label:
            elif '@GOT' in label:
                #keyword = label.split('@GOTOFF')[0]
                keyword = label.split('@GOT')[0]    # 提取基本标签名
                label_type = LblTy.GOTOFF   # GOT偏移类型
            else:
                if label[0] == '-':
                    keyword = label[1:] # 负标签
                else:
                    keyword = label
                label_type = LblTy.LABEL

            if keyword:
                # 查找标签地址
                addr = self.label_to_addr(keyword)

                #check whether the label is defined by .set directive
                # 检查是否为.set定义的标签
                if addr in [0,-1] and self.is_set_label(keyword):
                    addr, implicit_num = self._set_label_dict[keyword][0]

            # 如果没有找到地址但有值，则通过计算得到
            if addr <= 0 and self.value:
                if len(self.labels) == 3 and '_GLOBAL_OFFSET_TABLE_' in self.labels[0]:
                    pass    # 特殊情况
                # handle ddisasm bugs
                elif len(self.labels) == 2 and self.labels[-1] == '-_GLOBAL_OFFSET_TABLE_':
                    pass    # ddisasm bug处理
                elif len(self.labels) > 1:
                    raise SyntaxError('Unsolved label')
                addr = self.value - self.num    # 计算地址：值 - 偏移
            elif '@PLT' in label or '@GOTPCREL' in label:
                addr = 0    # PLT/GOTPCREL符号地址为0

            # 创建Label对象
            lbl = Label(label, label_type, addr, implicit_num)
            result.append(lbl)
        # 如果有数值偏移，添加到结果中
        if self.num:
            return result + [self.num]
        return result

    def get_table_terms(self):
        base_label = self.labels[1][1:]
        base_addr = self.label_to_addr(base_label)
        if self.value != 0 and base_addr <= 0:
            assert base_addr > 0, 'This is incorrect jump table base'

        if self.value == 0:
            addr1 = self.label_to_addr(self.labels[0])
        else:
            addr1 = (self.value + base_addr ) & 0xffffffff

        lbl1 = Label(self.labels[0], LblTy.LABEL, addr1, 0)
        lbl2 = Label(self.labels[1], LblTy.LABEL, base_addr, 0)

        return [lbl1, lbl2]

# 表达式解析器基类
class ExParser:
    """表达式解析器基类，负责解析汇编表达式"""
    def __init__(self):
        self.line = ''  # 待解析的表达式
        self.current = ''   # 当前解析的token

    def parse(self, expr):
        """解析表达式入口"""
        self.has_rip = False    # 是否包含RIP相对寻址
        self.is_imm = False     # 是否立即数
        self.line = self._strip(expr)   # 预处理表达式
        result =  self._exp()   # 解析表达式
        if self.line != '':
            raise SyntaxError('Unexpected character after expression: ' + self.line)
        return result

    def _is_next(self, regexp):
        """检查下一个token是否匹配正则表达式"""
        m = re.match(r'\s*' + regexp + r'\s*', self.line)
        if m:
            self.current = m.group().strip()
            self.line = self.line[m.end():]
            return True
        return False

    @abstractmethod
    def _strip(self):
        """预处理表达式，移除不需要的部分"""
        pass

    @abstractmethod
    def _exp(self):
        """解析表达式"""
        pass

    @abstractmethod
    def _term(self):
        """解析项"""
        pass

    @abstractmethod
    def _factor(self):
        """解析因子"""
        pass

class ATTExParser(ExParser):
    """AT&T语法表达式解析器"""
    def _strip(self, expr):
        """AT&T语法表达式预处理"""
        #remove offset & pointer directive
        if expr.startswith('$'):    # $表示立即数
            self.is_imm = True
            expr = expr[1:]
        elif expr.startswith('*'):
            expr = expr[1:] # *表示间接寻址

        # 处理各种特殊情况
        if re.search ('%fs:.*', expr):
            return ''   # 段寄存器，忽略
        elif re.search ('%es:.*', expr):
            return ''   # 寄存器，忽略
        elif expr[0] == '%':
            return ''
        elif ':$' in expr:
            # 处理ramblr反汇编错误
            #handle ramblr diassem errors.
            # ljmpl $0x32dc:$0x3d80ffff
            return ''
        elif expr.startswith('_GLOBAL_OFFSET_TABLE_+'):
            # clang x86 PIE特殊情况
            # clang x86 pie
            # $_GLOBAL_OFFSET_TABLE_+(.Ltmp266-.L15$pb)
            expr = '%s+%s-%s'%(re.findall('^(.*)\+\((.*)-(.*)\)$', expr)[0])
        
        # 处理各种括号嵌套情况
        elif re.search('.*\(.*\)', expr):
            # 处理括号表达式
            if '%rip' in re.findall('.*\((.*)\)', expr)[0]:
                self.has_rip = True # 标记为RIP相对

            # ramblr: movzbl  (label_4744+7)(%rdx),  %esi
            if re.search('^\(.*\)\(.*\)$', expr):
                expr = re.findall('^\((.*)\)\(.*\)$', expr)[0]
            # ramblr: movl $(label_4299+3), -316(%ebp)
            # ramblr: movw $0x808, (label_1293+2)
            elif ('%' not in expr) and re.search('^\(.*\)$', expr):
                expr = re.findall('\((.*)\)', expr)[0]
            else:
                expr = re.findall('(.*)\(.*\)', expr)[0]

            #if re.search('\(.*\)', expr):
            #    expr = re.findall('\((.*)\)', expr)[0]
        return expr

    def _exp(self):
        """解析AT&T表达式"""
        result = []
        factor = self._factor()
        if factor.data:
            result.append(factor)

        # 解析加减运算符
        while self._is_next(r'[-+]'):
            op = self.current
            factor = self._factor()
            if factor.data:
                result.append(Factor(op, factor.data))

        return result

    def _term(self):
        pass    # AT&T语法不需要项解析

    def _factor(self):
        """解析AT&T因子"""
        if self._is_next(r'-'):
            # 负因子
            factor = self._factor()
            if factor.op == '+':
                return Factor('-', factor.data)
        #elif self._is_next(r'[_.a-zA-Z0-9@]*'):
        # for cgc clang 6.4
        elif self._is_next(r'[_.a-zA-Z0-9@$]*'):
            # 标签或数字
            if self.line == '$pb':
                self.current += self.line
                self.line = ''
            return Factor('+', self.current)


        raise SyntaxError('Unexpect syntax' + self.line)


class IntelExParser(ExParser):
    """Intel语法表达式解析器"""
    def _strip(self, expr):
        """Intel语法表达式预处理"""
        if re.search('.* PTR \[.*\]', expr):
            expr = re.findall('.* PTR \[(.*)\]', expr)[0]
        elif re.search ('.* PTR .S:.*', expr):
            return ''
        elif re.match ('ST\(.*\)', expr):
            return ''
        elif re.search('^\[.*\]$', expr):
            expr = re.findall('^\[(.*)\]$', expr)[0]

        # add BYTE PTR [OFFSET _GLOBAL_OFFSET_TABLE_]
        # 处理OFFSET关键字
        if re.search('OFFSET .*', expr):
            expr = re.findall('OFFSET (.*)', expr)[0]
            if expr.startswith('_GLOBAL_OFFSET_TABLE_+'):
                # clang x86 pie
                # $_GLOBAL_OFFSET_TABLE_+(.Ltmp266-.L15$pb)
                # clang x86 PIE特殊情况
                expr = '%s+%s-%s'%(re.findall('^(.*)\+\((.*)-(.*)\)$', expr)[0])

            self.is_imm = True
        # give exception to handle ddisasm error
        # 处理ddisasm错误
        elif re.search('\(.*-\.L\_0\)/2', expr) or re.search('\(.*-_GLOBAL_OFFSET_TABLE_\)/2',expr):
            expr = '%s-%s'%(re.findall('\((.*)-(.*)\)/2', expr)[0])

        return expr

    def _exp(self):
        """解析Intel表达式"""
        result = []
        factor = self._term()
        if factor.data:
            result.append(factor)

        # 解析加减运算符
        while self._is_next(r'[-+]'):
            op = self.current
            factor = self._term()
            if factor.data:
                result.append(Factor(op, factor.data))

        # 处理GOTOFF特殊情况
        if result and re.search('^[0-9]*@GOTOFF', result[-1].data):
            # [EBX+_ZN4Data5SetUpINS_12Exercise_2_3ILi3EEELi3EE15right_hand_sideE+12@GOTOFF]
            for factor in result[:-1]:
                if factor.data and not factor.data.isdigit():
                    factor.data += '@GOTOFF'
            result[-1].data = result[-1].data.split('@')[0]

        return result

    def _term(self):
        """解析Intel项（支持乘法）"""
        fact1 = self._factor()
        fact2 = None
        while self._is_next('[*]'):
            fact2 = self._factor()

        if fact2 is None:
            return fact1
        else: # ignore multiply
            # 忽略乘法
            return Factor(None, None)

    def _factor(self):
        """解析Intel因子"""
        if self._is_next(r'[_.a-zA-Z0-9@]*'):
            if self.current in ['RIP']:
                self.has_rip = True # 标记RIP相对
            if self.current in REGISTERS: # ignore register # 忽略寄存器
                return Factor(None, None)

            return Factor('+', self.current)

        elif self._is_next(r'-'):
            # 负因子
            factor = self._factor()
            if factor.op == '+':
                return Factor('-', factor.data)

        raise SyntaxError('Unexpect syntax' + self.line)


