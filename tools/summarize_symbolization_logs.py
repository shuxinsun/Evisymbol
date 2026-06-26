#!/usr/bin/env python3

import os
import re
from collections import defaultdict
from openpyxl import Workbook

LOG_ROOT="../logs"
OUTPUT_FILE="./accuracy_summary.xlsx"
TXT_OUTPUT="./accuracy.txt"

stats=defaultdict(lambda:{"TP":0,"FN":0,"FP":0,"E8":0,
                          "FN_SQ":0,"E8_symtab":0,"E8_unknown":0,
                          "GT":0,"Pred":0,
                          "log_total":0,"log_missing":0,"symbolGT_failed":0,"no_matched_asm":0,"success":0,
                          "per_type":defaultdict(lambda:{"GT":0,"Pred":0,"TP":0,"FP":0,"FN":0})})

type_stats=defaultdict(lambda:defaultdict(lambda:{"TP":0,"FN":0,"FP":0}))

# ===============================
# 解析单个log文件
# ===============================
def parse_log_file(log_path):
    local_type_counts=defaultdict(lambda:{"TP":0,"FN":0,"FP":0})
    local_e8=0
    local_fn_sq=0
    local_e8_symtab=0
    local_e8_unknown=0

    local_gt = defaultdict(int)
    local_pred = defaultdict(int)

    # log statistics
    log_total=0
    log_missing=0
    symbolGT_failed=0
    no_matched_asm=0
    success=0

    in_table=False
    with open(log_path,"r",encoding="utf-8",errors="ignore") as f:
        log_total += 1
        for line in f:

            # 新增统计
            m1=re.search(r"FN-S\?\s*:\s*(\d+)",line)
            if m1:
                local_fn_sq+=int(m1.group(1))

            m2=re.search(r"E8-symtab\s*:\s*(\d+)",line)
            if m2:
                local_e8_symtab+=int(m2.group(1))

            m3=re.search(r"E8-unknown_region\s*:\s*(\d+)",line)
            if m3:
                local_e8_unknown+=int(m3.group(1))

            if "Missing log" in line:
                symbolGT_failed += 1

            if "[!] evisymbol.py failed" in line:
                symbolGT_failed += 1

            if "[WARN] No matched assembly for" in line:
                no_matched_asm += 1

            if "[✓] Done. All logs saved in" in line:
                success += 1

            if "=== Per-Type Statistics ===" in line:
                in_table=True
                continue

            if in_table:
                if line.strip()=="" or line.startswith("----"):
                    continue

                m=re.match(r"\s*([1-8])\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",line)
                if m:
                    t=int(m.group(1))
                    TP=int(m.group(4))
                    FP=int(m.group(5))
                    FN=int(m.group(6))
                    Pred=int(m.group(3))
                    GT=int(m.group(2))

                    if t==8:
                        local_e8+=FP
                    else:
                        local_type_counts[t]["TP"]+=TP
                        local_type_counts[t]["FP"]+=FP
                        local_type_counts[t]["FN"]+=FN

                    local_gt[t]+=GT
                    local_pred[t]+=Pred

    return (local_type_counts,local_e8,local_fn_sq,local_e8_symtab,local_e8_unknown,
            log_total,log_missing,symbolGT_failed,no_matched_asm,success,
            local_gt,local_pred)

# ===============================
# 遍历所有log文件
# ===============================
folders=sorted([f for f in os.listdir(LOG_ROOT) if os.path.isdir(os.path.join(LOG_ROOT,f))])
total_logs=len(folders)
print("Total logs:",total_logs)

for idx,folder in enumerate(folders,start=1):
    path=os.path.join(LOG_ROOT,folder)
    log_file=os.path.join(path,"log.txt")
    if not os.path.exists(log_file):
        continue
    parts=folder.split("-")
    if len(parts)<3:
        continue
    mode=parts[0].lower()
    opt=parts[1]

    percent=(idx/total_logs)*100
    print("[{}/{}]({:.1f}%)Processing:{}".format(idx,total_logs,percent,folder))

    (local_types,local_e8,local_fn_sq,local_e8_symtab,local_e8_unknown,
     log_total,log_missing,symbolGT_failed,no_matched_asm,success,
     local_gt,local_pred) = parse_log_file(log_file)

    for t in range(1,8):
        tp=local_types[t]["TP"]
        fn=local_types[t]["FN"]
        fp=local_types[t]["FP"]

        for key in [("ALL","ALL"),("ALL",opt),(mode,"ALL")]:
            type_stats[key][t]["TP"]+=tp
            type_stats[key][t]["FN"]+=fn
            type_stats[key][t]["FP"]+=fp

            stats[key]["TP"]+=tp
            stats[key]["FN"]+=fn
            stats[key]["FP"]+=fp

            stats[key]["per_type"][t]["TP"]+=tp
            stats[key]["per_type"][t]["FP"]+=fp
            stats[key]["per_type"][t]["FN"]+=fn
            stats[key]["per_type"][t]["GT"]+=local_gt[t]
            stats[key]["per_type"][t]["Pred"]+=local_pred[t]

    for key in [("ALL","ALL"),("ALL",opt),(mode,"ALL")]:
        stats[key]["E8"]+=local_e8
        stats[key]["FN_SQ"]+=local_fn_sq
        stats[key]["E8_symtab"]+=local_e8_symtab
        stats[key]["E8_unknown"]+=local_e8_unknown

        stats[key]["log_total"]+=log_total
        stats[key]["log_missing"]+=log_missing
        stats[key]["symbolGT_failed"]+=symbolGT_failed
        stats[key]["no_matched_asm"]+=no_matched_asm
        stats[key]["success"]+=success

# ===============================
# 生成accuracy.txt
# ===============================
with open(TXT_OUTPUT,"w") as f:
    groups=[("ALL","ALL"),("pie","ALL"),("nonpie","ALL")]
    opt_levels=[("ALL","ALL"),("pie","ALL"),("nonpie","ALL")]+ \
               [(g[0],g[1]) for g in stats.keys() if g[1]!="ALL"]

    for key in opt_levels:
        data=stats[key]
        f.write("===================================\n")
        f.write(f"{key[0]} {key[1]}\n")
        f.write("===================================\n\n")

        f.write("Log Statistics\n")
        f.write(f"Total: {data['log_total']}\n")
        f.write(f"Missing log: {data['log_missing']}\n")
        f.write(f"symbolGT failed: {data['symbolGT_failed']}\n")
        f.write(f"No matched asm: {data['no_matched_asm']}\n")
        f.write(f"Success: {data['success']}\n\n")

        # Overall
        GT_sum=sum(data['per_type'][t]['GT'] for t in range(1,9))
        Pred_sum=sum(data['per_type'][t]['Pred'] for t in range(1,9))
        TP_sum=sum(data['per_type'][t]['TP'] for t in range(1,9))
        FP_sum=sum(data['per_type'][t]['FP'] for t in range(1,9))
        FN_sum=sum(data['per_type'][t]['FN'] for t in range(1,9))
        precision = TP_sum/Pred_sum if Pred_sum>0 else 0
        recall = TP_sum/GT_sum if GT_sum>0 else 0
        f1 = 2*precision*recall/(precision+recall) if precision+recall>0 else 0

        f.write("Overall\n")
        f.write(f"GT: {GT_sum}\n")
        f.write(f"Pred: {Pred_sum}\n")
        f.write(f"TP: {TP_sum}\n")
        f.write(f"FP: {FP_sum}\n")
        f.write(f"FN: {FN_sum}\n")
        f.write(f"FN-S?: {data['FN_SQ']}\n")
        f.write(f"E8: {data['E8']}\n")
        f.write(f"E8-symtab: {data['E8_symtab']}\n")
        f.write(f"E8-unknown_region: {data['E8_unknown']}\n")
        f.write(f"Precision: {precision:.4f}\n")
        f.write(f"Recall   : {recall:.4f}\n")
        f.write(f"F1       : {f1:.4f}\n\n")

        # Per Type
        f.write("Per Type\n")
        for t in range(1,9):
            p = data['per_type'][t]
            tp,fp,fn,gt,pred = p['TP'],p['FP'],p['FN'],p['GT'],p['Pred']
            precision = tp/pred if pred>0 else 0
            recall = tp/gt if gt>0 else 0
            f1 = 2*precision*recall/(precision+recall) if precision+recall>0 else 0
            f.write(f"Type {t}: GT={gt} Pred={pred} TP={tp} FP={fp} FN={fn} P={precision:.4f} R={recall:.4f} F1={f1:.4f}\n")
        f.write("\n")

# ===============================
# 生成Excel（保持原逻辑不变）
# ===============================
wb=Workbook()
ws1=wb.active
ws1.title="Overall"

ws1.append([
"ID","Metric",
"Evisymbol(%)","Evisymbol(NUM)",
"Evisymbol_non-PIE(%)","Evisymbol_non-PIE(NUM)",
"Evisymbol_PIE(%)","Evisymbol_PIE(NUM)"
])

groups_excel=["ALL","nonpie","pie"]
for t in range(1,8):
    row_tp=["E{}".format(t),"TP"]
    row_fn=["","FN"]
    row_fp=["","FP"]
    for key in groups_excel:
        tc=type_stats[(key,"ALL")][t]
        TP=tc["TP"];FN=tc["FN"];FP=tc["FP"]
        denom=TP+FN+FP if TP+FN+FP>0 else 1
        row_tp+=[round(TP/denom*100,2),TP]
        row_fn+=[round(FN/denom*100,2),FN]
        row_fp+=[round(FP/denom*100,2),FP]
    ws1.append(row_tp)
    ws1.append(row_fn)
    ws1.append(row_fp)

# E8
row_e8=["E8","FP"]
for key in groups_excel:
    total_e1_7=sum(type_stats[(key,"ALL")][t]["TP"]+type_stats[(key,"ALL")][t]["FN"]+type_stats[(key,"ALL")][t]["FP"] for t in range(1,8))
    E8_total=stats[(key,"ALL")]["E8"]
    denom=total_e1_7+E8_total if total_e1_7+E8_total>0 else 1
    row_e8+=[round(E8_total/denom*100,2),E8_total]
ws1.append(row_e8)

# Sheet2 Optimization
ws2=wb.create_sheet("Optimization")
ws2.append(["Optimization","TP(%)","FN(%)","FP(%)","TP","FN","FP"])

total_TP=0
total_FN=0
total_FP=0
for opt in sorted(set(k[1] for k in stats.keys() if k[0]=="ALL" and k[1]!="ALL")):
    c=stats[("ALL",opt)]
    denom=c["TP"]+c["FN"]+c["FP"]
    if denom==0:
        continue
    ws2.append([
        opt,
        round(c["TP"]/denom*100,2),
        round(c["FN"]/denom*100,2),
        round(c["FP"]/denom*100,2),
        c["TP"],c["FN"],c["FP"]
    ])
    total_TP+=c["TP"]
    total_FN+=c["FN"]
    total_FP+=c["FP"]

# Total row
total_denom=total_TP+total_FN+total_FP if total_TP+total_FN+total_FP>0 else 1
ws2.append([
    "Total",
    round(total_TP/total_denom*100,2),
    round(total_FN/total_denom*100,2),
    round(total_FP/total_denom*100,2),
    total_TP,total_FN,total_FP
])

wb.save(OUTPUT_FILE)
print("accuracy.txt generated")
print("accuracy_summary.xlsx generated")
