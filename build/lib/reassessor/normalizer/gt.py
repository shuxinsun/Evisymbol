import re
import struct
import capstone
import sys
import os
import pickle
import glob, json
from elftools.elf.elffile import ELFFile
from elftools.elf.descriptions import describe_reloc_type
from elftools.elf.relocation import RelocationSection
from collections import defaultdict

from reassessor.lib.types import Program, InstType, LblTy, Label
from reassessor.lib.parser import CompGen
from reassessor.lib.asmfile import AsmFileInfo, LocInfo, AsmInst

class JumpTable:
    def __init__(self, entries):
        self.entries = entries
        self.lengh = len(entries)
        self.base = 0

    def set_base(self, base):
        self.base = base

    def get_entries(self):
        pass

class CompData:
    def __init__(self, entries):
        self.entries = entries
        self.lengh = len(entries)
        self.base = 0

    def set_base(self, base):
        self.base = base

    def get_entries(self):
        pass

class FuncInst:
    def __init__(self, inst_list, func_info, asm_path):
        self.inst_list = inst_list
        self.name, self.addr, self.size = func_info
        self.asm_path = asm_path
        self.jmp_table_list = []

    def register_jmp_table(self, inst_addr, label, tbl_addr, tbl_size):
        self.jmp_table_list.append({'inst_addr':inst_addr, 'label':label, 'addr':tbl_addr, 'size':tbl_size})

def get_dwarf_loc(filename):
    dwarf_loc_map = {}

    def process_file(filename):
        with open(filename, 'rb') as f:
            elffile = ELFFile(f)

            if not elffile.has_dwarf_info():
                print('  file has no DWARF info')
                return

            dwarfinfo = elffile.get_dwarf_info()
            for CU in dwarfinfo.iter_CUs():
                line_program = dwarfinfo.line_program_for_CU(CU)
                if line_program is None:
                    continue
                line_entry_mapping(line_program)

    def line_entry_mapping(line_program):
        lp_entries = line_program.get_entries()
        for lpe in lp_entries:
            if not lpe.state or lpe.state.file == 0:
                continue

            filename = lpe_filename(line_program, lpe.state.file)
            if lpe.state.address not in dwarf_loc_map.keys():
                dwarf_loc_map[lpe.state.address] = set()
            dwarf_loc_map[lpe.state.address].add('%s:%d'%(filename, lpe.state.line))

    def lpe_filename(line_program, file_index):
        lp_header = line_program.header
        file_entries = lp_header["file_entry"]

        file_entry = file_entries[file_index - 1]
        dir_index = file_entry["dir_index"]

        if dir_index == 0:
            return file_entry.name.decode()

        directory = lp_header["include_directory"][dir_index - 1]
        return os.path.join(directory, file_entry.name).decode()

    process_file(filename)
    return dwarf_loc_map




def disasm(prog, cs, addr, length):
    offset = addr - prog.text_base
    insts = []
    for inst in prog.disasm_range(cs, addr, length):
        #if not is_semantically_nop(inst):
        insts.append(inst)
    return insts

def get_reloc_bytesize(rinfo_type):
    if 'X86_64_' in rinfo_type and '32' not in rinfo_type:
        return 8
    else:
        return 4

def get_reloc_gotoff(rinfo_type):
    if 'GOTOFF' in rinfo_type:
        return True
    else:
        return False

# 获取所有重定位表
def get_reloc(elf):
    relocs = {}

    for section in elf.iter_sections():
        if not isinstance(section, RelocationSection):
            continue
        if ( section.name.startswith(".rel") and \
             ( ("data" in section.name) or \
               section.name.endswith(".dyn") or \
               section.name.endswith('.init_array') or \
               section.name.endswith('.fini_array') ) ) or \
               section.name in ['.rela.plt'] or \
               section.name in ['.rel.plt']:

            for relocation in section.iter_relocations():
                addr = relocation['r_offset']
                t = describe_reloc_type(relocation['r_info_type'], elf)
                sz = get_reloc_bytesize(t)
                is_got = get_reloc_gotoff(t)
                relocs[addr] = (sz, is_got, t)

    return relocs

def get_reloc_symbs(elf, sec_name = '.symtab'):
    names = {}
    dynsym = elf.get_section_by_name(sec_name)#('.dynsym')
    for symb in dynsym.iter_symbols():
        if symb['st_shndx'] != 'SHN_UNDEF':
            addr = symb['st_value']
            name = symb.name
            size = symb['st_size']
            if addr != 0 and len(name) > 0:
                if name in names:
                    names[name].append((addr, size))
                else:
                    names[name] = [(addr, size)]
    return names

class NormalizeGT:
    """
    Ground Truth（原始二进制）符号化处理类
    
    主要功能：
    1. 解析原始二进制文件（ELF格式），提取所有符号信息
    2. 作为基准（Ground Truth），用于评估其他反汇编工具的准确性
    3. 提取代码段、数据段、重定位信息、符号表等关键信息
    """
    def __init__(self, bin_path, asm_dir, reloc_file='', build_path=''):
        """
        初始化GT符号化处理器
        对ELF文件进行分析和反汇编
        获取二进制文件基本信息存储到Program类的实例中
        match_src_to_bin
        
        Args:
            bin_path (str): 原始二进制文件路径（通常是可执行文件）
            asm_dir (str): 汇编文件目录，可能包含反汇编结果
            reloc_file (str): 重定位文件路径（可选，用于解析重定位信息）
            build_path (str): 构建路径（可选，用于查找调试信息和源代码）
        """
        # 1. 保存输入参数
        self.bin_path = bin_path
        self.asm_dir = asm_dir
        self.build_path = build_path
        self.reloc_file = reloc_file
        #self.ex_parser = ATTExParser()

        # 2. 收集位置候选（用于后续地址匹配）
        # 可能从调试信息或符号表中提取函数、变量位置
        self.collect_loc_candidates()
        f = open(self.bin_path, 'rb')   # 3. 以二进制模式打开ELF文件

        # 4. 使用pyelftools解析ELF文件
        self.elf = ELFFile(f)   # ELF文件对象，包含所有节区和段信息
        
        # 5. 获取GOT（全局偏移表）地址
        # GOT用于PIC（位置无关代码），存放全局变量和函数的绝对地址
        if self.elf.get_section_by_name('.got.plt'):
            # 优先使用.got.plt（包含PLT相关的GOT条目）
            self.got_addr = self.elf.get_section_by_name('.got.plt')['sh_addr']
        else:
            # 否则使用普通的.got节区
            self.got_addr = self.elf.get_section_by_name('.got')['sh_addr']

         # 6. 获取重定位信息
         # 重定位信息指示哪些位置需要在加载时修改
        if reloc_file:
            # 如果有单独的重定位文件，从中提取重定位信息
            with open(reloc_file, 'rb') as fp:
                reloc_elf = ELFFile(fp)
                self.relocs = get_reloc(reloc_elf)  # 提取重定位条目
        else:
            # 否则从主ELF文件中提取
            self.relocs = get_reloc(self.elf)
        # 7. 获取符号表信息
        # 符号表包含所有函数、变量的名称和地址
        self.symbs = get_reloc_symbs(self.elf)  # 获取与重定位相关的符号

        # 8. 提取.text节区信息（代码段）
        self.text = self.elf.get_section_by_name(".text")   # 获取代码段节区
        self.text_base = self.text.header["sh_addr"]    # 代码段的加载地址

        # 9. 初始化Capstone反汇编引擎
        # 根据ELF的机器架构选择适当的模式
        if self.elf['e_machine'] in  ('EM_X86_64'):
            # x86-64架构：64位模式
            self.cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
        else:
            # x86-32架构：32位模式
            self.cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

        # 10. 配置Capstone反汇编器
        self.cs.detail = True   # 启用详细信息（操作数、寄存器等）
        self.cs.syntax = capstone.CS_OPT_SYNTAX_ATT # 使用AT&T语法
        # 11. 反汇编整个代码段
        # 从.text节区的数据开始，在代码段基址处进行反汇编
        disassembly = self.cs.disasm(self.text.data(), self.text_base)

        # 12. 初始化符号化组件生成器
        # CompGen用于从汇编中提取和符号化标签引用
        self.comp_gen = CompGen(got_addr = self.got_addr)

        # 13. 存储反汇编结果：地址 -> 指令对象
        self.instructions = {}  # address : instruction # 字典：地址 -> Capstone指令对象
        for instruction in disassembly:
            self.instructions[instruction.address] = instruction

        # 14. 获取排序后的指令地址列表
        self.instruction_addrs = list(self.instructions.keys())
        self.instruction_addrs.sort()   # 按地址升序排序

        # 15. 创建Program对象（可能用于高级程序结构分析）
        # Program可能封装了更复杂的程序分析功能
        self.prog = Program(self.elf, self.cs, asm_path=asm_dir)
        
        # 16. 匹配源代码和二进制代码（如果有调试信息）
        # 可能用于将二进制地址映射回源代码位置
        self.match_src_to_bin()


    def is_semantically_nop(self, inst):
        if isinstance(inst, capstone.CsInsn):
            mnemonic = inst.mnemonic
            operand_list = inst.op_str.split(', ')
        elif isinstance(inst, AsmInst):
            mnemonic = inst.opcode
            operand_list = inst.operand_list

        try:
            if mnemonic.startswith("nop"):
                return True
            if mnemonic[:3] == "lea" and mnemonic != 'leave':
                return operand_list[0] == "(" + operand_list[1] + ")"
            elif mnemonic[:3] == "mov" and not mnemonic.startswith("movs"):
                return operand_list[0] == operand_list[1]
        except:
            assert False, 'unexpected instruction %s' % ' '.join(operand_list)
        return False


    def get_section(self, addr):
        for section in self.elf.iter_sections():
            sec_addr = section['sh_addr']
            sec_size = section['sh_size']
            if sec_addr <= addr and addr < sec_addr + sec_size:
                return section
        return None


    def get_int(self, addr, sz = 4):
        section = self.get_section(addr)
        if not section:
            return 0
        base = section['sh_addr']
        offset = addr - base
        data = section.data()
        data = data[offset:offset + sz]
        if sz == 4:
            data = data.ljust(4, b'\x00')
            return struct.unpack("<I", data)[0]
        elif sz == 8:
            data = data.ljust(8, b'\x00')
            return struct.unpack("<Q", data)[0]


    def update_table(self, addr, comp_data, asm_path):
        for line, idx in comp_data.members:
            directive = line.split()[0]
            if directive in ['.long']:
                sz = 4
            elif directive in ['.quad']:
                sz = 8
            else:
                assert False, 'Unsupported jump table entries'

            value = self.get_int(addr, sz)

            label_dict = {comp_data.label:comp_data.addr}
            data = self.comp_gen.get_data(addr, asm_path, line, idx, value, label_dict)
            self.prog.Data[addr] = data
            #component = self.comp_gen.get_data_components(line.split()[1], value, label_dict)
            #self.prog.Data[addr] = Data(addr, component, asm_path, idx+1, line)

            addr += sz


    def update_data(self, addr, comp_data, asm_path):
        for line, idx in comp_data.members:
            directive = line.split()[0]
            if directive in ['.long']:
                sz = 4
            elif directive in ['.quad']:
                sz = 8
            elif directive in ['.word']:
                sz = 2
            elif directive in ['.byte']:
                sz = 1
            elif directive in ['.zero']:
                sz = int(line.split()[1])
            else:
                print(line)
                assert False, "unknown data type"

            expr = ' '.join(line.split()[1:])
            if sz in [4,8] and re.search('.[+|-]', expr):
                value = self.get_int(addr, sz)

                #if '@GOTOFF' in line:
                #    value += self.got_addr

                data = self.comp_gen.get_data(addr, asm_path, line, idx , value)
                self.prog.Data[addr] = data
                #component = self.comp_gen.get_data_components(expr, value)
                #self.prog.Data[addr] = Data(addr, component, asm_path, idx+1, directive+' '+ expr)

            addr += sz

    def update_labels(self, func_info, factors, asm_file): #label_dict, jmptbls, factors):
        target_addr = factors.value - factors.num
        jmp_list = []
        for label in factors.labels:
            if label == '_GLOBAL_OFFSET_TABLE_':
                continue

            if '@GOT' in label and '@GOTPCREL' not in label:
                label = label.split('@')[0]

            if label in asm_file.composite_data and not asm_file.composite_data[label].addr:
                asm_file.composite_data[label].set_addr(target_addr)

            if label in asm_file.jmp_dict:
                asm_file.jmp_dict[label].set_addr(target_addr)
                jmp_list.append((label, target_addr, len(asm_file.jmp_dict[label].members)))

            if label in asm_file.str_dict:
                asm_file.str_dict[label].set_addr(target_addr)

        return jmp_list


    def get_objdump(self):
        temp_file = "/tmp/xx" + self.bin_path.replace('/','_')
        os.system("objdump -t -f %s | grep \"F .text\" | sort > %s" % (self.bin_path, temp_file))

        funcs = []
        prev_addr = 0
        with open(temp_file) as fp:
            lines = fp.readlines()
            for line in lines:
                l = line.split()
                fname = l[-1]
                faddress = int(l[0], 16)
                fsize = int(l[4], 16)

                try:
                    #if len(loc_candidates) and fsize > 0:
                    if self.has_func_assem_file(fname) and fsize > 0:
                        if prev_addr == faddress:
                            funcs[-1][0].append(fname)
                            print(funcs[-1])
                        else:
                            funcs.append([[fname], faddress, fsize])

                    prev_addr = faddress
                except:
                    pass

        os.unlink(temp_file)

        return funcs


    def update_instr(self, func_info):

        fname, faddress, fsize = func_info

        f_offset = faddress - self.text_base
        f_end_offset = f_offset + fsize
        dump = self.cs.disasm(self.text.data()[f_offset:f_end_offset], faddress)
        for inst in dump:
            if inst.address in self.instructions:
                break
            self.instructions[inst.address] = inst
            self.instruction_addrs.append(inst.address)
        self.instruction_addrs.sort()


    def match_src_to_bin(self):
        """
        将二进制代码与源代码（汇编文件）进行匹配,建立了二进制机器码与汇编源代码之间的桥梁
        
        主要功能：
        1. 将二进制中的函数与汇编文件中的函数对齐
        2. 创建符号化指令表示
        3. 识别跳转表和函数边界
        4. 标记未知代码区域
        """

        # 初始化数据结构
        self.bin2src_dict = {}  # 二进制地址 -> 函数摘要的映射
        self.composite_data = dict()    # 复合数据字典
        self.jmp_table_dict = dict()    # 跳转表字典

        # 初始化调试信息相关变量（虽然在此函数中未使用，但可能在后续扩展中使用）
        debug_loc_paths = {}
        src_files = {}

        #result = {}
        # 从二进制文件中获取DWARF调试位置信息
        # DWARF调试信息包含源代码行号、变量位置等
        self.dwarf_loc = get_dwarf_loc(self.bin_path)

        # 通过objdump获取二进制中的函数列表
        # funcs格式: [(函数名列表, 函数地址, 函数大小), ...]
        funcs = self.get_objdump()   # [funcname, address, size] list
        # 遍历每个函数
        for func_info in funcs:
            fname_list, faddress, fsize = func_info

            # 跳过特殊的x86辅助函数
            if len(fname_list) == 1 and '__x86.get_pc_thunk' in fname_list[0]:
                continue

            '''
            Handle weird padding bytes
            '''
            '''
            处理奇怪的填充字节
            有时函数起始地址可能不在反汇编指令字典中，
            可能是因为填充字节或对齐区域
            '''
            if faddress not in self.instructions:
                # 更新指令字典，确保函数区域被反汇编
                self.update_instr(func_info) #faddress, fsize) # 参数为函数信息

            # 获取函数的机器码（用于匹配汇编文件）
            func_code = self.get_func_code(faddress, fsize)

            # 在汇编文件中查找匹配的函数
            # asm_file: 包含汇编代码的文件对象
            # addressed_asm_list: 地址化的汇编列表，每个元素为(地址, Capstone指令, 汇编标记)
            asm_file, addressed_asm_list = self.find_match_func(func_code, func_info)

            # 创建函数摘要对象，存储函数的基本信息和指令序列
            func_summary = FuncInst(addressed_asm_list, func_info, asm_file.file_path)
            # 将函数地址映射到函数摘要
            self.bin2src_dict[faddress] = func_summary

             # 遍历函数中的每条指令
            prev_opcode = ''    # 记录前一条指令的操作码
            for idx, (addr, capstone_insn, asm_token) in enumerate(addressed_asm_list):
                
                # 如果汇编标记为空（可能没有对应的汇编代码）
                if not asm_token:
                    # nop code might has no relevant assembly code
                    # 如果是nop指令或某些特殊指令
                    # 检查前一条指令是否是控制流指令
                    if prev_opcode in ['jmp', 'jmpq', 'jmpl', 'call', 'callq', 'calll', 'ret', 'retq', 'retl', 'halt', 'ud2']:
                        # 获取下一条指令的地址
                        next_addr, _, _ = addressed_asm_list[idx+1]
                        # 将当前地址到下一条指令地址之间的区域标记为对齐区域
                        # 这些区域可能是填充字节或对齐字节
                        self.prog.aligned_region.update([item for item in range(addr, next_addr)])

                    # 创建空的指令类型对象（没有汇编标记）
                    self.prog.Instrs[addr] = InstType(addr, asm_file.file_path)
                    continue
                
                # 更新前一条指令的操作码
                prev_opcode = capstone_insn.mnemonic

                # 使用符号化生成器创建指令对象
                # 参数：地址，汇编文件路径，汇编标记，Capstone指令
                instr = self.comp_gen.get_instr(addr, asm_file.file_path, asm_token, capstone_insn)
                # 存储指令对象
                self.prog.Instrs[addr] = instr

                # update labels
                # 更新标签信息，处理跳转表
                jmp_list = []   # 存储跳转表信息
                # 如果指令的立即数字段包含标签
                if instr.imm and instr.imm.has_label():
                    # 更新标签信息，并获取可能的跳转表信息
                    ret = self.update_labels(func_summary, instr.imm, asm_file)
                    jmp_list.extend(ret)
                # 如果指令的位移字段包含标签
                if instr.disp and instr.disp.has_label():
                    ret = self.update_labels(func_summary, instr.disp,  asm_file)
                    jmp_list.extend(ret)

                # 处理跳转表
                for (label, jmp_base, jmp_size) in jmp_list:
                    # 将跳转表信息注册到函数摘要中
                    func_summary.register_jmp_table(addr, label, jmp_base, jmp_size)


        # 处理未知区域（不属于任何函数的代码区域）
        text_end = self.text.data_size + self.text_base # 代码段结束地址
        prev_end = self.text_base   # 上一个函数结束地址，初始为代码段起始地址
        unknown_region = set()  # 未知区域集合
        # 遍历所有函数地址（按地址排序）
        for faddress in sorted(self.bin2src_dict.keys()):
            # 从上一个函数结束到当前函数开始之间的区域是未知区域
            unknown_region.update(range(prev_end, faddress))
            # 更新上一个函数结束地址为当前函数结束地址
            prev_end = faddress + self.bin2src_dict[faddress].size
        # 最后一个函数结束到代码段结束之间的区域也是未知区域
        unknown_region.update(range(prev_end, text_end))
        # 将未知区域存储到程序对象中
        self.prog.unknown_region = unknown_region



    def is_semantically_same(self, insn, asm):

        if insn.mnemonic[:-1] == asm.opcode:
            return True
        if insn.mnemonic == asm.opcode[:-1]:
            return True
        if insn.mnemonic.startswith('rep') and asm.opcode.startswith('rep'):
            if insn.mnemonic.split()[1] == asm.opcode.split()[1]:
                return True
        if insn.group(capstone.CS_GRP_JUMP):
            jumps = [
                ["jo"],
                ["jno"],
                ["js"],
                ["jns"],
                ["je", "jz"],
                ["jne", "jnz"],
                ["jb", "jna", "jc"],
                ["jnb", "jae", "jnc"],
                ["jbe", "jna"],
                ["ja", "jnb"],
                ["jl", "jng"],
                ["jge", "jnl"],
                ["jle", "jng"],
                ["jg", "jnl"],
                ["jp", "jpe"],
                ["jnp", "jpo"],
                ["jcx", "jec"]
            ]
            for jump in jumps:
                if insn.mnemonic in jump and asm.opcode in jump:
                    return True
        else:
            opcodes = [
                # Mnemonic Alias
                ["call", "callw"],
                ["call", "calll"],
                ["call", "callq"],
                ["cbw",  "cbtw"],
                ["cwde", "cwtl"],
                ["cwd",  "cwtd"],
                ["cdq",  "cltd"],
                ["cdqe", "cltq"],
                ["cqo",  "cqto"],
                ["lret", "lretw"],
                ["lret", "lretl"],
                ["leavel", "leave"],
                ["leaveq", "leave"],
                ["loopz",  "loope"],
                ["loopnz", "loopne"],
                ["popf",  "popfw"],
                ["popf",  "popfl"],
                ["popf",  "popfq"],
                ["popfd", "popfl"],
                ["pushf",  "pushfw"],
                ["pushf",  "pushfl"],
                ["pushf",  "pushfq"],
                ["pushfd", "pushfl"],
                ["pusha",  "pushaw"],
                ["pusha",  "pushal"],
                ["repe",  "rep"],
                ["repz",  "rep"],
                ["repnz", "repne"],
                ["ret", "retw"],
                ["ret", "retl"],
                ["ret", "retq"],
                ["salb", "shlb"],
                ["salw", "shlw"],
                ["sall", "shll"],
                ["salq", "shlq"],
                ["smovb", "movsb"],
                ["smovw", "movsw"],
                ["smovl", "movsl"],
                ["smovq", "movsq"],
                ["ud2a",  "ud2"],
                ["verrw", "verr"],
                ["sysret",  "sysretl"],
                ["sysexit", "sysexitl"],
                ["lgdt", "lgdtw"],
                ["lgdt", "lgdtl"],
                ["lgdt", "lgdtq"],
                ["lidt", "lidtw"],
                ["lidt", "lidtl"],
                ["lidt", "lidtq"],
                ["sgdt", "sgdtw"],
                ["sgdt", "sgdtl"],
                ["sgdt", "sgdtq"],
                ["sidt", "sidtw"],
                ["sidt", "sidtl"],
                ["sidt", "sidtq"],
                ["fcmovz",   "fcmove"],
                ["fcmova",   "fcmovnbe"],
                ["fcmovnae", "fcmovb"],
                ["fcmovna",  "fcmovbe"],
                ["fcmovae",  "fcmovnb"],
                ["fcomip",   "fcompi"],
                ["fildq",    "fildll"],
                ["fistpq",   "fistpll"],
                ["fisttpq",  "fisttpll"],
                ["fldcww",   "fldcw"],
                ["fnstcww",  "fnstcw"],
                ["fnstsww",  "fnstsw"],
                ["fucomip",  "fucompi"],
                ["fwait",    "wait"],
                ["fxsaveq",   "fxsave64"],
                ["fxrstorq",  "fxrstor64"],
                ["xsaveq",    "xsave64"],
                ["xrstorq",   "xrstor64"],
                ["xsaveoptq", "xsaveopt64"],
                ["xrstorsq",  "xrstors64"],
                ["xsavecq",   "xsavec64"],
                ["xsavesq",   "xsaves64"],
                # findings
                ['shl', 'sal'],
                ['cmovael', 'cmovnb'],
                ['cmovbq', 'cmovc'],
                ['retq', 'rep ret'],
                ['retl', 'rep ret'],
                # assembler optimization
                ['leaq', 'movq'],
                ['leal', 'movl'],
            ]
            for opcode in opcodes:
                if insn.mnemonic in opcode and asm.opcode in opcode:
                    return True

            if self.check_suffix(insn.mnemonic, asm.opcode):
                return True

            if insn.mnemonic in ['addq'] and asm.opcode in ['subq']:
                if asm.operand_list[0].startswith('$-'):
                    return True

            capstone_bugs = [
                ['movd', 'movq'],
                ['cmovaeq', 'cmovnb'],
                ['cmovaew', 'cmovnb'],
                ['cmovbl', 'cmovc'],
                ['cmovael', 'cmovnc'],
                ['cmovaeq', 'cmovnc'],
            ]
            for opcode in capstone_bugs:
                if insn.mnemonic in opcode and asm.opcode in opcode:
                    return True

        return False

    def check_suffix(self, opcode1, opcode2):
        suffix_list = [('(.*)c$','(.*)b$'),      #setc   -> setb
            ('(.*)z$','(.*)e$'),       #setz   -> sete
            ('(.*)na$','(.*)be$'),     #setna  -> setbe
            ('(.*)nb$','(.*)ae$'),     #setnb  -> setae
            ('(.*)nc$','(.*)ae$'),     #setnc  -> setae
            ('(.*)ng$','(.*)le$'),     #setng  -> setle
            ('(.*)nl$','(.*)ge$'),     #setnl  -> setge
            ('(.*)nz$','(.*)ne$'),     #setnl  -> setge
            ('(.*)pe$','(.*)p$'),      #setpe  -> setp
            ('(.*)po$','(.*)np$'),     #setpo  -> setnp
            ('(.*)nae$','(.*)b$'),     #setnae -> setb
            ('(.*)nbe$','(.*)a$'),     #setnbe -> seta
            ('(.*)nge$','(.*)l$'),     #setnbe -> seta
            ('(.*)nle$','(.*)g$')]     #setnle -> setg
        for (suff1, suff2) in suffix_list:
            rex = suff1+'|'+suff2
            if re.search(rex, opcode1) and re.search(rex,opcode2):
                if re.search(suff1, opcode1): tmp1 = re.findall(suff1, opcode1)[0]
                else: tmp1 = re.findall(suff2, opcode1)[0]
                if re.search(suff1, opcode2): tmp2 = re.findall(suff1, opcode2)[0]
                else: tmp2 = re.findall(suff2, opcode2)[0]
                if tmp1 == tmp2:
                    return True
        return False

    def assem_addr_map(self, func_code, asm_token_list, candidate_len, debug=False, malformed = True):
        addressed_asm_list = []
        idx = 0
        for bin_idx, bin_asm in enumerate(func_code):
            if idx >= len(asm_token_list):
                if self.is_semantically_nop(bin_asm):
                    addressed_asm_list.append((bin_asm.address, bin_asm, ''))
                    continue
                return []
            asm_token = asm_token_list[idx]

            if bin_asm.address in self.dwarf_loc:
                dwarf_set1 = self.dwarf_loc[bin_asm.address]
                dwarf_set2 = set()
                while isinstance(asm_token, LocInfo):
                    dwarf_set2.add( '%s:%d'%(asm_token.path, asm_token.idx))
                    idx += 1
                    if idx >= len(asm_token_list):
                        return []
                    asm_token = asm_token_list[idx]
                #give exception for a first debug info since some debug info is related to prev func
                #in case of weak symbols, multiple debug info could be merged.
                #ex) {'xercesc/dom/DOMNodeImpl.hpp:271', './xercesc/dom/impl/DOMNodeImpl.hpp:271'}
                if dwarf_set2 - dwarf_set1:
                    #clang might eliminate file path..
                    new_dwarf_set1 = set()
                    for debug_str in dwarf_set1:
                        file_path, no = debug_str.split(':')
                        file_name = os.path.basename(file_path)
                        new_dwarf_set1.add('%s:%s'%(file_name, no))

                    new_dwarf_set2 = set()
                    for debug_str in dwarf_set2:
                        file_path, no = debug_str.split(':')
                        file_name = os.path.basename(file_path)
                        new_dwarf_set2.add('%s:%s'%(file_name, no))

                    if new_dwarf_set2 - new_dwarf_set1:
                        if (self.is_semantically_nop(bin_asm) and
                            func_code[bin_idx+1].address in self.dwarf_loc):
                            dwarf_set3 = self.dwarf_loc[func_code[bin_idx+1].address]
                            for debug_str in dwarf_set3:
                                file_path, no = debug_str.split(':')
                                file_name = os.path.basename(file_path)
                                new_dwarf_set1.add('%s:%s'%(file_name, no))
                            if new_dwarf_set2 - new_dwarf_set1:
                                return []
                            else:
                                pass
                        else:
                            if addressed_asm_list and not malformed:
                                return []
                            else:
                                # debug info mismatch is allowed
                                # at the beginning of function
                                pass

            if isinstance(asm_token, LocInfo):
                # nop code might not have debug info
                if self.is_semantically_nop(bin_asm):
                    addressed_asm_list.append((bin_asm.address, bin_asm, ''))
                    continue
                elif debug:
                    # some debug info might be omitted
                    while isinstance(asm_token, LocInfo):
                        idx += 1
                        asm_token = asm_token_list[idx]
                    pass
                else:
                    return []

            if self.is_semantically_nop(bin_asm):
                #.align might cause nop code
                if self.is_semantically_nop(asm_token):
                    addressed_asm_list.append((bin_asm.address, bin_asm, asm_token))
                else:
                    addressed_asm_list.append((bin_asm.address, bin_asm, ''))
                    continue
            elif asm_token.opcode == bin_asm.mnemonic:
                addressed_asm_list.append((bin_asm.address, bin_asm, asm_token))
            #capstone couldn't properly handle notrack instruction
            elif len(asm_token.opcode.split()) == 2 and (
                    asm_token.opcode.split()[0] == 'notrack' and
                    asm_token.opcode.split()[1].startswith('jmp') and
                    bin_asm.mnemonic.startswith('jmp')):
                addressed_asm_list.append((bin_asm.address, bin_asm, asm_token))
            elif self.is_semantically_same(bin_asm, asm_token):
                addressed_asm_list.append((bin_asm.address, bin_asm, asm_token))
            else:
                if candidate_len > 1:
                    if debug:
                        pass
                    return []
                print(bin_asm)
                print('%s %s'%(asm_token.opcode, ' '.join(asm_token.operand_list)))
                addressed_asm_list.append((bin_asm.address, bin_asm, asm_token))
                #return []
                #assert False, 'Unexpacted instruction sequence'
            idx += 1

        if idx < len(asm_token_list):
            for idx2 in range(idx, len(asm_token_list)):
                if not isinstance(asm_token_list[idx2], LocInfo):
                    #assert False, 'Unexpacted instruction sequence'
                    return []

        return addressed_asm_list

    def find_match_func(self, func_code, func_info):

        fname_list, faddress, fsize = func_info
        for fname in fname_list:
            if not self.has_func_assem_file(fname):
                return None

        if len(fname_list) > 1:
            print(fname_list)
        ret = []
        candidate_dict = dict()
        for fname in fname_list:
            candidate_dict[fname] = self.get_assem_file(fname)
        malformed = False
        if len(candidate_dict) == 0:
            print("%x: there is no available candidate, so we extract visited candidates"%(faddress))
            for fname in fname_list:
                candidate_dict[fname] = self.get_assem_file(fname, include_visited_func=True)
            malformed = True

        candidate_len = 0
        for asm_file_list in candidate_dict.values():
            candidate_len += len(asm_file_list)

        for fname, asm_file_list in candidate_dict.items():
            for asm_file in asm_file_list:
                asm_basename = os.path.basename(asm_file.file_path)
                if asm_basename in ['base32-basenc.s', 'base64-basenc.s', 'basenc-basenc.s',
                            'b2sum-b2sum.s', 'cksum-b2sum.s', 'b2sum-blake2b-ref.s', 'cksum-blake2b-ref.s',
                            'b2sum-digest.s', 'cksum-digest.s', 'md5sum-digest.s', 'sha1sum-digest.s',
                            'sha224sum-digest.s', 'sha256sum-digest.s', 'sha384sum-digest.s',
                            'sha512sum-digest.s', 'sum-digest.s', 'cksum-sum.s', 'sum-sum.s']:
                    if asm_basename.split('-')[0] != os.path.basename(self.bin_path):
                        continue

                if os.path.basename(asm_file.file_path) in ['src_sha224sum-md5sum.s']:
                    if os.path.basename(self.bin_path) in ['sha512sum', 'sha256sum', 'sha384sum']:
                        continue
                if os.path.basename(asm_file.file_path) in ['src_sha256sum-md5sum.s']:
                    if os.path.basename(self.bin_path) in ['sha512sum', 'sha224sum', 'sha384sum']:
                        continue
                if os.path.basename(asm_file.file_path) in ['src_sha384sum-md5sum.s']:
                    if os.path.basename(self.bin_path) in ['sha512sum', 'sha224sum', 'sha256sum']:
                        continue
                if os.path.basename(asm_file.file_path) in ['src_sha512sum-md5sum.s']:
                    if os.path.basename(self.bin_path) in ['sha224sum', 'sha256sum', 'sha384sum']:
                        continue
                if 'usable_st_size' in fname:
                    '''
                        grep  '^usable_st_size:'  coreutils-8.30/x64/clang/nopie/o1-bfd/src/* -A 10 | grep orl
                        coreutils-8.30/x64/clang/nopie/o1-bfd/src/dd.s-	orl	24(%rdi), %eax
                        coreutils-8.30/x64/clang/nopie/o1-bfd/src/head.s-	orl	24(%rdi), %eax
                        coreutils-8.30/x64/clang/nopie/o1-bfd/src/od.s-	orl	24(%rdi), %eax
                        coreutils-8.30/x64/clang/nopie/o1-bfd/src/shuf.s-	orl	24(%rdi), %eax
                        coreutils-8.30/x64/clang/nopie/o1-bfd/src/split.s-	orl	in_stat_buf+24(%rip), %eax
                        coreutils-8.30/x64/clang/nopie/o1-bfd/src/tail.s-	orl	24(%rdi), %eax
                        coreutils-8.30/x64/clang/nopie/o1-bfd/src/truncate.s-	orl	24(%rdi), %eax
                        coreutils-8.30/x64/clang/nopie/o1-bfd/src/wc.s-	orl	24(%rdi), %eax
                    '''
                    if os.path.basename(asm_file.file_path) in ['dd.s', 'head.s', 'od.s', 'shuf.s', 'tail.s', 'truncate.s', 'wc.s']:
                        if os.path.basename(self.bin_path) in ['split']:
                            continue
                    if os.path.basename(asm_file.file_path) in ['split.s']:
                        if os.path.basename(self.bin_path) in  ['dd', 'head', 'od', 'shuf', 'tail', 'truncate', 'wc']:
                            continue


                #asm_inst_list = [line for line in asm_file.func_dict[fname] if isinstance(line, AsmInst)]
                #addressed_asm_list = self.assem_addr_map(func_code, asm_inst_list, candidate_len)
                addressed_asm_list = self.assem_addr_map(func_code, asm_file.func_dict[fname], candidate_len, malformed)

                if not addressed_asm_list:
                    continue
                ret.append((fname, asm_file, addressed_asm_list))


        if not ret:
            # debug info might be omitted.
            # we give some exception to assembly matching.
            for fname, asm_file_list in candidate_dict.items():
                for asm_file in asm_file_list:
                    addressed_asm_list = self.assem_addr_map(func_code, asm_file.func_dict[fname], candidate_len, True)

                if addressed_asm_list:
                    ret.append((fname, asm_file, addressed_asm_list))

            if len(ret) == 0:
                import pdb
                pdb.set_trace()
            assert len(ret) > 0, 'No matched assembly code'


        fname, asm_file, addressed_asm_list = ret[0]
        asm_file.visited_func.add(fname)

        return asm_file, addressed_asm_list

    def get_func_code(self, address, size):
        try:
            result = []
            idx = self.instruction_addrs.index(address)
            curr = address
            while True:
                if curr >= address + size:
                    break
                inst = self.instructions[curr]
                result.append(inst)
                curr += inst.size
            return result
        except:
            print(hex(curr))
            print("Disassembly failed.")
            exit()

    def get_src_files(self, src_files, loc_candidates):
        for loc_path, _ in loc_candidates:
            if loc_path not in src_files.keys():
                if self.build_path:
                    loc_path_full = os.path.join(self.build_path, loc_path[1:])
                    f = open(loc_path_full, errors='ignore')
                    src_files[loc_path] = f.read()
                else:
                    loc_path_full = os.path.join(self.asm_dir, loc_path[1:])
                    f = open(loc_path_full, errors='ignore')
                    src_files[loc_path] = f.read()
        return src_files


    def get_src_paths(self):
        srcs = []
        for i in range(20):
            t = "*/" * i
            srcs += glob.glob(self.asm_dir + t + "*.s")

        # give a first priority to a main source code
        main_src = '%s/src/%s.s'%(self.asm_dir, os.path.basename(self.bin_path))
        if main_src in srcs:
            srcs.remove(main_src)
            srcs.insert(0, main_src)

        return srcs

    def has_func_assem_file(self, func_name):
        return func_name in self._func_map

    def get_assem_file(self, func_name, include_visited_func=False):
        ret = []
        for asm_path in self._func_map[func_name]:
            #ignored referred assembly file
            #since local function can be defined twice
            # _Z41__static_initialization in 483.xalancbmk
            if func_name in self.asm_file_dict[asm_path].visited_func:
                if include_visited_func:
                    ret.append(self.asm_file_dict[asm_path])
                pass
            else:
                ret.append(self.asm_file_dict[asm_path])
        return ret

    def collect_loc_candidates(self):

        srcs = self.get_src_paths()
        #result = {}

        self._func_map = defaultdict(list)
        self.asm_file_dict = dict()

        for src in srcs:
            asm_file = AsmFileInfo(src)
            asm_file.scan()
            self.asm_file_dict[src] = asm_file
            for func_name in asm_file.func_dict.keys():
                self._func_map[func_name].append(src)


    def normalize_data(self):
        """
        规范化数据处理函数
        主要功能：处理数据段和重定位信息，将汇编文件中的数据定义和重定位条目转换为符号化表示
        
        处理步骤：
        1. 处理汇编文件中的复合数据（如.data节中的符号定义）
        2. 处理跳转表和字符串数据
        3. 处理所有重定位条目
        4. 将处理结果存储到self.prog.Data字典中
        """
        visited_label = []  # 记录已处理的标签，避免重复处理
        # 第一部分：处理汇编文件中已解析地址的复合数据
        # 复合数据：汇编文件中定义的数据结构，如全局变量、数组等
        for asm_path, asm_file in self.asm_file_dict.items():
            for label, comp_data in asm_file.composite_data.items():
                if comp_data.addr:  # 如果数据已经有解析出的地址
                    # 更新数据：将汇编文件中的数据定义转换为符号化数据对象
                    self.update_data(comp_data.addr, comp_data, asm_path)
                    visited_label.append(label) # 标记为已处理

        # 第二部分：处理汇编文件中未解析地址但符号表中有对应项的复合数据
        for asm_path, asm_file in self.asm_file_dict.items():
            for label, comp_data in asm_file.composite_data.items():
                if not comp_data.addr:  # 数据没有解析出的地址
                    # 检查符号表中是否有对应的符号定义
                    if label in self.symbs and len(self.symbs[label]) == 1 and label not in visited_label:
                        #if symbol size is zero we ignore it
                        # 如果符号大小为0则忽略（可能是未初始化的符号）
                        if self.symbs[label][0][1] == 0:
                            continue
                        # 使用符号表中的地址来更新数据
                        self.update_data(self.symbs[label][0][0], comp_data, asm_path)
                        visited_label.append(label)
                    # 如果没有找到对应的符号，可能需要记录但当前忽略
                    #else:
                    #    print('unknown comp data %s:%s'%(asm_path, label))

         # 第三部分：验证已处理的数据地址与重定位地址的一致性
        comp_set = set(self.prog.Data.keys())
        reloc_set = set(self.relocs)

        # 打印未重定位但被处理的数据地址（可能有问题）
        if comp_set - reloc_set:
            print(comp_set - reloc_set)
        
        # 第四部分：处理跳转表和字符串数据
        # 跳转表：用于switch语句等间接跳转的目标表
        # 字符串数据：汇编文件中定义的字符串常量
        for asm_path, asm_file in self.asm_file_dict.items():
            # 处理跳转表
            for label, comp_data in asm_file.jmp_dict.items():
                if comp_data.addr:  # 跳转表有解析出的地址
                    # 更新跳转表数据
                    self.update_table(comp_data.addr, comp_data, asm_path)
                    visited_label.append(label)
            # 处理字符串数据
            for label, comp_data in asm_file.str_dict.items():
                if comp_data.addr:  # 字符串数据有解析出的地址
                    # 更新字符串数据
                    self.update_table(comp_data.addr, comp_data, asm_path)
                    visited_label.append(label)

        # 第五部分：处理所有重定位条目
        # 重定位条目：指示链接器在加载时需要修改的位置
        for addr in self.relocs:
            # 如果该地址已处理过，跳过（可能是复合数据或跳转表）
            if addr in self.prog.Data:
                # composite ms || already processed
                continue
            # 获取重定位信息：大小、是否是GOT重定位、重定位类型
            sz, is_got, r_type = self.relocs[addr]
            # 从二进制文件中读取该地址处的值
            value = self.get_int(addr, sz)
            #This reloc data is added by linker
            #if value == 0 and r_type in ['R_X86_64_64']:
            #    asm_line = '.quad %s'%(r_type)
            #    pass
            #elif value == 0:
            #    continue
            # 跳过某些特定的重定位类型
            # R_X86_64_COPY: 复制重定位，由动态链接器处理
            # R_X86_64_REX_GOTPCRELX: 优化后的GOTPCRELX重定位
            # R_386_COPY: 32位版本的复制重定位
            if r_type in ['R_X86_64_COPY', 'R_X86_64_REX_GOTPCRELX', 'R_386_COPY']:
                continue
            # 处理GLOB_DAT和JUMP_SLOT类型重定位（全局数据和跳转槽）
            elif r_type in ['R_X86_64_GLOB_DAT', 'R_X86_64_JUMP_SLOT', 'R_386_GLOB_DAT', 'R_386_JUMP_SLOT']:
                # 这些类型通常用于动态链接，值为符号的实际地址
                label = 'L%x'%(value)   # 生成临时标签
                asm_line = '.long ' + label # 创建.long伪指令
            # 处理其他重定位类型
            else:
                directive = '.long' # 默认使用.long（4字节）
                # 如果值为0，使用重定位类型作为标签（特殊标记）
                if value == 0:
                    label = r_type
                else:
                    # 如果值不为0，生成基于值的标签
                    if is_got:
                        # GOT相对重定位：调整值加上GOT基地址
                        value += self.got_addr
                        label = 'L%x@GOTOFF'%(value)    # 添加@GOTOFF后缀
                    else:
                        label = 'L%x'%(value)
                        if sz == 8: directive = '.quad' # 如果是8字节，使用.quad伪指令

                asm_line = directive + ' ' + label  # 创建汇编行

            # 使用符号生成器创建数据对象
            # 参数：地址，汇编文件路径（这里为空字符串），汇编行，索引，值，重定位类型
            data = self.comp_gen.get_data(addr, '',  asm_line, 0, value, r_type = r_type)
            # 将符号化数据存储到Program对象中
            self.prog.Data[addr] = data

    def save(self, save_file):
        with open(save_file, 'wb') as f:
            pickle.dump(self.prog, f)

    def save_func_dict(self, save_file):
        with open(save_file, 'w') as f:
            res = {}
            for key, val in self.bin2src_dict.items():
                func_info = dict()
                func_info['asm_path'] = val.asm_path
                func_info['addr'] = hex(val.addr)
                func_info['inst_addrs'] = [hex(addr) for (addr, _, _) in val.inst_list]
                func_info['jmp_tables'] = []
                for tbl in val.jmp_table_list:
                    func_info['jmp_tables'].append({'inst_addr':hex(tbl['inst_addr']),
                        'label':tbl['label'], 'addr':hex(tbl['addr']), 'size':tbl['size']})

                res[hex(key)] = func_info

            data = json.dumps(res, indent=1)
            #print(re.sub(r',\n\s*([0-9])', r',\1', data), file=f)
            print(re.sub(r',\n\s*"([0-9])', r',"\1', data), file=f)

class FuncSummary:
    def __init__(self, func_inst):
        self.asm_path = func_inst.asm_path
        self.addr = func_inst.addr
        self.inst_addrs = [addr for (addr, _, _) in func_inst.inst_list]
        self.jmp_table_list = func_inst.jmp_table_list



import argparse
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='normalize_retro')
    parser.add_argument('bin_path', type=str)
    parser.add_argument('asm_dir', type=str)
    parser.add_argument('save_file', type=str)
    parser.add_argument('--reloc', type=str)
    parser.add_argument('--build_path', type=str)
    parser.add_argument('--save_func_dict', type=str)
    args = parser.parse_args()

    gt = NormalizeGT(args.bin_path, args.asm_dir, args.reloc, args.build_path)
    gt.normalize_data()

    gt.save(args.save_file)

    if args.save_func_dict:
        gt.save_func_dict(args.save_func_dict)

