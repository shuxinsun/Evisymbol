import capstone
import re
import os

from reassessor.lib.parser import parse_intel_asm_line, DATA_DIRECTIVE, SKIP_DIRECTIVE, ReasmInst, ReasmData, ReasmLabel, ReasmSetLabel, parse_set_directive
from .tool_base import NormalizeTool

SYM_BLK = ['__rela_iplt_end']

def ddisasm_label_to_addr(label):
    # '.L_587dd0@GOTPCREL'
    label = label.split('@')[0]
    if label.startswith('FUN_'):
        addr = int(label[4:],16)
    elif label.startswith('.L_'):
        if label.endswith('_END'):
            addr = int(label[3:-4], 16)
        else:
            addr = int(label[3:], 16)
    else:
        addr = 0

    return addr



class NormalizeDdisasm(NormalizeTool):
    def __init__(self, bin_path, reassem_path, supplement_file=''):
        super().__init__(bin_path, reassem_path, ddisasm_mapper, capstone.CS_OPT_SYNTAX_INTEL, supplement_file=supplement_file)

def ddisasm_mapper(reassem_path, tokenizer, supplement_file):
    result = [] # 存放解析结果，包括 ReasmLabel、ReasmSetLabel 或指令/数据条目
    addr = -1    # 当前正在处理的指令/数据地址
    is_linker_gen = False  # 标记当前行是否属于链接器生成（非用户代码）内容

    asm_file = os.path.basename(reassem_path)

     # 打开反汇编生成的汇编文件
    with open(reassem_path) as f:
        unknown_label_idx = -1
        for idx, line in enumerate(f):
            terms = line.split('#')[0].split()  # 去掉注释 '#'，按空格分割
            if len(terms) == 0:
                continue

            if terms[0] in ['.align', '.globl', '.hidden', '.weak', '.intel_syntax', '.type', 'nop']:
                pass  # 这些伪指令不生成标签或立即值，跳过
            elif terms[0].startswith('.cfi_'):
                pass  # 调试帧指令，跳过
            elif terms[0] in ['.section']:  # 切换段，可能是链接器生成段
                # Ddisam 1.5.3 sometimes does not create section name
                # .section
                # 416.gamess and 434.zeusmp
                # Ddisasm 1.5.3 有时不会生成段名，处理特殊情况
                if '416.gamess' in reassem_path or '434.zeusmp' in reassem_path:
                    is_linker_gen = False
                elif len(terms) > 1 and terms[1] not in ['.fini', '.init', '.plt.got']:
                    is_linker_gen = False
                else:
                    is_linker_gen = True
            elif terms[0] in ['.text', '.data', '.bss']:
                is_linker_gen = False
            elif terms[0] in ['.set']:
                # ex) .set FUN_804a3f0, . - 10
                # ex) .set L_0, 0
                label_addr, num = parse_set_directive(line, ddisasm_label_to_addr)
                result.append(ReasmSetLabel(terms[1][:-1], label_addr, num, idx+1))
            elif re.search('^.*:$', line):
                xaddr = ddisasm_label_to_addr(terms[0][:-1])
                if xaddr > 0:
                    addr = xaddr
                    if unknown_label_idx + 1 == idx and isinstance(result[-1], ReasmLabel):
                        prev_label, _, prev_idx = result[-1]
                        assert prev_idx == unknown_label_idx + 1
                        result[-1] = ReasmLabel(prev_label, addr, prev_idx)
                if addr > 0:
                    result.append(ReasmLabel(terms[0][:-1], addr, idx+1))
                else:
                    result.append(ReasmLabel(terms[0][:-1], 0, idx+1))
                    unknown_label_idx = idx

                continue
            elif is_linker_gen or terms[0] in SKIP_DIRECTIVE:
                continue
            elif terms[0].startswith('.'):
                pass
            elif terms[0] in ['nop']:
                pass
            else:
                addr = int(re.search('^([0-9a-f]*)', terms[0][:-1])[0],16)
                if unknown_label_idx + 1 == idx and isinstance(result[-1], ReasmLabel):
                    prev_label, _, prev_idx = result[-1]
                    assert prev_idx == unknown_label_idx + 1
                    result[-1] = ReasmLabel(prev_label, addr, prev_idx)
                if terms[1] in DATA_DIRECTIVE:
                    if terms[1] in ['.long', '.quad']:
                        expr = ''.join(terms[2:])
                        #if re.search('.[+|-]', expr):
                        if [term for term in re.split('[+|-]', expr) if re.match('[._a-zA-Z]', term) ]:
                            result.append(tokenizer.parse_data(terms[1] + ' ' + expr, addr, idx+1))
                else:
                    asm_line = ' '.join(terms[1:])
                    result.append(tokenizer.parse(asm_line, addr, idx+1))

            addr = -1
    #ddisasm debug option has some bugs so we store label to additional assembly files
    if supplement_file and os.path.isfile(supplement_file):
        with open(supplement_file) as f:
            for line in f:
                if re.search('^.*:$', line):
                    terms = line.split('#')[0].split()
                    xaddr = ddisasm_label_to_addr(terms[0][:-1])
                    if xaddr > 0:
                        result.append(ReasmLabel(terms[0][:-1], xaddr, 0))
   
    return result


import argparse
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='normalize_ddisasm')
    parser.add_argument('bin_path', type=str)
    parser.add_argument('reassem_path', type=str)
    parser.add_argument('save_file', type=str)
    args = parser.parse_args()

    ddisasm = NormalizeDdisasm(args.bin_path, args.reassem_path)
    ddisasm.normalize_inst()
    ddisasm.normalize_data()
    ddisasm.save(args.save_file)

