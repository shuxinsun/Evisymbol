import time
from evidence.baselevel.baseevidence import BaseLevelEvidence
from evidence.middlelevel.middleevidence import MiddleLevelEvidence
from evidence.highlevel.highevidence import HighLevelEvidence
from symbolizer.symbolize import Symbolizer
from lib.consts import UNKNOWN_REGION, MODE_MAPPING, MODE_WEIGHT_ANALYSIS

class FusionEvidence:
    def __init__(self, container, immediates):
        self.container = container
        self.immediates = immediates
        # 不使用defaultdict是为了后面打印日志做表格
        # 应用规则的数据统计
        self.evidence_counts = {
            'r1-address-range': 0,
            'r2-symtab': 0,
            'r3-relocation-exact': 0,
            'r4-call': 0,
            'r5-jmp-reference': 0,
            'r6-function-entry': 0,
            'r7-non-float-constant': 0,
            'r8-non-string-constant': 0,
            'r9-lea-base-offset': 0,
            'r10-got-entry': 0,
            'r11-gotplt-entry': 0,
            'r12-plt-entry': 0,
            'r13-pc-relative': 0,
            'r14-rbp-relative': 0,
            'r15-jumptable-base': 0,
            'r16-code-pointer': 0,
            'r17-aligned': 0,
            'r18-special-sections': 0,
            'r19-indexed-table-base': 0,
            'r25-indirect-call-offset': 0
        }
        # 统计立即值目标地址偏离程度（除了.dyn重定位表之外的）
        self.address_range_stats = {
            'in_range': 0,
            'out_0_1kb': 0,
            'out_1_2kb': 0,
            'out_2_3kb': 0,
            'out_3_4kb': 0,
            'out_4kb_plus': 0,
        }
        # 统计数据地址对齐情况
        self.data_align_stats = {
            'total': 0,
            'aligned_8': 0,       # 仅8字节对齐（不满足16字节对齐，但满足8字节对齐）
            'aligned_4': 0,       # 仅4字节对齐（不满足8字节对齐，但满足4字节对齐）
            'aligned_2': 0,       # 仅2字节对齐（不满足4字节对齐，但满足2字节对齐）
            'misaligned': 0       # 不对齐（连2字节对齐都不满足）
        }
        self.baseEvi = BaseLevelEvidence(container, immediates, self.evidence_counts, self.address_range_stats)
        self.middleEvi = MiddleLevelEvidence(container, immediates, self.evidence_counts, self.data_align_stats)
        self.highEvi = HighLevelEvidence(container, immediates, self.evidence_counts)

        # 用于计算时间
        self.time_base = 0.0
        self.time_middle = 0.0
        self.time_high = 0.0
        self.total_time = 0.0

        self.high_level_count = 0  # 进入高级证据的立即数数量
        self.high_level_confirmed_count = 0 # 进入高级证据层且被高级证据层确定的立即数数量
        self.total_imm_count = 0   # 总立即数数量


    # 在中级证据层后对证据得分进行分级
    def classify_symbolization_safety(self, imm):
        evi = imm.evidence
        dec = imm.decision
        if evi.score < -1: # 可能存在作为参数的地址指向了并非8字节对齐的情况
            dec.must_symbolize = "S-"
        elif evi.score >= 3:
            dec.must_symbolize = "S+"

    # 计时打印函数
    def print_time_stats(self):
        total = self.time_base + self.time_middle + self.time_high
        if total == 0:
            total = 1e-9
        
        print("\n" + "="*50)
        print("[+] Time Statistics for Evidence Levels")
        print("="*50)
        print(f"Base Level Time      : {self.time_base:.4f} s  ({self.time_base/total*100:.2f}%)")
        print(f"Middle Level Time    : {self.time_middle:.4f} s  ({self.time_middle/total*100:.2f}%)")
        print(f"High Level Time      : {self.time_high:.4f} s  ({self.time_high/total*100:.2f}%)")
        print(f"Total Evidence Time  : {total:.4f} s")
        print(f"Total Process Time   : {self.total_time:.4f} s")
        print("="*50 + "\n")
    
        # 打印高级证据比例统计
        if self.total_imm_count > 0:
            ratio = self.high_level_count / self.total_imm_count * 100
            high_level_confirmed_ratio = self.high_level_confirmed_count / self.high_level_count * 100
            print("\n" + "="*60)
            print("[+] High-Level Evidence Statistics")
            print("="*60)
            print(f"Total Immediates Processed    : {self.total_imm_count}")
            print(f"Entered High-Level Evidence   : {self.high_level_count}")
            print(f"High-Level Evidence Ratio     : {ratio:.2f}%")
            print(f"High-Level Confirmed Results  : {self.high_level_confirmed_count}")
            print(f"Confirmed Ratio in High-Level : {high_level_confirmed_ratio:.2f}%")
            print("="*60 + "\n")


    def run(self, mode=None):
        total_start = time.time()
        uncertain_symbol_set = set()
        # rip_certain_immediates = []
        symbolizer = Symbolizer(self.container)
        print("[*] Running Base/Middle/High Level Evidence...")
        self.total_imm_count = len(self.immediates)
        for imm in self.immediates:
            not_in_UNKNOWN_REGION = any(
                addr not in UNKNOWN_REGION 
                for addr in (imm.fact.inst_address, imm.fact.imm_address) 
                if addr
            )
            st = time.time()
            self.baseEvi.run(imm, not_in_UNKNOWN_REGION, mode)
            self.time_base += time.time() - st

            st = time.time()
            self.middleEvi.run(imm, not_in_UNKNOWN_REGION, mode)
            self.time_middle += time.time() - st

            self.classify_symbolization_safety(imm)
            if imm.decision.must_symbolize == "S?":
                self.high_level_count += 1
                st = time.time()
                self.highEvi.run(imm, mode)
                self.time_high += time.time() - st

                self.classify_symbolization_safety(imm)
                if imm.decision.must_symbolize == "S?":
                    uncertain_symbol_set.add(imm.fact.inst_address if imm.fact.inst_address else imm.fact.imm_address)
                    # print(f"[?] Uncertain Immediate at {imm.fact.asmline} (address: {imm.fact.inst_address}) with score {imm.evidence.score}")
                elif imm.decision.must_symbolize == "S+":
                    self.high_level_confirmed_count += 1
            if imm.decision.must_symbolize == "S+":
                symbolizer.symbolize(imm)
            

        self.total_time = time.time() - total_start
        self.print_time_stats()  
        print(f"[*] Uncertain Immediate Count: {len(uncertain_symbol_set)}")
        print("[*] Evidence Fusion Completed.")
        return self.evidence_counts, self.address_range_stats, self.data_align_stats, uncertain_symbol_set
