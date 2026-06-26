from capstone import *

def disasm_bytes(bytes, addr):
    # ssx:初始化 Capstone 引擎
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    #ssx:Capstone默认使用Intel语法，改为ATT语法。
    #ssx:ATT语法常见于GNU工具链（如gdb、objdump等）
    md.syntax = 2 # CS_OPT_SYNTAX_ATT
    #ssx:每条指令的详细信息会被填充
    md.detail = True
    '''
    这个函数返回一个Capstone指令对象的列表，每个对象包含如下字段（仅列常用）：
    address: 指令地址
    mnemonic: 指令助记符
    op_str: 操作数字符串
    operands: 操作数列表（需要md.detail=True）
    regs_read: 读取的寄存器列表（需要md.detail=True）
    regs_written: 写入的寄存器列表（需要md.detail=True）
    '''
    return list(md.disasm(bytes, addr))
