import argparse
import sys
import io
import struct
from collections import defaultdict
from collections import OrderedDict

from capstone import CS_OP_IMM, CS_GRP_JUMP, CS_GRP_CALL, CS_OP_MEM
from capstone.x86_const import X86_REG_RIP

from elftools.elf.descriptions import describe_reloc_type
from elftools.elf.enums import ENUM_RELOC_TYPE_x64
from elftools.elf.sections import SymbolTableSection
from elftools.dwarf.callframe import FDE, CIE, ZERO
from elftools.dwarf.constants import *
from elftools.dwarf.enums import *
from elftools.dwarf.structs import DWARFStructs
from elftools.common.utils import struct_parse
from elftools.construct import Struct
from lib.consts import GCC_FUNCTIONS, DATASECTIONS

class AssemblyRewriter:
    def __init__(self, container):
        self.container = container
    
    def dump(self, outfile):
        results = list()
        # 按基地址排序，打印所有的DataSection
        for sec, section in sorted(
                self.container.sections.items(), key=lambda x: x[1].base):
            results.append("%s" % (section))
        
        results.append(".section .text")    # 添加.text节的起始声明
        results.append(".align 16") # # 添加.text节的起始声明
        results.append(".section .note.GNU-stack,\"\",%progbits")   # 添加GNU栈属性声明（标记栈不可执行）

        # 遍历所有函数，按地址排序
        for _, function in sorted(self.container.functions.items()):
            """
            if function.name == "frame_dummy":
                results.append("\t.extern frame_dummy\n")
                continue
            """
            # 跳过GCC内置函数（如_start、__libc_csu_init等）
            if function.name in GCC_FUNCTIONS:
                continue
            # 添加.text节声明和函数的汇编代码
            results.append("\t.text\n%s" % (function))

        # 如果容器中有异常处理personality函数定义，添加到输出
        if self.container.personality:
            results.append(self.container.personality)       

        # 将所有结果写入输出文件
        with open(outfile, 'w') as outfd:
            outfd.write("\n".join(results + ['']))



class Rewriter():
   
    def __init__(self, container, outfile, eh_frame=False, lang_cpp=False):
        self.eh_frame = eh_frame # ssx: 布尔值，指示是否处理异常帧
        # TODO: generic if we need different techniques for different languages.
        self.lang_cpp = lang_cpp # ssx:布尔值，指示是否处理C++语言相关的特性
        self.container = container # ssx: 一个容器对象，包含节区和函数等信息
        self.outfile = outfile # ssx:输出文件
