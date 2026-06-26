import os, sys
from .normalizer.gt import NormalizeGT
from .normalizer.ramblr import NormalizeRamblr
from .normalizer.retro import NormalizeRetro
from .normalizer.ddisasm import NormalizeDdisasm
from .differ.diff import diff
from .preprocessing import remove_useless_sections

class Reassessor:
    def __init__(self, target, assem_dir, output_dir, bin_path = '', build_path=''):
        self.target =  os.path.abspath(target)
        self.assem_dir  =  os.path.abspath(assem_dir)
        self.output_dir =  os.path.abspath(output_dir)

        if build_path:
            self.build_path = os.path.abspath(build_path)
        else:
            self.build_path = self.assem_dir

        #copy binary
        self.base_name = os.path.basename(self.target)

        if bin_path:
            self.binary = bin_path
        else:
            self.binary = '%s/bin/%s'%(self.output_dir, self.base_name)

        if not os.path.exists(self.binary):
            os.system('mkdir -p %s/bin'%(self.output_dir))
            os.system('cp %s %s'%(self.target, self.binary))
            remove_useless_sections(self.binary)


    def run(self, reassem_dict):
        gt_norm_path, norm_dict = self.run_normalizer(reassem_dict)
        self.run_differ(gt_norm_path, norm_dict)


    def run_normalizer(self, reassem_dict, reset=False):
        """
        运行符号化工具（normalizer）对反汇编结果进行规范化处理
        
        主要功能：
        1. 对原始二进制（GT）进行符号化
        2. 对每个反汇编工具（ramblr、retrowrite、ddisasm）的输出进行符号化
        3. 将符号化结果保存为数据库文件，便于后续比较和分析
        
        Args:
            reassem_dict (dict): 反汇编工具的输出路径字典
                                格式：{工具名: 反汇编文件路径}
                                如：{'ramblr': '/path/ramblr.s', 'ddisasm': '/path/ddisasm.s'}
            reset (bool): 是否重置/重新生成符号化结果（忽略已存在的缓存）
        
        Returns:
            tuple: (gt_norm_path, norm_dict)
                - gt_norm_path: 原始二进制符号化结果的数据库路径
                - norm_dict: 各工具符号化结果的数据库路径字典
        """
        # 1. 创建规范化结果输出目录
        norm_dir = '%s/norm_db'%(self.output_dir)
        os.system('mkdir -p %s'%(norm_dir))
        # 2. 处理Ground Truth（原始二进制）的符号化
        gt_norm_path = '%s/gt.db'%(norm_dir)

        # 检查是否已有缓存且不需要重置
        if os.path.exists(gt_norm_path) and not reset:
            pass    # 已有缓存，跳过重新生成
        else:
            # 生成GT符号化结果
            # 打印执行命令（用于调试/日志）
            print('python3 -m reassessor.normalizer.gt %s %s %s --reloc %s --build_path %s'%(self.binary, self.assem_dir, gt_norm_path, self.target, self.build_path))
            # 创建GT符号化对象
            # 参数说明：
            # - self.binary: 原始二进制文件路径
            # - self.assem_dir: 汇编文件目录（可能包含反汇编输出）
            # - build_path: 构建路径（用于查找调试信息等）
            # - reloc_file: 重定位文件（用于符号解析）
            gt = NormalizeGT(self.binary, self.assem_dir, build_path=self.build_path, reloc_file=self.target) # 指令的符号化信息
            gt.normalize_data() # 执行数据符号化
            gt.save(gt_norm_path)   # 保存结果到数据库文件

        
        # 3. 初始化各工具符号化结果路径字典
        norm_dict = dict()

        # 无需其他工具对比，只要符号化的ground truth
        # 4. 对每个反汇编工具的输出进行符号化
        # for tool, reassem_path in reassem_dict.items():
        #     reassem = None
        #     cmd = ''
        #     if tool == 'ramblr':
        #         norm_path = '%s/ramblr.db'%(norm_dir)
        #         cmd = 'python3 -m reassessor.normalizer.ramblr %s %s %s'%(self.binary, reassem_path, norm_path)
        #     if tool == 'retrowrite':
        #         norm_path = '%s/retrowrite.db'%(norm_dir)
        #         cmd = 'python3 -m reassessor.normalizer.retro %s %s %s'%(self.binary, reassem_path, norm_path)
        #     if tool == 'ddisasm':
        #         norm_path = '%s/ddisasm.db'%(norm_dir)
        #         cmd = 'python3 -m reassessor.normalizer.ddisasm %s %s %s'%(self.binary, reassem_path, norm_path)

        #     # 5. 检查是否已有缓存或需要重置
        #     if not os.path.exists(norm_path) or reset:
        #         print(cmd)
        #         sys.stdout.flush()
        #         # 根据工具类型创建对应的符号化对象
        #         if tool == 'ramblr':
        #             reassem = NormalizeRamblr(self.binary, reassem_path)
        #         if tool == 'retrowrite':
        #             reassem = NormalizeRetro(self.binary, reassem_path)
        #         if tool == 'ddisasm':
        #             reassem = NormalizeDdisasm(self.binary, reassem_path)

        #         # 执行符号化操作
        #         reassem.normalize_inst()    # 规范化指令（提取指令中的符号）
        #         reassem.normalize_data()    # 规范化数据（提取数据段中的符号）
        #         reassem.save(norm_path)     # 保存到数据库文件

        #     # 6. 确认符号化结果文件存在，然后记录到返回字典中
        #     if os.path.exists(norm_path):
        #         norm_dict[tool] = norm_path
        # 7. 返回结果
        return gt_norm_path, norm_dict
    

    def run_differ(self, gt_norm_path, norm_dict, reset=False):
        error_dir = '%s/errors'%(self.output_dir)
        cmd = 'python3 -m reassessor.differ.diff %s %s %s'%(self.binary, gt_norm_path, error_dir)
        bRun = False
        if 'ramblr' in norm_dict:
            bRun = True
            cmd += ' --ramblr %s'%(norm_dict['ramblr'])
        if 'retrowrite' in norm_dict:
            bRun = True
            cmd += ' --retro %s'%(norm_dict['retrowrite'])
        if 'ddisasm' in norm_dict:
            bRun = True
            cmd += ' --ddisasm %s'%(norm_dict['ddisasm'])

        if bRun:
            print(cmd)
            diff(self.binary, gt_norm_path, norm_dict, error_dir, reset=reset)


import argparse
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='manager')
    parser.add_argument('target', type=str, help='Target Binary')
    parser.add_argument('assem_dir', type=str, help='Assembly Directory')
    parser.add_argument('output_dir', type=str, help='output_dir')
    parser.add_argument('--bin_path', type=str, help='Non-stripped binary path')
    parser.add_argument('--build_path', type=str, help='build_path')

    parser.add_argument('--ramblr', type=str, help='ramblr output')
    parser.add_argument('--retrowrite', type=str, help='retrowrite output')
    parser.add_argument('--ddisasm', type=str, help='ddisasm output')
    args = parser.parse_args()

    reassem_dict = dict()
    # 无需其他工具对比，只要符号化的ground truth
    # if args.ramblr:
    #     reassem_dict['ramblr'] = args.ramblr
    # if args.retrowrite:
    #     reassem_dict['retrowrite'] = args.retrowrite
    # if args.ddisasm:
    #     reassem_dict['ddisasm']  = args.ddisasm
    
    # if reassem_dict:
    #     reassessor = Reassessor(args.target, args.assem_dir, args.output_dir, bin_path = args.bin_path, build_path = args.build_path)
    #     gt_norm_path, norm_dict = reassessor.run_normalizer(reassem_dict)
    #     reassessor.run_differ(gt_norm_path, norm_dict)

    # 简要修改，让其无需其他工具的反汇编结果也能运行
    reassessor = Reassessor(args.target, args.assem_dir, args.output_dir, bin_path = args.bin_path, build_path = args.build_path)
    gt_norm_path, norm_dict = reassessor.run_normalizer(reassem_dict)