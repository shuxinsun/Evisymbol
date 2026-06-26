import pickle
import os
import json

'''
输出释义
"4499": {
    "addr": 4499, // 指令在内存或二进制中的地址
    "path": "/home/ssx/Desktop/myProject/demos/swtich_demo/asm/hello.s", // 汇编文件路径
    "asm_token": [
        "movl bar+8(%rip), %eax", // 整条汇编指令文本
        "movl",                   // 操作码（opcode）
        [
            "bar+8(%rip)",        // 操作数 1
            "%eax"                // 操作数 2
        ],
        50                        // 指令在 asm 文件中的索引（行号）
    ],
    "asm_line": "movl bar+8(%rip), %eax", // 汇编指令原始文本
    "asm_idx": 50,                         // 指令索引
    "imm": null,                           // 立即数（immediate operand），此条指令没有
    "disp": {                              // 位移/偏移量操作数信息
        "labels": [
            "bar"                          // 涉及的符号名
        ],
        "num": 8,                           // 数值偏移
        "value": 8232,                      // 计算后的目标地址值
        "is_pcrel": true,                   // 是否是 PC-relative 寻址
        "terms": [
            {
                "Address": 8224,           // 存储的是符号所代表的地址
                "Name": "bar",             // 符号名
                "Ty": 2,                   // 符号类型（这里 Ty=2，对应 Absolute+Composite）
                "Num": 0                   // 内部序号
            },
            8                              // 偏移量
        ],
        "type": 4                           // 符号化类型（4 = PCRelative + Composite）
    }
}

compare_two_reloc_expr函数
# 计算type方式
    gt_reloc_type = gt_reloc.type
# 计算目标地址方式
if gt_reloc.terms[0].Address > 0:
                
        gt_target_label = gt_reloc.terms[0].Address + gt_reloc.num
    else:
        gt_target_label = gt_reloc.num
# 计算符号本身的value值
gt_reloc.terms[0].Address
'''

PROJECT_ROOT = os.environ.get("PROJECT_ROOT")
if PROJECT_ROOT is None:
    raise RuntimeError("PROJECT_ROOT environment variable is not set")

# 将reasessor对指令建模后的序列化gt转换为可读的字典
def gt_load(file_path):
    with open(file_path, 'rb') as f:
        loaded_object = pickle.load(f)
    dict = vars(loaded_object)
    # dict_keys(['Instrs', 'Data', 'asm_path', 'text_base', 'text_data', 'relocs', 'sections', 'unknown_region', 'aligned_region'])
    gt_load_object_dict = {}
    gt_Instrs_dict = {}
    gt_Datas_dict = {}
    gt_asm_path_dict = {}
    gt_text_base_dict = {}
    gt_text_data_dict = {}
    gt_relocs_dict = {}
    gt_sections_dict = {}
    gt_unknown_region_dict = {}
    gt_aligned_region_dict = {}
    # print(str(dict.keys())) 
    for gt_key in dict.keys():
        if gt_key == 'Instrs':
            # Instrs_key is key of instruction list
            for Instrs_key in dict[gt_key].keys():
                gt_Instrs_dict[Instrs_key] = {}
                # print(dict[gt_key][Instrs_key])
                # Instr_key is key of a instruction
                Instr_object = vars(dict[gt_key][Instrs_key])
                # {'addr': 4636, 'path': '/home/ssx/Desktop/reassessor/example/asm/hello.s', 'asm_token': AsmInst(asm_line='retq ', opcode='retq', operand_list=[], idx=144), 'asm_line': 'retq ', 'asm_idx': 144, 'imm': None, 'disp': None}
                # print(Instr_object)
                for Instr_key in Instr_object.keys():
                    # The keys started with '__' are useless normally.
                    if Instr_key.startswith('_'):
                        continue
                    # the value of key 'imm' and 'disp' are lists, and the other's is a concrete value
                    if Instr_key == 'imm' or Instr_key == 'disp':
                        # dir(Instr_object['imm']) = ['__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', '_label_dict', '_label_func', '_set_label_dict', 'get_ddisasm_got_terms', 'get_norm_str', 'get_str', 'get_table_terms', 'get_terms', 'get_type', 'has_label', 'is_composite', 'is_pcrel', 'is_set_label', 'label_to_addr', 'labels', 'num', 'terms', 'type', 'value']
                        if Instr_object[Instr_key]:
                            gt_Instrs_dict[Instrs_key][Instr_key] = {}
                            for label_key in vars(Instr_object[Instr_key]).keys():
                                # print(vars(Instr_object[Instr_key])['terms'])
                                # The keys started with '__' are useless normally.
                                if label_key.startswith('_'):
                                        continue
                                # terms need to be vars()
                                if label_key == 'terms':
                                    # print(vars(Instr_object[Instr_key])[label_key])
                                    # the value of key 'terms' may be 'None' or term list
                                    if len(vars(Instr_object[Instr_key])[label_key]) != 0:
                                        gt_Instrs_dict[Instrs_key][Instr_key][label_key] = []
                                        term_list = []
                                        for term in vars(Instr_object[Instr_key])[label_key]:
                                            # There are two cases, including [<reassessor.lib.types.Label object at 0x7f7108488550>] and [<reassessor.lib.types.Label object at 0x7f7108488640>, 8]
                                            try:
                                                term_list.append(vars(term))
                                                # 'Ty': <LblTy.LABEL: 2> require processing
                                                # print(vars(term)['Ty'].value)
                                                term_list[-1]['Ty'] = vars(term)['Ty'].value
                                            except Exception as e:
                                                term_list.append(term)
                                        gt_Instrs_dict[Instrs_key][Instr_key][label_key] = term_list    
                                    else:
                                        gt_Instrs_dict[Instrs_key][Instr_key][label_key] = vars(Instr_object[Instr_key])[label_key]
                                else:
                                    gt_Instrs_dict[Instrs_key][Instr_key][label_key] = vars(Instr_object[Instr_key])[label_key]
                                # gt_Instrs_dict[Instrs_key][Instr_key][key] = vars(Instr_object[Instr_key])[key]
                        else:
                            gt_Instrs_dict[Instrs_key][Instr_key] = Instr_object[Instr_key]
                    else:
                        gt_Instrs_dict[Instrs_key][Instr_key] = Instr_object[Instr_key]
                
                    # print(Instr_object[Instr_key])
        elif gt_key == 'Data':
            for Datas_key in dict[gt_key].keys():
                gt_Datas_dict[Datas_key] = {}
                Data_object = vars(dict[gt_key][Datas_key])
                for Data_key in Data_object.keys():
                    gt_Datas_dict[Datas_key][Data_key] = {}
                    # The keys started with '__' are useless normally.
                    if Data_key.startswith('_'):
                            continue
                    # value need to be vars()
                    if Data_key == 'value':
                        label_object = vars(Data_object[Data_key])
                        for label_key in label_object.keys():
                            # The keys started with '__' are useless normally.
                            if label_key.startswith('_'):
                                    continue
                            # terms need to be vars()
                            if label_key == 'terms':
                                gt_Datas_dict[Datas_key][Data_key][label_key] = []
                                term_list = []
                                for term in label_object[label_key]:
                                    try:
                                        term_list.append(vars(term))
                                        # 'Ty': <LblTy.LABEL: 2> require processing
                                        # print(vars(term)['Ty'].value)
                                        term_list[-1]['Ty'] = vars(term)['Ty'].value
                                    except Exception as e:
                                        term_list.append(term)
                                gt_Datas_dict[Datas_key][Data_key][label_key] = term_list 
                            else:
                                gt_Datas_dict[Datas_key][Data_key][label_key] = label_object[label_key]
                        
                    else:
                        gt_Datas_dict[Datas_key][Data_key] = Data_object[Data_key]
        # The key 'asm_path' or 'text_base' in dict is a concrete value, and the key 'sections' is a list. They don't have anything that can't be transformed into json format, so they don't need to be transformed. 
        # gt_key == 'asm_path' or gt_key == 'text_base' or gt_key == 'relocs' or gt_key == 'sections' or gt_key == 'unknown_region' or gt_key == 'aligned_region'
        elif gt_key == 'asm_path' or gt_key == 'text_base' or gt_key == 'sections':
            gt_load_object_dict[gt_key] = dict[gt_key]
        # The key 'relocs' or 'unknown_region' or 'aligned_region' is a set. But set can't be tramsformed into json format directily.
        elif gt_key == 'relocs' or gt_key == 'unknown_region' or gt_key == 'aligned_region':
            gt_load_object_dict[gt_key] = list(dict[gt_key])
    gt_load_object_dict['Instrs'] = gt_Instrs_dict
    gt_load_object_dict['Data'] = gt_Datas_dict

    return gt_load_object_dict

# 去重
def deduplicate_dicts(list_of_dicts):
    seen = []
    result = []
    
    for d in list_of_dicts:
        if d not in seen:
            seen.append(d)
            result.append(d)
    return result

# 从原有的指令建模中拿到符号化的ground truth symbol_dict
def get_symbolization_object(gt_load_object_dict, includeAddress=True):

    symbolization_object_list = []

    Instrs_dict = gt_load_object_dict['Instrs']
    for address in Instrs_dict:
        attribute = ''
        if Instrs_dict[address]['imm']:
            # 'imm' means immediate oprand
            attribute = 'imm'
        elif Instrs_dict[address]['disp']:
            # 'disp' means displacement
            attribute = 'disp'
        else:
            continue
        # 获取的时候排除了值为-1或0的符号，这里认为是用作占位符的特殊数值，不进行符号化
        expType = Instrs_dict[address][attribute]['type']
        # [1, 3, 5]是原子表达式，理论上只有一个labels
        if expType in [1, 3, 5] and Instrs_dict[address][attribute]['terms'][0]['Address'] not in [-1, 0]:
            symbol_dict = {
                'idx': '',
                'instAddress': '', 
                'label': '', 
                'symbolValue': 0, 
                'type': -1, 
                'pos': '.text', 
                'attribute': attribute, 
                'evidence':{}
            }
            if includeAddress:
                symbol_dict['idx'] = Instrs_dict[address]['asm_idx']
                symbol_dict['instAddress'] = Instrs_dict[address]['addr']
            terms = Instrs_dict[address][attribute]['terms']
            symbol_dict['label'] = terms[0]['Name']  # 符号名称
            symbol_dict['symbolValue'] = terms[0]['Address'] # 符号地址
            symbol_dict['type'] = Instrs_dict[address][attribute]['type']   #   符号类型
            symbol_dict['final_value'] = Instrs_dict[address][attribute]['value']
            symbol_dict['final_label'] = symbol_dict['label']
            symbolization_object_list.append(symbol_dict)

        # [2, 4, 6, 7]是复合表达式，理论上至少一个labels
        elif expType in [2, 4, 6, 7]:
            symbol_dict = {
                'idx': '',
                'instAddress': '', 
                'label1': '', 
                'symbolValue1': 0, 
                'label2': '', 
                'symbolValue2': 0, 
                'type': -1, 
                'pos': '.text', 
                'attribute': attribute, 
                'evidence':{}
            }
            if includeAddress:
                symbol_dict['idx'] = Instrs_dict[address]['asm_idx']
                symbol_dict['instAddress'] = Instrs_dict[address]['addr']
            terms = Instrs_dict[address][attribute]['terms']
            symbol_dict['label1'] = terms[0]['Name']
            symbol_dict['symbolValue1'] = terms[0]['Address']
            if isinstance(terms[1], dict):
                symbol_dict['label2'] = terms[1]['Name']
                symbol_dict['symbolValue2'] = terms[1]['Address']
            else:
                symbol_dict['label2'] = terms[1]
                symbol_dict['symbolValue2'] = terms[1]
            symbol_dict['type'] = Instrs_dict[address][attribute]['type']
            symbol_dict['final_value'] = Instrs_dict[address][attribute]['value']
            # 跳转表的情况，第二个标签自带符号
            if str(symbol_dict['label2']).startswith('-'):
                symbol_dict['final_label'] = str(symbol_dict['label1']) + str(symbol_dict['label2'])
            else:
                symbol_dict['final_label'] = str(symbol_dict['label1']) + '+' + str(symbol_dict['label2'])
            symbolization_object_list.append(symbol_dict)
        # 符号参与计算的目标地址
        if "value" in Instrs_dict[address][attribute]:
            # 检查是否是间接跳转或类似跳表
            asm_line = Instrs_dict[address].get("asm_line", "")
            if "*" in asm_line and "(" in asm_line:
                # jump table 或间接跳转，无法静态确定目标
                symbol_dict['evidence']['targetAddress'] = None
            else:
                # 目前发现代码段中只有偏移存在于pc-relative才可以计算出目标地址
                if attribute == 'disp' and not Instrs_dict[address]['asm_is_pc_relative']:
                    symbol_dict['evidence']['targetAddress'] = None
                else:
                    symbol_dict['evidence']['targetAddress'] = Instrs_dict[address][attribute]["value"]
        if 'asm_is_call' in Instrs_dict[address]:
            symbol_dict['evidence']['asm_is_call'] = Instrs_dict[address]['asm_is_call']
        if 'asm_is_jmp' in Instrs_dict[address]:
            symbol_dict['evidence']['asm_is_jmp'] = Instrs_dict[address]['asm_is_jmp']
        if 'asm_is_lea' in Instrs_dict[address]:
            symbol_dict['evidence']['asm_is_lea'] = Instrs_dict[address]['asm_is_lea']
        if 'asm_is_pc_relative' in Instrs_dict[address]:
            symbol_dict['evidence']['asm_is_pc_relative'] = Instrs_dict[address]['asm_is_pc_relative']
        if 'asm_is_rbp_based' in Instrs_dict[address]:
            symbol_dict['evidence']['asm_is_rbp_based'] = Instrs_dict[address]['asm_is_rbp_based']
    


    Data_dict = gt_load_object_dict['Data']
    for address in Data_dict:
        expType = Data_dict[address]['value']['type']
        # [1, 3, 5]是原子表达式，理论上只有一个label
        if expType in [1, 3, 5]:
            symbol_dict = {
                'idx': '',
                'instAddress': '', 
                'label': '', 
                'symbolValue': 0, 
                'type': -1, 
                'pos': '.data',
                'evidence':{}
            }
            if includeAddress:
                symbol_dict['idx'] = Data_dict[address]["asm_idx"]
                symbol_dict['instAddress'] = Data_dict[address]['addr']
            symbol_dict['label'] =  Data_dict[address]['value']['terms'][0]['Name']
            symbol_dict['symbolValue'] =  Data_dict[address]['value']['terms'][0]['Address']
            symbol_dict['type'] =  Data_dict[address]['value']['type']
            symbol_dict['final_value'] = Data_dict[address]['value']['value']
            symbol_dict['final_label'] = symbol_dict['label']
            symbolization_object_list.append(symbol_dict)

        # [2, 4, 6, 7]是复合表达式，理论上至少一个labels
        elif expType in [2, 4, 6, 7]:
            symbol_dict = {
                'idx': '',
                'instAddress': '', 
                'label1': '', 
                'symbolValue1': 0, 
                'label2': '', 
                'symbolValue2': 0, 
                'type': -1, 
                'pos': '.data',
                'evidence':{}
            }
            if includeAddress:
                symbol_dict['idx'] = Data_dict[address]["asm_idx"]
                symbol_dict['instAddress'] = Data_dict[address]['addr']
            terms = Data_dict[address]['value']['terms']
            symbol_dict['label1'] =  terms[0]['Name']
            symbol_dict['symbolValue1'] = terms[0]['Address']
            if isinstance(terms[1], dict):
                symbol_dict['label2'] = terms[1]['Name']
                symbol_dict['symbolValue2'] = terms[1]['Address']
            else:
                symbol_dict['label2'] = terms[1]
                symbol_dict['symbolValue2'] = terms[1]
            symbol_dict['type'] =  Data_dict[address]['value']['type']
            symbol_dict['final_value'] = Data_dict[address]['value']['value']
            # 跳转表的情况，第二个标签自带符号
            if str(symbol_dict['label2']).startswith('-'):
                symbol_dict['final_label'] = str(symbol_dict['label1']) + str(symbol_dict['label2'])
            else:
                symbol_dict['final_label'] = str(symbol_dict['label1']) + '+' + str(symbol_dict['label2'])
            symbolization_object_list.append(symbol_dict)
        # 符号参与计算的目标地址（这里跳转表的目标地址reassessor计算的有点问题，应该是label1的值）
        if "value" in Data_dict[address]['value']:
            # 跳转表项表达式的目标地址
            if 'is_jumptable_item' in Data_dict[address] and Data_dict[address]['is_jumptable_item'] == True:
                symbol_dict['evidence']['targetAddress'] = Data_dict[address]['value']['terms'][0]['Address']
            # 重定位立即数的目标地址暂时不知
            elif 'r_type' in Data_dict[address] and Data_dict[address]['r_type'] in ["R_X86_64_JUMP_SLOT", 'R_X86_64_RELATIVE']:
                symbol_dict['evidence']['targetAddress'] = None
            # 普通符号的目标地址
            else:
                symbol_dict['evidence']['targetAddress'] = Data_dict[address]['value']["value"]
        # 标记识别的的符号是否是跳转表符号
        if 'is_jumptable_item' in Data_dict[address]:
            symbol_dict['evidence']['is_jumptable_item'] = Data_dict[address]['is_jumptable_item']

    # 去除因为不同汇编行导致生成同一符号的多个项
    symbolization_object_list = deduplicate_dicts(symbolization_object_list)
    return symbolization_object_list


# 将原始 symbol_dict 重构为 ImmediateWrapper 的 dict 形式,便于通过eviSymbol进行证据统计
def symbol_dict_to_immediate_wrappers(symbol_exp, completed_jumptable_bases):
    """
    一个 symbol_dict 转换为 1 个或 2 个 ImmediateWrapper(dict)
    """
    wrappers = []

    def build_wrapper(label, value):
        fact = {
            "value": value,
            "imm_size": None,
            "inst_address": symbol_exp.get("instAddress"),
            "inst_size": None,
            "imm_address": None,
            "imm_offset": None,
            "kind": "Imm" if symbol_exp.get("attribute") == "imm" else "Disp",

            "section": symbol_exp.get("pos"),
            "function": None,
            "asmline": "",
            "basicblock": None,
            "instr_mnemonic": None,
            "operand_index": None,
        }

        raw_evi = symbol_exp.get("evidence", {})

        meta = {
            "cs_ins": None,
            "asm_is_call": raw_evi.get("asm_is_call"),   # 相对于ImmediateWrapper新增
            "asm_is_jmp":  raw_evi.get("asm_is_jmp"),    # 相对于ImmediateWrapper新增
            "asm_is_lea": raw_evi.get("asm_is_lea"),     # 相对于ImmediateWrapper新增
            "asm_is_pc_relative": raw_evi.get("asm_is_pc_relative"),     # 相对于ImmediateWrapper新增
            "asm_is_rbp_based": raw_evi.get("asm_is_rbp_based"),         # 相对于ImmediateWrapper新增
            "is_jumptable_base": None,         # 相对于ImmediateWrapper新增,后续统一判断
            "is_jumptable_item": None,         # 相对于ImmediateWrapper新增,后续统一判断
        }

        evidence = {
            "target_address": raw_evi.get("targetAddress"),
            "address_from": None,
            "source": None,
            "flags": None,
            "explanations": None,
            "score": 0.0
        }

        decision = {
            "must_symbolize": "S+",
            "final_label": label,
            "type": symbol_exp.get("type"), # 相对于ImmediateWrapper新增
            "reason": []
        }

        return {
            "fact": fact,
            "meta": meta,
            "evidence": evidence,
            "decision": decision
        }

    # -------------------------
    # 单 label
    # -------------------------
    if "label" in symbol_exp:
        wrappers.append(
            build_wrapper(
                symbol_exp["final_label"],
                symbol_exp["final_value"]
            )
        )

    # -------------------------
    # 双 label →  一个类型应该只被建模一次
    # -------------------------
    elif "label1" in symbol_exp and "label2" in symbol_exp:
        wrappers.append(
            build_wrapper(
                symbol_exp["final_label"],
                symbol_exp["final_value"]
            )
        )
        # 用final_label和final_value处理应该就不需要单独处理跳转表了
        # # 跳转表项情况看基址是否已经建模过
        # if symbol_exp["evidence"]["is_jumptable_item"] == True:
        #     wrappers[0]["meta"]["is_jumptable_item"] = True
        #     if symbol_exp["label2"] in completed_jumptable_bases:
        #         # 跳转表基址已经建模过，跳过
        #         pass
        #     else:
        #         wrappers.append(
        #             build_wrapper(
        #                 symbol_exp["label2"],
        #                 symbol_exp["symbolValue2"]
        #             )
        #         )
        #         wrappers[1]["meta"]["is_jumptable_base"] = True
        #         completed_jumptable_bases.add(wrappers[1]["decision"]["final_label"])
        # # 不是跳转表项的情况正常建模
        # else:
        #     wrappers.append(
        #         build_wrapper(
        #             symbol_exp["label2"],
        #             symbol_exp["symbolValue2"]
        #         )
        #     )

    return wrappers

# 统计符号类型的数目
def count_symbol_types(symbolization_object_list):
    counts = {i: 0 for i in range(1, 9)} 
    for symbol in symbolization_object_list:
        t = symbol.get('type')
        if t in counts:
            counts[t] += 1
    return counts

# 统计符号类型并输出到控制台和文件中
def print_symbol_type_comparison(counts_with, counts_without, outfile=None):
    type_desc = {
        1: "Absolute + Atomic",
        2: "Absolute + Composite",
        3: "PCRelative + Atomic",
        4: "PCRelative + Composite",
        5: "GOTRelative + Atomic",
        6: "GOTRelative + Composite",
        7: "LabelRelative + Composite",
        8: "Other",
    }

    lines = []
    title = "Symbolization Type Statistics (With vs Without Instruction Address)"
    lines.append(title)
    lines.append("-" * len(title))

    header = f"{'Type':<6} {'Description':<35} {'WithInstAddr':<15} {'WithoutInstAddr':<18}"
    sep = "-" * len(header)

    lines.append(header)
    lines.append(sep)

    total_with = total_without = 0

    for t in range(1, 9):
        w = counts_with.get(t, 0)
        wo = counts_without.get(t, 0)
        total_with += w
        total_without += wo
        lines.append(f"{t:<6} {type_desc[t]:<35} {w:<15} {wo:<18}")

    lines.append(sep)
    lines.append(f"{'Total':<6} {'':<35} {total_with:<15} {total_without:<18}")

    # stdout
    print()
    for line in lines:
        print(line)

    # file
    if outfile:
        with open(outfile, "w", encoding="utf-8") as f:
            f.write("\n\n")
            for line in lines:
                f.write(line + "\n")

if __name__ == '__main__':
    
    input_file_path = os.path.join(
	    PROJECT_ROOT,
	    "reassessor",
	    "output",
	    "norm_db",
	    "gt.db"
	)

    gt_load_output_file_path = os.path.join(
	    PROJECT_ROOT,
	    "reassessorTmp",
	    "program.json"
	)

    # jumptable_info_path = os.path.join(
	#     PROJECT_ROOT,
	#     "reassessorTmp",
	#     "jumptable.txt"
	# )

    gt_symbolization_withInstAddr_outputfile_path = os.path.join(
	    PROJECT_ROOT,
	    "gt_results",
	    "gt_symbol_with_instAddr.json"
	)

    gt_symbolization_withoutInstAddr_outputfile_path = os.path.join(
	    PROJECT_ROOT,
	    "gt_results",
	    "gt_symbol_without_instAddr.json"
	)


    gt_symbol_instAddr_immediateWrapper_path = os.path.join(
	    PROJECT_ROOT,
	    "gt_results",
	    "gt_symbol_with_instAddr_ImmediateWrapper.json"
	)

    stat_path = os.path.join(
	    PROJECT_ROOT,
	    "reassessorTmp",
	    "type_counts.txt"
	)

    unknown_region_path = os.path.join(
	    PROJECT_ROOT,
	    "reassessorTmp",
	    "unknown_region.txt"
	)

    # 在数据统计文件里先添加说明性解释
    note = """type = 1: Absolute + Atomic
    type = 2: Absolute + Composite
    type = 3: PCRelative + Atomic
    type = 4: PCRelative + Composite
    type = 5: GOTRelative + Atomic
    type = 6: GOTRelative + Composite
    type = 7: LabelRelative + Composite
    type = 8: other
    """
    with open(stat_path, "a") as f:
        f.write(note + "\n")
    

    gt_load_object_dict = gt_load(input_file_path)
    
    # output the result of processed gt
    with open(gt_load_output_file_path, 'w') as file:
        json.dump(gt_load_object_dict, file, indent=4)
    # ssx: 最后需要删掉这个提示
    print("[OUTPUT] gt_load result has been wriiten into:", gt_load_output_file_path)

    # output the unknown region
    with open(unknown_region_path, "w") as f:
        addresses = gt_load_object_dict.get('unknown_region', [])
        for addr in addresses:
            f.write(str(addr) + "\n")
    
    
    # output the symbolization object produced from gt result
    includeInstAddr, notIncludeInstAddr = True, False

    # 从符号地址角度来说，不同地址的同一个符号算作两次符号化
    symbolList_with_instAddr = get_symbolization_object(gt_load_object_dict, includeInstAddr)
    with open(gt_symbolization_withInstAddr_outputfile_path, 'w') as file:
        json.dump(symbolList_with_instAddr, file, indent=4)
    # ssx:最后需要修改这个提示路径
    print("[OUTPUT] symbolization object with the number of instruction address from gt_load has been wriiten into:", gt_symbolization_withInstAddr_outputfile_path)

    # 从符号本身来说，不同地址但是标签一致的符号算作一次符号化
    symbolList_withoutAsm = get_symbolization_object(gt_load_object_dict, notIncludeInstAddr)
    with open(gt_symbolization_withoutInstAddr_outputfile_path, 'w') as file:
        json.dump(symbolList_withoutAsm, file, indent=4)
    # ssx:最后需要修改这个提示路径
    print("[OUTPUT] symbolization object without the number of instruction address from gt_load has been wriiten into:", gt_symbolization_withoutInstAddr_outputfile_path)

    # 将整体统计结果输出
    counts_with = count_symbol_types(symbolList_with_instAddr)
    counts_without = count_symbol_types(symbolList_withoutAsm)
    print_symbol_type_comparison(
        counts_with,
        counts_without,
        outfile=stat_path
    )

    
    # 将原始 symbol_dict 重构为 ImmediateWrapper 的 dict 形式
    immediate_wrappers = []
    completed_jumptable_bases = set()  # 记录已经建模的跳转表基址，防止被多次建模
    for sym in symbolList_with_instAddr:

        immediate_wrappers.extend(
            symbol_dict_to_immediate_wrappers(sym, completed_jumptable_bases)
        )
    with open(gt_symbol_instAddr_immediateWrapper_path, 'w') as file:
        json.dump(immediate_wrappers, file, indent=4)

    
