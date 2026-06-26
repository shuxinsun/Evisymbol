#!/usr/bin/env python

import argparse
import angr
import struct
from collections import defaultdict

from intervaltree import IntervalTree

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
from elftools.elf.relocation import RelocationSection
from elftools.elf.enums import ENUM_RELOC_TYPE_x64

from .container import Container, Function, DataSection
from .consts import PTR_SIZE
from .disasm import disasm_bytes


class Loader():
    def __init__(self, fname):
        # 以二进制方式打开 fname 指向的文件，并把文件句柄保存到 self.fd 中，供后续读取使用。
        self.fname = fname
        self.fd = open(fname, 'rb')
        self.elffile = ELFFile(self.fd)
        self.container = Container()
    # this function is checking is the binarie is suited for retrowrite rewriting (PIE/PIC)
    def is_nonpie(self):
        base_address = next(seg for seg in self.elffile.iter_segments() 
                                        if seg['p_type'] == "PT_LOAD")['p_vaddr']
        return not (self.elffile['e_type'] == 'ET_DYN' and base_address == 0)

    def get_binaryfile_addr(self):
        # 找第一个 LOAD 段
        first_load_segment = next(
            s for s in self.elffile.iter_segments() 
            if s.header.p_type == 'PT_LOAD'
        )
        base_addr = first_load_segment.header.p_vaddr
        return base_addr
    
    def is_stripped(self):
        # Get the symbol table entry for the respective symbol
        symtab = self.elffile.get_section_by_name('.symtab')
        if not symtab:
            # print('No symbol table available, this file is probably stripped!')
            return True

        sym = symtab.get_symbol_by_name("main")[0]
        if not sym:
            # print('Symbol {} not found')
            return True
        return False

    def is_pie(self):
        base_address = next(seg for seg in self.elffile.iter_segments() 
                                        if seg['p_type'] == "PT_LOAD")['p_vaddr']
        return self.elffile['e_type'] == 'ET_DYN' and base_address == 0
    
    # 判断 ELF 文件是否包含符号表（.symtab）
    def has_symbol_table(self):
        symtab = self.elffile.get_section_by_name('.symtab')
        return symtab is not None and symtab.num_symbols() > 0
    
    def load_functions(self, fnlist):
        '''
        (1)对于代码段中的每个函数,提取其机器码并创建 Function 对象,然后添加到容器中.
        (2)确认用于存储启动时自动被调用的函数指针数组.init_array节区的存在，若不存在则手动创建.
        '''
        # ssx:从ELF文件的.text段中提取已知函数的机器代码。
        # ssx:获取.text节区（代码段）的信息
        text_section = self.elffile.get_section_by_name(".text")
        text_data = text_section.data() # ssx:代码段的原始字节数据
        text_base = text_section['sh_addr'] # ssx:代码段的基地址
        # ssx:遍历函数列表，加载每个函数
        for faddr, fvalue in fnlist.items():
            section_offset = faddr - text_base  # ssx:计算函数在.text节区中的偏移量
            bytes = text_data[section_offset:section_offset + fvalue["sz"]] # ssx:切片提取函数的机器码字节(从函数起始点到函数终止点)  fvalue["sz"]是函数的大小-字节数
            
            fixed_name = fvalue["name"].replace("@", "_") # ssx:处理函数名（替换特殊字符）
            # ssx:创建Function对象并添加到容器
            function = Function(fixed_name, faddr, fvalue["sz"], bytes,
                                fvalue["bind"]) # ssx:bind:符号绑定类型（如全局、局部等）
            self.container.add_function(function)

        # ssx: 获取.init_array节区（初始化函数数组）
        section = self.elffile.get_section_by_name(".init_array")
        if section:
            data = section.data()
            # section = self.elffile.get_section_by_name(".fini_array")
            # data += section.data()
            # ssx:遍历.init_array中的每个函数指针（每8字节一个地址）
            for e,i in enumerate(range(0, len(data), 8)):
                address = data[i:i+8]
                addr_int = struct.unpack("<Q", address)[0] # ssx:小端序解包为整数
                # ssx:检查这个函数是否已经在容器中
                func = self.container.functions.get(addr_int, None)
                if func == None:
                    print(f"[ERROR] ERROR: missed .init_array function symbol at {hex(addr_int)}")
                    # TODO 
                    # We need to add them to the function list
                    # we need to "add_function" like right above
                    # ssx:需要手动创建这些缺失的函数:通过查找下一个函数的地址来确定当前函数的大小
                    min_next_func = 0xffffffffffffffff
                    for func in self.container.functions:
                        if func > addr_int:
                            min_next_func = min(min_next_func, func)
                    # ssx:如果能确定函数大小
                    if min_next_func != 0xffffffffffffffff:
                        sz = min_next_func - addr_int # ssx:计算函数大小
                        # ssx:提取函数的机器码
                        func_bytes = text_data[addr_int - text_base:addr_int - text_base + sz]
                        if e == 0:
                            # ssx:第一个初始化函数特殊处理：只包含ret指令
                            # skip first initial array and just do ret (problems with _ITM_registerTMClone... begin unlinkable)
                            self.container.add_function(Function(f"entry_{hex(addr_int)}", addr_int, sz, b"\xc3"))
                        else:
                            # ssx:其他初始化函数使用实际的机器码
                            self.container.add_function(Function(f"entry_{hex(addr_int)}", addr_int, sz, func_bytes))

        # fill gaps 
        # functions = list(sorted(self.container.functions.items()))
        # print(functions)
        # for i, f in enumerate(functions):
        #     _, function = f
        #     if i < len(functions) - 1:
        #         if function.start + function.sz < functions[i+1][1].start:
        #             sz = functions[i+1][1].start - (function.start + function.sz)
        #             new_start = function.start + function.sz
        #             func_bytes = text_data[new_start - text_base:new_start + sz - text_base]
        #             self.container.add_function(Function(f"entry_{hex(new_start)}", new_start, sz, func_bytes))
            

    '''
    处理数据相关得section
    (1)对于".init_array"节区:解析存储的函数指针值，然后检查这个指针是否指向一个已知的函数
    (2)其他节区，直接将原始数据添加到more中
    (3)生成DataSection对象
    (4)单独处理.plt、.got/.got.plt、.plt.sec、.plt.got节区
    '''
    def load_data_sections(self, seclist, section_filter=lambda x: True):
        # ssx:处理数据相关得section
        for sec in [sec for sec in seclist if section_filter(sec)]:
            sval = seclist[sec] # ssx:节区的元数据 (sval)
            section = self.elffile.get_section_by_name(sec)
            data = section.data() # ssx:节区的实际数据 (data)
            more = bytearray()
            # ssx:遍历原始数据，解析指针值，然后检查这个指针是否指向一个已知的函数
            if sec == ".init_array":
                # TODO: get PTR_SIZE from specific architecture as needed.
                for i in range(0, len(data), PTR_SIZE):

                    ptr_raw = data[i:i+PTR_SIZE]
                    ptr = struct.unpack("<Q", ptr_raw)[0]

                    func = self.container.functions.get(ptr, None)
                    # ssx:指向未知函数，打印警告信息
                    if func == None:
                        print("[WARNING] Found .init_array pointer to an unknown function at address 0x%08x" % (ptr))
                        print("[WARNING] This could be a bug. Please report it your case here: https://github.com/HexHive/retrowrite/issues/new")
                    # ssx: 指向已知函数
                    else:
                        # GCC will output frame_dummy by default in most new 
                        # binaries as needed, as part of libc. If we find it 
                        # here we should strip it out so that it isn't 
                        # symbolized when we process relocations.
                        # ssx:这段代码的目的是从.init_array节区中移除对frame_dummy函数的引用，以避免在后续的重定位处理中对其进行符号化。注释中已经解释了原因：frame_dummy是GCC默认输出的一个函数，属于libc的一部分，通常不需要被符号化。
                        if func.name == "frame_dummy":
                            print("[NOTE] .init_array frame_dummy pointer removed.")
                            continue
                        # we are all good.
                        print("[NOTE] .init_array function %s left in place" % func.name)
                    # ssx:已知函数则保留
                    more.extend(ptr_raw)
            else:
                #ssx:其他节区，直接将原始数据添加到more中
                more.extend(data)
                # ssx:如果处理后的数据长度小于指定的节区大小（sval['sz']），则用0填充到指定大小。
                if len(more) < sval['sz']:
                    more.extend(
                        [0x0 for _ in range(0, sval['sz'] - len(more))])
            # ssx:创建一个DataSection对象，并将其添加到容器中
            bytes = more
            ds = DataSection(sec, sval["base"], sval["sz"], bytes,
                             sval['align'])

            self.container.add_section(ds)

        # Find if there is a plt section
        # 单独处理.plt、.got/.got.plt、.plt.sec、.plt.got节区
        for sec in seclist:
            # ssx:查找 PLT 节区并设置基址
            if sec == '.plt':
                self.container.plt_base = seclist[sec]['base']
            if sec == '.plt.sec': # support old gcc version, skip one plt entry
                self.container.plt_base = seclist[sec]['base'] - 16
            # ssx:获取节区数据，并反汇编节区中的代码 
            if sec == ".plt.got" or sec == ".plt.sec":
                section = self.elffile.get_section_by_name(sec)
                data = section.data()
                entries = list(
                    disasm_bytes(section.data(), seclist[sec]['base']))
                self.container.gotplt_base = seclist[sec]['base']
                self.container.gotplt_sz = seclist[sec]['sz'] + 16
                self.container.gotplt_entries = entries
            # ssx:创建一个区间树（IntervalTree）来记录GOT节区的地址范围
            if sec == ".got":
                self.container.got = IntervalTree()
                base = seclist[sec]['base']
                end = base + seclist[sec]['sz']
                self.container.got[base:end] = "GOT"

                self.container.got_base = base
                self.container.got_sz = seclist[sec]['sz']
                # 构建 GOT 条目列表，用于精确匹配 target_address
                got_entries = []
                for i in range(0, len(data), PTR_SIZE):
                    ptr_raw = data[i:i+PTR_SIZE]
                    if len(ptr_raw) < PTR_SIZE:
                        break
                    ptr = struct.unpack("<Q", ptr_raw)[0]  # 小端解析

                    # 直接从符号表缓存查找
                    if not hasattr(self.container, "_symtab_cache"):
                        self.container._build_symtab_cache(self.elffile)
                    sym_info = self.container._symtab_cache.get(ptr)
                    sym_name = sym_info[0] if sym_info else None
                    entry = {
                        "address": base + i,
                        "symbol_name": sym_name,
                    }
                    got_entries.append(entry)
                self.container.got_entries = got_entries

    '''
    (1)将解析得到的重定位信息按节区加载到容器中
    (2)特殊处理 PLT，把 PLT 重定位条目映射到对应的 PLT 地址
    (3)并对未加载节区打印警告
    '''
    def load_relocations(self, relocs):
        for reloc_section, relocations in relocs.items():
            section = reloc_section[5:] # ssx:移除 ".rela" 前缀
            # ssx:特殊处理 PLT 重定位
            # ssx: 将每个 PLT 重定位条目（即每个需要通过 PLT 调用的函数）与 PLT 中的一个条目关联起来
            if reloc_section == ".rela.plt":
                self.container.add_plt_information(relocations)

            # ssx: 如果目标节区已加载到容器中，将重定位信息添加进去, 例如.rela.text → .text 节区
            if section in self.container.sections:
                self.container.sections[section].add_relocations(relocations)
            # ssx: 如果目标节区未加载，仍然保存重定位信息,打印警告信息
            else:
                print("[*] Relocations for a section that's not loaded:" + str(reloc_section))
                self.container.add_relocations(section, relocations)

    '''
    (1)从 ELF 文件的重定位表和其关联的符号表中提取所有重定位条目
    (2)按节区组织成字典列表
    '''
    def reloc_list_from_symtab(self):
        relocs = defaultdict(list)

        #ssx:遍历重定位节区
        for section in self.elffile.iter_sections():
            if not isinstance(section, RelocationSection):
                continue

            # ssx: 获取关联的符号表(每个重定位节区通过 sh_link 字段指向对应的符号表)
            symtable = self.elffile.get_section(section['sh_link'])
            
            #ssx:处理每个重定位条目
            for rel in section.iter_relocations():
                symbol = None
                symbol_name = None
                is_section_symbol = False # Section symbol 不是“程序语义符号”，而是“链接器内部用来描述节区位置的锚点”
                #ssx:如果重定位有符号引用（r_info_sym ≠ 0），获取对应的符号
                if rel['r_info_sym'] != 0:
                    symbol = symtable.get_symbol(rel['r_info_sym'])

                # ssx:解析符号名称
                if symbol:
                    # ssx:无名符号 (st_name == 0): 使用所在节区的名称
                    if symbol['st_name'] == 0:
                        is_section_symbol = True
                        symsec = self.elffile.get_section(symbol['st_shndx'])
                        symbol_name = symsec.name if symsec else None
                    # ssx: 有名符号: 直接使用符号名称
                    else:
                        symbol_name = symbol.name
                # ssx:无符号重定位: 符号名称为 None
                else:
                    symbol = dict(st_value=None)
                    symbol_name = None

                reloc_type = ENUM_RELOC_TYPE_x64.get(
                    rel['r_info_type'], rel['r_info_type']
                )
                # ssx:构建重定位信息字典
                reloc_i = {
                    'section': section.name,
                    'offset': rel['r_offset'],
                    'addend': rel['r_addend'],
                    'type': reloc_type,              # 字符串类型
                    'name': symbol_name,
                    'st_value': symbol['st_value'],
                    'is_section_symbol': is_section_symbol,
                }

                relocs[section.name].append(reloc_i)

        return relocs

    # 从有符号表的二进制文件中提取函数信息
    def flist_from_symtab(self):
        # ssx:遍历所有section，找到符号表(pyelftools库中的SymbolTableSection,通常名为.symtab或.dynsym)
        symbol_tables = [
            sec for sec in self.elffile.iter_sections()
            if isinstance(sec, SymbolTableSection)
        ]

        function_list = dict()

        # ssx:遍历各个Symbol section
        # ssx: 各个Symbol section包括的内容
        '''ssx:
        section.name      # 节区名称，如 '.symtab'、'.dynsym'
        section.header    # 节区头信息
        section['sh_type'] # 节区类型
        section['sh_addr'] # 节区在内存中的地址
        section['sh_size'] # 节区大小
        section['sh_entsize'] # 每个条目的大小
        '''
        for section in symbol_tables:

            if not isinstance(section, SymbolTableSection):
                continue

            if section['sh_entsize'] == 0:
                continue

            # ssx:遍历符号表中的每个符号
            '''ssx:
            symbol.name                 # 符号名称
            symbol['st_name']          # 符号名称在字符串表中的索引
            symbol['st_value']         # 符号值（函数/变量地址）
            symbol['st_size']          # 符号大小（函数代码大小/变量大小）
            symbol['st_shndx']         # 符号所属节区索引
            symbol['st_info']['type']  # 符号类型：
                                        # 'STT_NOTYPE'   - 未指定类型
                                        # 'STT_OBJECT'   - 数据对象
                                        # 'STT_FUNC'     - 函数
                                        # 'STT_SECTION'  - 节区
                                        # 'STT_FILE'     - 文件名
                                        # 'STT_COMMON'   - 通用符号
                                        # 'STT_TLS'      - 线程局部存储

            symbol['st_info']['bind']  # 符号绑定：
                                        # 'STB_LOCAL'    - 局部符号
                                        # 'STB_GLOBAL'   - 全局符号  
                                        # 'STB_WEAK'     - 弱符号
            symbol['st_other']['visibility']  # 符号可见性：
                                                # 'STV_DEFAULT'   - 默认
                                                # 'STV_INTERNAL'  - 内部
                                                # 'STV_HIDDEN'    - 隐藏
                                                # 'STV_PROTECTED' - 受保护
            '''
            for symbol in section.iter_symbols():
                # ssx:这里不再跳过隐藏函数，.hidden 的真实含义是：链接可见性受限，而不是“不可执行 / 不是真函数”
                # if symbol['st_other']['visibility'] == "STV_HIDDEN":
                #     continue

                # ssx:筛选条件：类型为函数 (STT_FUNC)且不是未定义符号 (SHN_UNDEF)，即排除外部函数声明
                if (symbol['st_info']['type'] == 'STT_FUNC'
                        and symbol['st_shndx'] != 'SHN_UNDEF'):
                    function_list[symbol['st_value']] = {
                        'name': symbol.name,
                        'sz': symbol['st_size'],
                        'visibility': symbol['st_other']['visibility'],
                        'bind': symbol['st_info']['bind'],
                    }

        return function_list


    

    # 从没有符号表的二进制文件中提取函数信息（用angr的cfgfast）
    def flist_from_cfgfast(self):
        if self.is_pie() and self.is_stripped():
            base_addr = self.get_binaryfile_addr()
            proj = angr.Project(
                self.fname,
                auto_load_libs=False, # 避免加载 libc 等外部库
                load_options={"main_opts": {"base_addr": base_addr}} # 设置基地址
            )
        else:
            proj = angr.Project(
                self.fname,
                auto_load_libs=False # 避免加载 libc 等外部库
            )

        # 构建快速控制流图
        cfg = proj.analyses.CFGFast(
            normalize=True,         # 对基本块地址进行规范化处理
            data_references=True    # 分析数据引用关系
        )

        function_list = dict()

        for func in cfg.kb.functions.values():
            # 跳过 PLT / SimProcedure（可选）
            if func.is_plt or func.is_simprocedure:
                continue
            
            # 获取函数包含的所有基本块
            blocks = list(func.blocks)
            if not blocks:
                continue
            
            # 计算函数的覆盖地址范围
            start = min(b.addr for b in blocks)
            end = max(b.addr + b.size for b in blocks)
            size = end - start

            function_list[func.addr] = {
                'name': func.name,
                'sz': size,
                'visibility': None,
                'bind': None,
            }

        return function_list


    # ssx:提取节区的基本信息，包括基地址、大小、文件偏移和对齐方式
    def slist_from_elffile(self):
        sections = dict()
        for section in self.elffile.iter_sections():
            sections[section.name] = {
                'base': section['sh_addr'],
                'sz': section['sh_size'],
                'offset': section['sh_offset'],
                'align': section['sh_addralign'],
            }
        # print(f"LOADED SECTIONS: {list(sections.keys())}")
        return sections

    def load_globals_from_glist(self, glist):
        self.container.add_globals(glist)

    # ssx: 这里使用“全局”一词可能不太准确，实际上应该是“已定义的数据对象”
    '''
    (1)从符号表中提取全局数据符号（排除隐藏、零大小、未定义以及特定库符号）
    (2)并按符号地址组织成字典列表
    '''
    def global_data_list_from_symtab(self):
        symbol_tables = [
            sec for sec in self.elffile.iter_sections()
            if isinstance(sec, SymbolTableSection)
        ]

        global_list = defaultdict(list)

        for section in symbol_tables:
            if not isinstance(section, SymbolTableSection):
                continue

            if section['sh_entsize'] == 0:
                continue

            for symbol in section.iter_symbols():
                # XXX: HACK
                # ssx: 跳过 GLIBC 和 GLIBC++ 的版本化符号
                if "@@GLIBC" in symbol.name:
                    continue

                if "@GLIBCXX" in symbol.name:
                    continue

                # ssx: 排除隐藏符号和零大小符号
                if symbol['st_other']['visibility'] == "STV_HIDDEN":
                    continue
                if symbol['st_size'] == 0:
                    continue

                # ssx: 类型为数据对象 (STT_OBJECT)且不是未定义符号 (SHN_UNDEF)(排除外部变量声明)
                if (symbol['st_info']['type'] == 'STT_OBJECT'
                        and symbol['st_shndx'] != 'SHN_UNDEF'):
                    global_list[symbol['st_value']].append({
                        'name':
                        "{}_{:x}".format(symbol.name, symbol['st_value']), # ssx:符号名+地址，避免局部符号变成全局符号之后重名冲突
                        'sz':
                        symbol['st_size'],
                    })

        return global_list

    # ssx:收集动态符号表中已定义的全局数据对象(只处理动态符号表)
    def identify_imports(self):
        symbol_tables = [
            sec for sec in self.elffile.iter_sections()
            if isinstance(sec, SymbolTableSection)
        ]

        symmap = IntervalTree()

        for section in symbol_tables:
            if not isinstance(section, SymbolTableSection):
                continue

            if section.name != ".dynsym":
                continue

            for symbol in section.iter_symbols():
                if (symbol['st_info']['type'] == 'STT_OBJECT'
                    and symbol['st_shndx'] != 'SHN_UNDEF'):

                    start = symbol['st_value']
                    end = symbol['st_value'] + symbol['st_size']

                    symmap[start:end] = symbol.name

        self.container.imports = symmap
        # print("IDENTIFIED IMPORTS")
