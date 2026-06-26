from collections import defaultdict
import struct
import subprocess as sp

from capstone import CS_OP_IMM, CS_OP_MEM, CS_GRP_JUMP, CS_OP_REG
from . import disasm
from lib.consts import VALID_TARGET_SECTIONS
from elftools.elf.sections import SymbolTableSection


# 用于生成汇编文件时候的dump
# 在写汇编文件中的数据段的字节时判断前缀用什么
class SzPfx():
    PREFIXES = {
        1: '.byte',
        2: '.word',
        4: '.long',
        8: '.quad',
        16: '.xmmword',
    }

    @staticmethod
    def pfx(sz):
        return SzPfx.PREFIXES[sz]
    
class Container():
    def __init__(self):

        """
        初始化Container类的实例，用于存储和管理程序的各种组件信息。
        包括函数、节区、全局变量、重定位信息等。
        初始化节区字典，用于存储程序节区信息
        """
        self.functions = dict()
        self.function_names = set()
        self.sections = dict()  # 存储节区字典，键为节区名称
        self.globals = None
        self.relocations = defaultdict(list)    # 重定位信息，默认值为列表
        self.loader = None  # 加载器信息
        # Imports
        self.imports = None # 全局变量
        # PLT information
        self.plt_base = None
        self.plt = dict()

        self.gotplt_base = None
        self.gotplt_sz = None
        self.gotplt_entries = list()

        self.ins_map = {} # 指令映射表 addr -> instruction wrapper
        self.bases = set()  # 可作为 PC 相对计算锚点的段内基准地址集合

        # Dwarf information
        self.dwarf_info = dict()
        self.personality = None

    '''
    把创建的Function实例添加到Container中
    '''
    def add_function(self, function):
        if function.name in self.function_names:
            function.name = "%s_%x" % (function.name, function.start)
        self.functions[function.start] = function
        self.function_names.add(function.name)

        # Check for mangled names
        if function.name.startswith("_Z"):
            function.is_mangled = True

    def add_section(self, section):
        self.sections[section.name] = section

    def get_section(self, name):
        return self.loader.elffile.get_section_by_name(name)
    
    # 获取合法的 target_address 范围（用于 R1 证据）
    def get_valid_target_address(self):
        # 预定义指针大小和数据段（暂不扩展）
        MEMORY_MARGIN = 0x0000  # 1KB 扩展上下界
        # 构建有效地址范围（上下扩 4KB）
        addr_ranges = []
        for sec_name in VALID_TARGET_SECTIONS:
            section = self.get_section(sec_name)
            if section is None:
                continue
            start = max(0, section['sh_addr'] - MEMORY_MARGIN)
            end   = section['sh_addr'] + section['sh_size'] + MEMORY_MARGIN
            addr_ranges.append((start, end))
        return addr_ranges
    
    '''
    (1)保存全局符号表
    (2)遍历全局符号按地址匹配节区
    (3)去重和格式化符号名称
    (4)添加全局符号到节区
    '''
    def add_globals(self, globals):
        self.globals = globals
        done = set()

        for location, gobjs in globals.items():
            found = None
            for sec, section in self.sections.items():
                if section.base <= location < section.base + section.sz:
                    found = sec
                    break

            if not found:
                continue

            for gobj in gobjs:
                if gobj['name'] in done:
                    continue
                fixed_name = gobj["name"].replace("@", "_")
                self.sections[found].add_global(location, fixed_name,
                                                gobj['sz'])
                done.add(gobj['name'])


    # 符号表缓存构建
    def _build_symtab_cache(self, elffile):
        # 静态符号表
        self._symtab_cache = {}
        self._symtab_intervals = []
        # 动态符号表
        self._dynsym_obj_intervals = []

        for section in elffile.iter_sections():

            if not isinstance(section, SymbolTableSection):
                continue
            if section['sh_entsize'] == 0:
                continue
            
            is_dynsym = section.name == '.dynsym'

            for symbol in section.iter_symbols():
                stype = symbol['st_info']['type']
                # stbind = symbol['st_info']['bind']   # 获取绑定类型
                shndx = symbol['st_shndx']
                addr = symbol['st_value']
                size = symbol['st_size']
                name = symbol.name
                visibility = symbol['st_other']['visibility']

                # 忽略弱符号
                # if stbind == 'STB_WEAK':
                #     continue
                    
                # 跳过未定义符号(外部符号声明，但当前二进制里没有定义,不是已有内存地址)
                # 跳过没有地址的符号(文件符号 / 节区符号等不是程序对象的符号或占位/链接器生成的符号的st_value 通常为 0)
                if shndx == 'SHN_UNDEF' or addr == 0:
                    continue

                # 处理 .dynsym（全局变量）
                if is_dynsym:
                    if stype == 'STT_OBJECT' and size > 0:
                        start = addr
                        end = addr + size
                        self._dynsym_obj_intervals.append((start, end, name, visibility))
                    continue  # dynsym 不进入普通 symtab 逻辑

                # 处理 .symtab
                # 只关心可能“像地址”的符号('STT_SECTION','STT_FILE'段标识和文件标识无需符号化)
                if stype  not in ('STT_FUNC', 'STT_OBJECT', 'STT_NOTYPE'):
                    continue

                self._symtab_cache[addr] = (name, stype, size, section.name, visibility)
                # 构建符号区间缓存 [(start, end, name, type, section)] 用于区间匹配
                if stype == 'STT_OBJECT' and size > 0:
                        self._symtab_intervals.append((addr, addr + size, name, stype, section.name, visibility))

#     # ssx:要求在.plt.got地址范围内且立即值恰好等于某个条目的地址
#     def is_target_gotplt(self, target):
#         assert self.gotplt_base and self.gotplt_sz

#         if not (self.gotplt_base <= target <
#                 self.gotplt_base + self.gotplt_sz):
#             return False

#         for ent in self.gotplt_entries:
#             if ent.address == target:
#                 # 如果找到地址等于目标地址的条目，并且这个条目是跳转指令（CS_GRP_JUMP）且第一个操作数是内存类型（CS_OP_MEM），则计算并返回重定位地址
#                 if (CS_GRP_JUMP in ent.groups
#                         and ent.operands[0].type == CS_OP_MEM):
#                     return ent.operands[0].mem.disp + ent.address + ent.size

#         return False

    def attach_loader(self, loader):
        self.loader = loader

#     def is_in_section(self, secname, value):
#         assert self.loader, "No loader found!"

#         section = self.loader.elffile.get_section_by_name(secname)
#         base = section['sh_addr']
#         sz = section['sh_size']
#         if base <= value < base + sz:
#             return True
#         return False

    def add_relocations(self, section_name, relocations):
        self.relocations[section_name].extend(relocations)

#     def section_of_address(self, addr):
#         for _, section in self.sections.items():
#             if section.base <= addr < section.base + section.sz:
#                 return section
#         # XXX: This does not check for .text section
#         return None

#     # ssx: 符号化规则1：.text中出现在重定位表中的偏移量需要指向有效的内存的地址(函数)
#     def function_of_address(self, addr):
#         for _, function in self.functions.items():
#             if function.start <= addr < function.start + function.sz:
#                 return function
#         return None

    # ssx: 把 PLT 重定位条目映射到对应的 PLT 地址
    def add_plt_information(self, relocinfo):
        plt_base = self.plt_base
        for idx, relocation in enumerate(relocinfo, 1):
            self.plt[plt_base + idx * 16] = relocation['name']

#     def reloc(self, target):
#         assert self.loader, "No loader found!"
#         return "import"

    # 获取某地址所在的section
    def get_section_by_address(self, addr):
        for sec, section in self.sections.items():
            if section.base <= addr < section.base + section.sz:
                return sec
        return None
    
    # ssx:【自己新增方法】打印container
    def safe_detailed_container_serializer(obj):
        """安全的详细 Container 对象序列化器 - 完整版"""
        try:
            # Container 对象
            if isinstance(obj, Container):
                result = {
                    '__type__': 'Container',
                    'functions': {},
                    'function_names': [],
                    'sections': {},
                    'got_base': obj.got_base,
                    'got_sz': obj.got_sz,
                    'got_entries': {},
                    'plt_base': obj.plt_base,
                    'plt': obj.plt,
                    'gotplt_base': obj.gotplt_base,
                    'gotplt_sz': obj.gotplt_sz,
                    'gotplt_entries': [],
                    'relocations': {},
                    'global_relocations': {},
                    'globals': obj.globals,
                    'imports': None,
                    'dwarf_info': {},
                    'personality': obj.personality,
                    'loader_attached': obj.loader is not None
                }
                
                # 安全处理 function_names
                try:
                    result['function_names'] = list(obj.function_names) if obj.function_names else []
                except Exception as e:
                    result['function_names'] = f"<错误: {e}>"
                
                # 安全处理 functions
                try:
                    for func_start, function in obj.functions.items():
                        # control_flow中存在原Function定义的两个属性：
                        # bbstarts: 基本块的起始地址集合
                        # nexts: 一个字典，记录每个指令索引对应的下一个指令（或基本块）的地址
                        func_info = {
                            'name': getattr(function, 'name', 'unknown'),
                            'start': getattr(function, 'start', 0),
                            'size': getattr(function, 'sz', 0),
                            'bind': getattr(function, 'bind', 'unknown'),
                            'instrumented': getattr(function, 'instrumented', False),
                            'is_mangled': getattr(function, 'is_mangled', False),
                            'basic_blocks_count': len(getattr(function, 'bbstarts', set())),
                            'bytes_length': len(getattr(function, 'bytes', b'')),
                            'analysis': {},
                            'control_flow': {},
                            'exception_info': {},
                            'instructions_count': 0
                        }
                        
                        # 安全获取 true_name
                        try:
                            func_info['true_name'] = function.true_name if hasattr(function, 'true_name') else function.name
                        except:
                            func_info['true_name'] = function.name
                        
                        # 安全获取 analysis
                        try:
                            if hasattr(function, 'analysis') and function.analysis:
                                func_info['analysis'] = dict(function.analysis)
                        except:
                            func_info['analysis'] = {}
                        
                        # 安全获取控制流信息
                        try:
                            if hasattr(function, 'bbstarts') and function.bbstarts:
                                func_info['control_flow']['bbstarts'] = sorted(list(function.bbstarts))
                            if hasattr(function, 'nexts') and function.nexts:
                                # 转换 defaultdict 为普通 dict
                                nexts_dict = {}
                                for key, values in function.nexts.items():
                                    nexts_dict[str(key)] = [str(v) for v in values]
                                func_info['control_flow']['nexts'] = nexts_dict
                        except Exception as e:
                            func_info['control_flow'] = f"<控制流序列化错误: {e}>"
                        
                        # 安全获取异常处理信息
                        try:
                            if hasattr(function, 'except_table') and function.except_table:
                                func_info['exception_info']['except_table'] = str(function.except_table)
                            if hasattr(function, 'cfi_map') and function.cfi_map:
                                func_info['exception_info']['cfi_map'] = dict(function.cfi_map)
                        except Exception as e:
                            func_info['exception_info'] = f"<异常信息序列化错误: {e}>"
                        
                        # 安全获取指令信息
                        try:
                            if hasattr(function, 'cache') and function.cache:
                                func_info['instructions_count'] = len(function.cache)
                                instructions = []
                                instructions_str = []
                                for i, instr in enumerate(function.cache):
                                    instructions.append(instr)
                                    if hasattr(instr, '__str__'):
                                        instructions_str.append(str(instr))
                                func_info['instructions'] = instructions
                                func_info['instructions_str'] = instructions_str
                        except Exception as e:
                            func_info['instructions'] = f"<指令序列化错误: {e}>"
                        
                        result['functions'][hex(func_start)] = func_info
                except Exception as e:
                    result['functions'] = f"<处理functions错误: {e}>"
                
                # 安全处理 sections
                try:
                    for section_name, section in obj.sections.items():
                        section_info = {
                            'name': getattr(section, 'name', 'unknown'),
                            'base': getattr(section, 'base', 0),
                            'size': getattr(section, 'sz', 0),
                            'align': getattr(section, 'align', 16),
                            'bytes_length': len(getattr(section, 'bytes', b'')),
                            'relocations': [],
                            'globals': {},
                            'data_cells_count': 0
                        }
                        
                        # 安全处理节区重定位
                        try:
                            if hasattr(section, 'relocations'):
                                for reloc in section.relocations:
                                    if isinstance(reloc, dict):
                                        section_info['relocations'].append({
                                            'name': reloc.get('name'),
                                            'offset': reloc.get('offset'),
                                            'type': reloc.get('type')
                                        })
                        except Exception as e:
                            section_info['relocations'] = f"<错误: {e}>"
                        
                        # 安全处理节区全局变量
                        try:
                            if hasattr(section, 'named_globals'):
                                for location, globals_list in section.named_globals.items():
                                    section_info['globals'][hex(location)] = [
                                        {
                                            'label': g.get('label', 'unknown'),
                                            'size': g.get('sz', 0)
                                        } for g in globals_list
                                    ]
                        except Exception as e:
                            section_info['globals'] = f"<错误: {e}>"
                        
                        # 安全处理数据单元信息
                        try:
                            if hasattr(section, 'cache'):
                                section_info['data_cells_count'] = len(section.cache)
                                # 统计有效数据单元
                                valid_cells = 0
                                for cell in section.cache:
                                    if not getattr(cell, 'ignored', True):
                                        valid_cells += 1
                                section_info['valid_data_cells'] = valid_cells
                        except Exception as e:
                            section_info['data_cells'] = f"<错误: {e}>"
                        
                        result['sections'][section_name] = section_info
                except Exception as e:
                    result['sections'] = f"<处理sections错误: {e}>"
                
                # 安全处理 gotplt_entries
                try:
                    if obj.gotplt_entries:
                        for entry in obj.gotplt_entries:
                            entry_info = {
                                'address': getattr(entry, 'address', 0),
                                'mnemonic': getattr(entry, 'mnemonic', 'unknown'),
                                'op_str': getattr(entry, 'op_str', ''),
                            }
                            # 安全获取大小
                            if hasattr(entry, 'size'):
                                entry_info['size'] = entry.size
                            elif hasattr(entry, 'sz'):
                                entry_info['size'] = entry.sz
                            else:
                                entry_info['size'] = 'unknown'
                            
                            # 安全获取组信息
                            try:
                                if hasattr(entry, 'groups'):
                                    entry_info['groups'] = list(entry.groups) if entry.groups else []
                            except:
                                entry_info['groups'] = []
                                
                            # 安全获取操作数信息
                            try:
                                if hasattr(entry, 'operands'):
                                    operands_info = []
                                    for op in entry.operands:
                                        op_info = {'type': op.type}
                                        if hasattr(op, 'mem') and op.mem:
                                            op_info['mem'] = {
                                                'base': getattr(op.mem, 'base', 0),
                                                'index': getattr(op.mem, 'index', 0),
                                                'disp': getattr(op.mem, 'disp', 0),
                                                'scale': getattr(op.mem, 'scale', 1)
                                            }
                                        operands_info.append(op_info)
                                    entry_info['operands'] = operands_info
                            except:
                                entry_info['operands'] = []
                            
                            result['gotplt_entries'].append(entry_info)
                except Exception as e:
                    result['gotplt_entries'] = f"<处理gotplt_entries错误: {e}>"

                # 安全处理 got_entries
                try:
                    if obj.got_entries:
                        for entry in obj.got_entries:
                            entry_info = {
                                'address': obj.got_entries[0]['address'],
                                'symbol_name': obj.got_entries[0]['symbol_name'],
                            }

                            result['got_entries'][entry_info['address']] = entry_info
                except Exception as e:
                    result['got_entries'] = f"<处理got_entries错误: {e}>"

                # 安全处理重定位
                try:
                    for section_name, relocs in obj.relocations.items():
                        result['relocations'][section_name] = []
                        for reloc in relocs:
                            if isinstance(reloc, dict):
                                result['relocations'][section_name].append({
                                    'section': section_name,
                                    'name': reloc.get('name'),
                                    'st_value': reloc.get('st_value'),
                                    'offset': reloc.get('offset'),
                                    'addend': reloc.get('addend'),
                                    'type': reloc.get('type'),
                                    'is_section_symbol': reloc.get('is_section_symbol'),
                                })
                            else:
                                # 尝试序列化非字典的重定位对象
                                result['relocations'][section_name].append({
                                    '__str__': str(reloc),
                                    '__type__': type(reloc).__name__
                                })
                    
                    # 全局重定位统计
                    for section_name, relocs in obj.relocations.items():
                        result['global_relocations'][section_name] = len(relocs)
                except Exception as e:
                    result['relocations'] = f"<处理重定位错误: {e}>"
                    result['global_relocations'] = f"<处理重定位错误: {e}>"
                
                # 安全处理 imports
                try:
                    if obj.imports:
                        result['imports'] = {
                            '__type__': 'IntervalTree',
                            'interval_count': len(obj.imports),
                            'intervals': []
                        }
                        for interval in obj.imports:
                            result['imports']['intervals'].append({
                                'begin': interval.begin,
                                'end': interval.end,
                                'data': str(interval.data) if interval.data else None
                            })
                except Exception as e:
                    result['imports'] = f"<处理imports错误: {e}>"
                
                # 安全处理 dwarf_info
                try:
                    if hasattr(obj, 'dwarf_info') and obj.dwarf_info:
                        result['dwarf_info'] = dict(obj.dwarf_info)
                except Exception as e:
                    result['dwarf_info'] = f"<处理dwarf_info错误: {e}>"
                
                return result
            
            # Function 对象
            elif isinstance(obj, Function):
                func_info = {
                    '__type__': 'Function',
                    'name': obj.name,
                    'start': obj.start,
                    'size': obj.sz,
                    'bind': obj.bind,
                    'instrumented': obj.instrumented,
                    'is_mangled': obj.is_mangled,
                    'bytes_length': len(obj.bytes) if hasattr(obj, 'bytes') else 0,
                    'basic_blocks': sorted(list(obj.bbstarts)) if hasattr(obj, 'bbstarts') else [],
                    'analysis': dict(obj.analysis) if hasattr(obj, 'analysis') and obj.analysis else {},
                    'instructions_count': len(obj.cache) if hasattr(obj, 'cache') else 0
                }
                
                # 安全获取 true_name
                try:
                    func_info['true_name'] = obj.true_name
                except:
                    func_info['true_name'] = obj.name
                
                # 安全获取控制流信息
                try:
                    if hasattr(obj, 'nexts') and obj.nexts:
                        nexts_dict = {}
                        for key, values in obj.nexts.items():
                            nexts_dict[str(key)] = [str(v) for v in values]
                        func_info['control_flow'] = nexts_dict
                except Exception as e:
                    func_info['control_flow'] = f"<错误: {e}>"
                
                # 安全获取异常信息
                try:
                    if hasattr(obj, 'except_table') and obj.except_table:
                        func_info['except_table'] = str(obj.except_table)
                    if hasattr(obj, 'cfi_map') and obj.cfi_map:
                        func_info['cfi_map'] = dict(obj.cfi_map)
                except Exception as e:
                    func_info['exception_info'] = f"<错误: {e}>"
                
                return func_info
            
            # DataSection 对象
            elif isinstance(obj, DataSection):
                section_info = {
                    '__type__': 'DataSection',
                    'name': obj.name,
                    'base': obj.base,
                    'sz': obj.sz,
                    'align': obj.align,
                    'bytes_length': len(obj.bytes) if hasattr(obj, 'bytes') else 0,
                    'data_cells_count': len(obj.cache) if hasattr(obj, 'cache') else 0,
                    'relocations_count': len(obj.relocations) if hasattr(obj, 'relocations') else 0,
                    'globals_count': len(obj.named_globals) if hasattr(obj, 'named_globals') else 0
                }
                
                # 安全处理全局变量
                try:
                    if hasattr(obj, 'named_globals'):
                        globals_info = {}
                        for location, globals_list in obj.named_globals.items():
                            globals_info[hex(location)] = [
                                {'label': g.get('label', 'unknown'), 'size': g.get('sz', 0)} 
                                for g in globals_list
                            ]
                        section_info['globals'] = globals_info
                except Exception as e:
                    section_info['globals'] = f"<错误: {e}>"
                
                return section_info
            
            # InstructionWrapper 对象
            elif isinstance(obj, InstructionWrapper):
                instr_info = {
                    '__type__': 'InstructionWrapper',
                    'address': obj.address,
                    'mnemonic': obj.mnemonic,
                    'op_str': obj.op_str,
                    'size': obj.sz,
                    'before_instr_count': len(obj.before) if hasattr(obj, 'before') else 0,
                    'after_instr_count': len(obj.after) if hasattr(obj, 'after') else 0
                }
                
                # 安全获取寄存器访问信息
                try:
                    if hasattr(obj, 'reg_reads'):
                        instr_info['reg_reads'] = obj.reg_reads()
                    if hasattr(obj, 'reg_writes'):
                        instr_info['reg_writes'] = obj.reg_writes()
                    if hasattr(obj, 'cf_leaves_fn'):
                        instr_info['cf_leaves_fn'] = obj.cf_leaves_fn
                except Exception as e:
                    instr_info['register_info'] = f"<错误: {e}>"
                
                return instr_info
            
            # DataCell 对象
            elif isinstance(obj, DataCell):
                cell_info = {
                    '__type__': 'DataCell',
                    'value': obj.value,
                    'size': obj.sz,
                    'ignored': obj.ignored,
                    'is_instrumented': obj.is_instrumented,
                    'before_instr_count': len(obj.before) if hasattr(obj, 'before') else 0,
                    'after_instr_count': len(obj.after) if hasattr(obj, 'after') else 0
                }
                return cell_info
            
            # 其他对象类型简单处理
            elif hasattr(obj, '__dict__'):
                return {
                    '__type__': type(obj).__name__,
                    '__str__': str(obj),
                    '__dict__': {k: v for k, v in obj.__dict__.items() 
                            if not k.startswith('_') and not callable(v)}
                }
            
            # 默认情况
            return obj
        
        except Exception as e:
            return f"<序列化错误: {e}>"


class Function():
    def __init__(self, name, start, sz, bytes, bind="STB_LOCAL"):
        self.name = name
        self.cache = list()
        self.start = start
        self.sz = sz
        self.bytes = bytes
        self.bbstarts = set()
        self.bind = bind

        self.except_table = None
        self.cfi_map = None

        # Populated during symbolization.
        # Invalidated by any instrumentation.
        self.nexts = defaultdict(list)

        self.bbstarts.add(start)

        # Dict to save function analysis results
        self.analysis = defaultdict(lambda: None)

        # Is this an instrumented function?
        self.instrumented = False

        self.is_mangled = False
        self._true_name = None

    # asan插桩使用
    def set_instrumented(self):
        self.instrumented = True
    
#     @property
#     def true_name(self):
#         if self.is_mangled and not self._true_name:
#             call = sp.check_output("c++filt " + self.name, shell=True)
#             call = call.strip().decode('utf-8')
#             self._true_name = call
#             return call
#         elif self._true_name:
#             return self._true_name
#         return self.name


    def disasm(self, container):
        assert not self.cache
        for decoded in disasm.disasm_bytes(self.bytes, self.start):
            inst  = InstructionWrapper(decoded)
            self.cache.append(inst)
            container.ins_map[inst.address] = inst
     
    # 验证是否是指令的起始地址
    def is_valid_instruction(self, address):
        assert self.cache, "Function not disassembled!"

        for instruction in self.cache:
            if instruction.address == address:
                return True

        return False

#     # ssx: 符号化规则2：.text中出现在重定位表中的偏移量需要指向有效的内存地址(指令)
#     def instruction_of_address(self, address):
#         assert self.cache, "Function not disassembled!"

#         for instruction in self.cache:
#             if instruction.address <= address < instruction.address + instruction.sz:
#                 return instruction

#         return None

    # 用于生成汇编文件时候的dump
    def __str__(self):
        assert self.cache, "Function not disassembled!"

        results = []
        # Put all function names and define them.
        results.append("\t.align 2")        # 进一步保证函数入口对齐
        results.append("\t.p2align 4,,15")  # 进一步保证函数入口对齐
        if self.bind == "STB_GLOBAL":
            results.append("\t.globl %s" % (self.name)) # 声明函数为全局可见
        else:
            results.append("\t.local %s" % (self.name)) # 声明函数为局部可见
        results.append("\t.type %s, @function" % (self.name))   # 告诉链接器 main 是函数类型
        results.append("%s:" % (self.name))

        # Add .cfi_startproc directive
        results.append("\t.cfi_startproc")  # 表示函数开始
        # Add GCC except table, lsda information
        if self.except_table:
            results.append("\t.cfi_personality 155, DW.ref.__gxx_personality_v0")
            results.append("\t.cfi_lsda 0x1b,.LLSDA%x" % (self.start))

        current_offset = 0x0

        ret_prepend = ""

        for instruction in self.cache:
            # asan插桩使用
            if isinstance(instruction, InstrumentedInstruction):
                if not self.instrumented:
                    print("[x] Old style instrumentation detected:", self.name)
                results.append("%s" % (instruction))
                continue

            # 为每条指令生成局部标签 .LCxxxx;如果是基本块起始，还生成 .Lxxxx 基本块标签。
            if instruction.address in self.bbstarts:
                results.append(".L%x:" % (instruction.address))
                results.append(".LC%x:" % (instruction.address))
            else:
                results.append(".LC%x:" % (instruction.address))

            # 插入指令前的辅助指令（可能是调试或插桩代码）
            for iinstr in instruction.before:
                results.append("{}".format(iinstr))

            # 如果指令是 ret，可能需要插入 CFI 指令 保存栈帧信息。
            if instruction.mnemonic.startswith("ret"):
                results.append(ret_prepend)
            results.append(
                "\t%s %s" % (instruction.mnemonic, instruction.op_str)) # 输出反汇编指令

            current_offset += instruction.sz    # 更新函数当前偏移量，用于处理 CFI 表

            # 每条指令可能对应 CFI 信息（保存栈指针变化）
            if self.cfi_map:
                for cfi in self.cfi_map[current_offset]:
                    if ".cfi_def_cfa " in cfi:
                        ret_prepend = cfi
                    else:
                        results.append(cfi)

            # 指令后辅助操作或插桩代码
            for iinstr in instruction.after:
                results.append("{}".format(iinstr))

        # Add .cfi_endproc directive
        results.append("\t.cfi_endproc")    # 表示函数结束

        # 如果有异常表（C++ 异常处理表），加入
        if self.except_table:
            results.append(self.except_table)
            results.append("\t.text")

        results.append("\t.size %s,.-%s" % (self.name, self.name))  # 函数大小，告诉链接器这个函数占用多少字节

        return "\n".join(results)

    def next_of(self, instruction_idx):
        nexts = list()
        for x in self.nexts[instruction_idx]:
            if isinstance(x, str):
                nexts.append(x)
            else:
                nexts.append(x)
        return nexts


class InstructionWrapper():
    def __init__(self, instruction):
        self.cs = instruction
        self.address = instruction.address
        self.mnemonic = instruction.mnemonic
        self.op_str = instruction.op_str
        self.sz = instruction.size

        # Instrumentation cache for this instruction
        self.before = list()
        self.after = list()

        # CF Leaves function?
        self.cf_leaves_fn = None

    # 用于可视化输出到container.json文件中
    def __str__(self):
        return "%x: %s %s" % (self.address, self.mnemonic, self.op_str)

    # asan插桩使用
    def get_mem_access_op(self):
        for idx, op in enumerate(self.cs.operands):
            # ssx:CS_OP_MEM 是 Capstone 反汇编引擎定义的常量，表示内存操作数类型
            if op.type == CS_OP_MEM:
                return (op.mem, idx)
        return (None, None)

    # asan插桩使用
    def reg_reads(self):
        # Handle nop
        if self.mnemonic.startswith("nop"):
            return []
        regs = self.cs.regs_access()[0]
        return [self.cs.reg_name(x) for x in regs]

    # asan插桩使用
    def reg_writes(self):
        # Handle nop
        if self.mnemonic.startswith("nop"):
            return []
        regs = self.cs.regs_access()[1]
        return [self.cs.reg_name(x) for x in regs]

    # asan插桩使用
    def instrument_before(self, iinstr, order=None):
        if order:
            self.before.insert(order, iinstr)
        else:
            self.before.append(iinstr)

    # asan插桩使用
    def instrument_after(self, iinstr, order=None):
        if order:
            self.after.insert(order, iinstr)
        else:
            self.after.append(iinstr)
        
    # def __str__(self):
    #     return "ImmediateCandidate(address=0x%x, value=0x%x, sz=%d)" % (
    #         self.address, self.value, self.sz)

# asan插桩使用
class InstrumentedInstruction():
    def __init__(self, code, label=None, forinst=None):
        self.code = code
        self.label = label
        self.forinst = forinst

    def __str__(self):
        if self.label:
            return "%s: # %s\n\t%s" % (self.label, self.forinst, self.code)
        else:
            return "%s" % (self.code)


class DataSection():
    def __init__(self, name, base, sz, bytes, align=16):
        self.name = name
        self.cache = list()
        self.base = base
        self.sz = sz
        self.bytes = bytes
        self.relocations = list()
        self.align = align
        self.named_globals = defaultdict(list)

    # ssx: 把节区的字节数据加载到缓存中，每个字节作为一个DataCell对象存储 
    def load(self):
        assert not self.cache
        # retrowrite对每一个字节都建模了
        for byte in self.bytes:
            self.cache.append(DataCell(byte, 1))

    def add_relocations(self, relocations):
        self.relocations.extend(relocations)

    def add_global(self, location, label, sz):
        self.named_globals[location].append({
            'label': label,
            'sz': sz,
        })

    # 尝试从指定虚拟地址读取 sz 个字节，并把它们按小端解析成一个整数（这里固定解成 32 位无符号整数）
    def read_at(self, address, sz):
        cacheoff = address - self.base
        if any([
                not isinstance(x.value, int)
                for x in self.cache[cacheoff:cacheoff + sz]
        ]):
            return None

        bytes_read = [x.value for x in self.cache[cacheoff:cacheoff + sz]]
        bytes_read_padded = bytes_read + [0]*(sz - len(bytes_read))

        value = struct.unpack("<I", bytes(bytes_read_padded))[0]

        return value

    # 用于将原来的数据替换成生成的符号, 符号化时使用
    def replace(self, address, sz, value):
        cacheoff = address - self.base

        if cacheoff >= len(self.cache):
            print("[x] Could not replace value in {}".format(self.name))
            return

        self.cache[cacheoff].value = value
        self.cache[cacheoff].sz = sz

        for cell in self.cache[cacheoff + 1:cacheoff + sz]:
            cell.set_ignored()

#     def iter_cells(self):
#         location = self.base
#         for cidx, cell in enumerate(self.cache):
#             if cell.ignored or cell.is_instrumented:
#                 continue
#             yield cidx, location, cell
#             location = location + cell.sz

    '''
    # 用于生成汇编文件时候的dump
    # 核心就是对每个数据类段中的每个从符号表中得到的全局符号的每个字节生成一个标签，并标明全局符号
    '''
    def __str__(self):
        if not self.cache:
            return ""

        results = []
        results.append(".section {}".format(self.name))

        if self.name != ".fini_array":
            results.append(".align {}".format(self.align))

        location = self.base
        valid_cells = False

        # 这里处理的是每一个字节，retrowrite对每一个字节都建模了DataCell
        for cell in self.cache:
            if cell.ignored:
                continue

            valid_cells = True

            if cell.is_instrumented:
                results.append("\t%s" % (cell))
                continue
            
            # 符号表中为STT_OBJECT类型的变量作为全局符号
            if location in self.named_globals:
                for gobj in self.named_globals[location]:
                    symdef = ".type\t{name},@object\n.globl {name}".format(
                        name=gobj["label"])
                    lblstr = "{}: # {:x} -- {:x}".format(
                        gobj["label"], location, location + gobj["sz"])

                    results.append(symdef)
                    results.append(lblstr)

            results.append(".LC%x:" % (location))
            location += cell.sz

            for before in cell.before:
                results.append("\t%s" % (before))

            if self.name == '.bss':
                cell.value = 0
            results.append("\t%s" % (cell))

            for after in cell.after:
                results.append("\t%s" % (after))

        if valid_cells:
            return "\n".join(results)
        else:
            return ""


class DataCell():
    def __init__(self, value, sz):
        self.value = value
        self.sz = sz
        self.ignored = False
        self.is_instrumented = False

        # Instrumentation
        self.before = list()
        self.after = list()

    # asan插桩使用
    @staticmethod
    def instrumented(value, sz):
        dc = DataCell(value, sz)
        dc.is_instrumented = True

        return dc

    # 符号化过程用符号代替原有数据段的数据时，对Cell进行了初始化设置
    def set_ignored(self):
        self.ignored = True

    # 用于生成汇编文件时候的dump
    def __str__(self):
        if not self.ignored:
            if self.is_instrumented:
                return self.value
            if isinstance(self.value, int):
                return "%s 0x%x" % (SzPfx.pfx(self.sz), self.value)
            return "%s %s" % (SzPfx.pfx(self.sz), self.value)
        else:
            return ""

    # asan插桩使用
    def instrument_before(self, idata):
        assert idata.is_instrumented

        self.before.append(idata)

    # asan插桩使用
    def instrument_after(self, idata):
        assert idata.is_instrumented

        self.after.append(idata)
