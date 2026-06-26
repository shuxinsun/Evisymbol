# EviSymbol 虚拟机源码复现说明书

EviSymbol 是一款针对二进制重写场景设计的立即数符号化工具，核心解决“二进制重写中，哪些立即数必须符号化、可以不符号化、绝不能符号化”的关键问题，避免因立即数符号化不当导致的重写错误，提升二进制重写的准确性与兼容性。

本说明书详细记录了 EviSymbol 工具在 Ubuntu 18.04 x64 虚拟机中的完整复现流程，包括环境搭建、代码运行、数据复现、问题排查等内容，确保使用者能够快速复现工具功能及相关实验结果。

# 第一章 虚拟机准备

## 一、虚拟机安装

操作系统：Ubuntu 18.04 LTS (x64)

## 二、源码下载

```bash
# 直接下载解压EviProject
```

**源码包目录如下：**

```bash
├── demos
│   ├── cpp_demo
│   ├── readme.md
│   ├── switch_demo-nonPIC
│   └── switch_demo-PIC
├── eviaccuracy.sh
├── evisymbol
│   ├── evidence
│   ├── evisymbol.py
│   ├── lib
│   ├── readme.md
│   ├── retrowrite
│   ├── rw
│   └── symbolizer
├── logs
├── readme.md
├── reassessor
│   ├── artifact
│   ├── build
│   ├── dist
│   ├── Dockerfile
│   ├── example
│   ├── LICENSE.md
│   ├── output
│   ├── README.md
│   ├── reassessor
│   ├── reassessor.egg-info
│   ├── requirements.txt
│   └── setup.py
├── evisymbol.sh
├── symbolGT.sh
├── threshold.sh
└── tools
    ├── gt_load.py
    ├── organize_llvm_asm.sh
    ├── readme.md
    ├── run_benchmarks_accuracy.sh
    ├── run_spec_accuracy.sh
    ├── spec_tools
    	├── buildtools
        ├── organize_spec_binaries.sh
        ├── prepare_stripped_bins.sh
        └── readme.md
    ├── summarize_symbolization_logs.py
    └── summarize_threshold_stats.py
```

# 第二章 EviSymbol

## 一、功能介绍

### 核心功能

- 立即数符号化决策：基于多层级证据分析（基础证据、中级证据、高级证据），判定候选立即数的符号化必要性，输出可解释、可追溯的符号化结果。
- 多基准测试支持：兼容 SPEC CPU2006、coreutils、binutils、llvm-test-suite 等主流基准测试集，支持不同编译级别（O0/O1/O2/O3/Os/Ofast）和运行模式（PIE/non-PIE、stripped/nonstripped）的测试。
- 兼容性验证：支持对符号化后的汇编文件进行编译运行，验证符号化结果的正确性。

### 依赖工具

- capstone：反汇编、指令解析
- angr：用于函数边界识别（CFGFast），辅助证据分析。

## 二、环境准备

### 基础信息

- 操作系统：Ubuntu 18.04 LTS (x64)

- Python 版本：3.6（推荐，兼容后续 reassessor 依赖）

- 编译器：gcc-4.9、g++-4.9、gfortran-4.9（推荐，兼容后续SPEC2006 ）

### 环境安装步骤

#### 1. 基础环境准备

```bash
# 更新软件源
sudo apt update
sudo apt-get update

# 安装 Python3 及 pip
sudo apt install python3-pip
```

#### 2. EviSymbol 环境安装

依赖 capstone、angr、intervaltree：（capstone 需指定版本 5.0.0.post1（5.0.1 与 angr 存在兼容性问题））

```bash
# 更新 pip 及相关工具
pip3 install --upgrade pip setuptools wheel

# 安装指定版本 capstone（解决后续reassessor的兼容性问题）
pip3 show capstone
pip3 uninstall capstone
pip3 install capstone==5.0.0.post1

# 安装 angr 和 intervaltree
pip3 install angr
pip3 install intervaltree
```

## 三、代码运行指南

#### 1. evisymbol.py

 - 功能：该 Python 脚本用于分析二进制文件，并提取满足特定证据条件的立即数。
 - 使用方法：`python3 ./evisymbol/evisymbol.py <binary_file_path> <asm_path> ` 
 - 输入：二进制文件 <binary_file_path> 和要生成的目标汇编文件自定义路径。
 - 输出：符号化信息文件，标记每条指令的立即数及其对应的证据类型。
 - 运行示例：`python3 ./evisymbol/evisymbol.py ./demos/cpp_demo/bin/simple_inheritance ./evi.s`

#### 2\. evisymbol.sh

 - 自动化调度运行 evisymbol.py，自动创建日志目录、保存运行日志与结果文件
 - 使用方法：`bash evisymbol.sh <stripped_binary_path> [-pie|-nonpie] [-O0|-O1|-O2|-O3|-Os|-Ofast] [-name program]`

 - 输入：已剥离二进制文件路径，可选传入编译模式、优化等级、程序名称等参数。
 - 输出：自动生成带时间戳与参数标识的日志文件夹，保存完整运行日志及分析结果。
 - 运行示例：`bash ./evisymbol.sh ./demos/switch_demo-PIC/bin/hello-stripped -pie -O2 -name switch_demo`

# 第三章 证据权重统计实验复现

## 一、功能介绍

### 核心功能

- 复现各个证据的权重统计数据结果

### 依赖工具

- evisymbol：核心工具，用于二进制重写场景下的立即数符号化决策。
- reassessor：用于生成符号化 ground truth（基准数据），用于准确率验证与对比。
- findutils/sed/grep/gawk/llvm-test-suite：用于阈值权重计算，适配实验数据统计需求。

## 二、环境准备

#### 1. EviSymbol安装

参考前述EviSymbol安装

#### 2. reassessor 环境安装

reassessor 依赖 pyelftools (≥ 0.29) 和 capstone (≥4.0.2)，其中 capstone 需指定版本 5.0.0.post1（5.0.1 与 angr 存在兼容性问题）：

```bash
# 进入reassessor
cd EviProject/reassessor

# 安装依赖
sudo pip3 install -r requirements.txt

# 安装 reassessor
python3 setup.py install --user

# 安装指定版本 capstone（解决兼容性问题，理论上Evisymbol已完成安装，由于安装 reassessor可能覆盖原有安装结果，建议重装）
# 验证capstone版本是否为5.0.0.post1
pip3 show capstone
pip3 uninstall capstone
pip3 install capstone==5.0.0.post1
```

#### 3. 安装 gcc-4.9 系列编译器

```bash
# 修改软件源（解决 Ubuntu 18.04 无 gcc-4.9 候选问题）
sudo gedit /etc/apt/sources.list

# 在文件末尾添加以下源
deb http://dk.archive.ubuntu.com/ubuntu/ xenial main
deb http://dk.archive.ubuntu.com/ubuntu/ xenial universe

# 更新源
sudo apt update

# 安装 gcc-4.9、g++-4.9、gfortran-4.9
sudo apt install g++-4.9
sudo apt install gcc-4.9
sudo apt install gfortran-4.9

# 查看编译器安装位置
which {gcc,g++,gfortran}-4.9

# 切换默认编译器版本（若当前版本不是 4.9）
# 切换 gcc
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-7 50
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-4.9 40
sudo update-alternatives --config gcc  # 输入 4.9 版本对应的序号

# 切换 g++
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-7 50
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-4.9 40
sudo update-alternatives --config g++  # 输入 4.9 版本对应的序号

# 切换 gfortran
sudo apt install gfortran  # 若未安装 gfortran 先执行此步骤
sudo update-alternatives --install /usr/bin/gfortran gfortran /usr/bin/gfortran-7 50
sudo update-alternatives --install /usr/bin/gfortran gfortran /usr/bin/gfortran-4.9 40
sudo update-alternatives --config gfortran  # 输入 4.9 版本对应的序号

# 验证默认版本（均需显示 4.9）
gcc --version
g++ --version
gfortran --version
```

#### 4. findutils 安装

安装路径：EviProject/weight_database（根目录下需提前创建weight_database文件夹）

##### （1）下载源码

```bash
# 下载 findutils 4.9.0 源码（下载至weight_database 目录）
cd EviProject/weight_database
# 下载源码包
wget https://ftp.gnu.org/gnu/findutils/findutils-4.9.0.tar.xz
# 解压源码包
tar -xf findutils-4.9.0.tar.xz
# 进入解压后的源码目录（进入后当前目录：EviProject/weight_database/findutils-4.9.0）
cd findutils-4.9.0
```

##### （2）六个优化级别编译

```bash
# 编译 findutils（O0 级别，保留中间文件，用于后续阈值权重计算）
mkdir build-O0
cd build-O0  # 当前目录：EviProject/weight_database/findutils-4.9.0/build-O0
# 配置编译参数
../configure CC=gcc CFLAGS="-O0 -g -save-temps=obj"
# 并行编译（使用所有 CPU 核心）
make -j$(nproc)
# 整理汇编文件（将所有 .s 文件统一移动到 intermediate/asm 目录）
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 findutils（O1 级别，相比O0变为O1即可，其他优化级别也是如此）
cd ..
mkdir build-O1
cd build-O1
../configure CC=gcc CFLAGS="-O1 -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 findutils（O2 级别）
cd ..
mkdir build-O2
cd build-O2
../configure CC=gcc CFLAGS="-O2 -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 findutils（O3 级别）
cd ..
mkdir build-O3
cd build-O3
../configure CC=gcc CFLAGS="-O3 -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 findutils（Os 级别）
cd ..
mkdir build-Os
cd build-Os
../configure CC=gcc CFLAGS="-Os -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 findutils（Ofast 级别）
cd ..
mkdir build-Ofast
cd build-Ofast
../configure CC=gcc CFLAGS="-Ofast -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;
```

#### 5. sed 环境安装

安装路径：EviProject/weight_database（根目录下需提前创建weight_database文件夹）

##### （1）下载源码

```bash
# 进入 sed 安装目录
cd EviProject/weight_database
# 下载 sed-4.9 源码包
wget https://ftp.gnu.org/gnu/sed/sed-4.9.tar.xz
# 解压源码包
tar -xf sed-4.9.tar.xz
# 进入解压后的源码目录（进入后当前目录：EviProject/weight_database/sed-4.9）
cd sed-4.9
```

##### （2）六个优化级别编译

```bash
# 编译 sed（O0 级别，保留中间文件，用于后续阈值权重计算）
mkdir build-O0
cd build-O0  # 当前目录：EviProject/weight_database/sed-4.9/build-O0
# 配置编译参数
../configure CC=gcc CFLAGS="-O0 -g -save-temps=obj"
# 并行编译
make -j$(nproc)
# 整理汇编文件（将所有 .s 文件统一移动到 intermediate/asm 目录）
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 sed（O1 级别，相比O0变为O1即可，其他优化级别也是如此）
cd ..
mkdir build-O1
cd build-O1
../configure CC=gcc CFLAGS="-O1 -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 sed（O2 级别）
cd ..
mkdir build-O2
cd build-O2
../configure CC=gcc CFLAGS="-O2 -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 sed（O3 级别）
cd ..
mkdir build-O3
cd build-O3
../configure CC=gcc CFLAGS="-O3 -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 sed（Os 级别）
cd ..
mkdir build-Os
cd build-Os
../configure CC=gcc CFLAGS="-Os -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 sed（Ofast 级别）
cd ..
mkdir build-Ofast
cd build-Ofast
../configure CC=gcc CFLAGS="-Ofast -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;
```

#### 6. grep 环境安装

安装路径：EviProject/weight_database（根目录下需提前创建weight_database文件夹）

##### （1）下载源码

```bash
# 进入 grep 安装目录
cd EviProject/weight_database
# 下载 grep-3.12 源码包
wget https://ftp.gnu.org/gnu/grep/grep-3.12.tar.xz
# 解压源码包
tar -xf grep-3.12.tar.xz
# 进入解压后的源码目录（进入后当前目录：EviProject/weight_database/grep-3.12）
cd grep-3.12
```

##### （2）六个优化级别编译

```bash
# 编译 grep（O0 级别，保留中间文件，用于后续阈值权重计算）
mkdir build-O0
cd build-O0  # 当前目录：EviProject/weight_database/grep-3.12/build-O0
# 配置编译参数
../configure CC=gcc CFLAGS="-O0 -g -save-temps=obj"
# 并行编译
make -j$(nproc)
# 整理汇编文件（将所有 .s 文件统一移动到 intermediate/asm 目录）
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 grep（O1 级别，相比O0变为O1即可，其他优化级别也是如此）
cd ..
mkdir build-O1
cd build-O1
../configure CC=gcc CFLAGS="-O1 -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 grep（O2 级别）
cd ..
mkdir build-O2
cd build-O2
../configure CC=gcc CFLAGS="-O2 -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 grep（O3 级别）
cd ..
mkdir build-O3
cd build-O3
../configure CC=gcc CFLAGS="-O3 -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 grep（Os 级别）
cd ..
mkdir build-Os
cd build-Os
../configure CC=gcc CFLAGS="-Os -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 grep（Ofast 级别）
cd ..
mkdir build-Ofast
cd build-Ofast
../configure CC=gcc CFLAGS="-Ofast -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;
```

#### 7. gawk 环境安装

安装路径：EviProject/weight_database（根目录下需提前创建weight_database文件夹）

##### （1）下载源码

```bash
# 进入 gawk 安装目录
cd EviProject/weight_database
# 下载 gawk-5.2.2 源码包
wget https://ftp.gnu.org/gnu/gawk/gawk-5.2.2.tar.xz
# 解压源码包
tar -xf gawk-5.2.2.tar.xz
# 进入解压后的源码目录（当前目录：EviProject/weight_database/gawk-5.2.2）
cd gawk-5.2.2
```

##### （2）六个优化级别编译

```bash
# 编译 gawk（O0 级别，保留中间文件，用于后续阈值权重计算）
mkdir build-O0
cd build-O0  # 当前目录：EviProject/weight_database/gawk-5.2.2/build-O0
# 配置编译参数
../configure CC=gcc CFLAGS="-O0 -g -save-temps=obj"
# 并行编译
make -j$(nproc)
# 整理汇编文件（将所有 .s 文件统一移动到 intermediate/asm 目录）
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 gawk（O1 级别，相比O0变为O1即可，其他优化级别也是如此）
cd ..
mkdir build-O1
cd build-O1
../configure CC=gcc CFLAGS="-O1 -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 gawk（O2 级别）
cd ..
mkdir build-O2
cd build-O2
../configure CC=gcc CFLAGS="-O2 -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 gawk（O3 级别）
cd ..
mkdir build-O3
cd build-O3
../configure CC=gcc CFLAGS="-O3 -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 gawk（Os 级别）
cd ..
mkdir build-Os
cd build-Os
../configure CC=gcc CFLAGS="-Os -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;

# 编译 gawk（Ofast 级别）
cd ..
mkdir build-Ofast
cd build-Ofast
../configure CC=gcc CFLAGS="-Ofast -g -save-temps=obj"
make -j$(nproc)
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;
```

#### 8. llvm-test-suite 环境安装

安装路径：EviProject/weight_database（根目录下需提前创建weight_database文件夹）

##### （1）下载源码

```bash
# 进入 llvm-test-suite 安装目录
cd EviProject/weight_database

# 下载 llvm-test-suite 8.0.0 版本源码（兼容 Ubuntu 18.04）
wget https://github.com/llvm/llvm-test-suite/archive/refs/tags/llvmorg-8.0.0.zip
unzip llvmorg-8.0.0.zip # 解压源码包
mv llvm-test-suite-llvmorg-8.0.0 llvm-test-suite # 重命名一下
# 进入源码目录（进入后当前目录：EviProject/weight_database/llvm-test-suite）
cd llvm-test-suite
```

##### （2）安装依赖

```bash
# 安装依赖（有个程序需要这两个依赖）
sudo apt install cmake tcl tcl-dev -y
```

##### （3）六个优化级别下编译

```bash
# 编译 MultiSource/Applications（O0 级别，保留中间文件）
mkdir multisource-build-O0
cd multisource-build-O0
cmake .. \
  -DCMAKE_C_COMPILER=gcc \
  -DCMAKE_C_FLAGS="-std=gnu89 -O0 -g -save-temps" \
  -DTEST_SUITE_SUBDIRS="MultiSource/Applications" \
  -DTEST_SUITE_COLLECT_CODE_SIZE=OFF
# 并行编译
make -j$(nproc)
# 进入编译结果目录（进入后当前目录：EviProject/weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications）
cd MultiSource/Applications
# 整理汇编文件（将所有 .s 文件统一移动到 intermediate/asm 目录）
cp ../../../../../tools/_llvm_asm.sh ./
# 按照绝对地址就是复制这个脚本：cp EviProject/tools/organize_llvm_asm.sh EviProject/weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications
bash ./organize_llvm_asm.sh


# 编译 MultiSource/Applications（O1 级别）
mkdir multisource-build-O1
cd multisource-build-O1
cmake .. \
  -DCMAKE_C_COMPILER=gcc \
  -DCMAKE_C_FLAGS="-std=gnu89 -O1 -g -save-temps" \
  -DTEST_SUITE_SUBDIRS="MultiSource/Applications" \
  -DTEST_SUITE_COLLECT_CODE_SIZE=OFF
make -j$(nproc)
cd MultiSource/Applications
cp ../../../../../tools/organize_llvm_asm.sh ./
bash ./organize_llvm_asm.sh


# 编译 MultiSource/Applications（O2 级别）
mkdir multisource-build-O2
cd multisource-build-O2
cmake .. \
  -DCMAKE_C_COMPILER=gcc \
  -DCMAKE_C_FLAGS="-std=gnu89 -O2 -g -save-temps" \
  -DTEST_SUITE_SUBDIRS="MultiSource/Applications" \
  -DTEST_SUITE_COLLECT_CODE_SIZE=OFF
make -j$(nproc)
cd MultiSource/Applications
cp ../../../../../tools/organize_llvm_asm.sh ./
bash ./organize_llvm_asm.sh

# 编译 MultiSource/Applications（O3 级别）
mkdir multisource-build-O3
cd multisource-build-O3
cmake .. \
  -DCMAKE_C_COMPILER=gcc \
  -DCMAKE_C_FLAGS="-std=gnu89 -O3 -g -save-temps" \
  -DTEST_SUITE_SUBDIRS="MultiSource/Applications" \
  -DTEST_SUITE_COLLECT_CODE_SIZE=OFF
make -j$(nproc)
cd MultiSource/Applications
cp ../../../../../tools/organize_llvm_asm.sh ./
bash ./organize_llvm_asm.sh

# 编译 MultiSource/Applications（Os 级别）
mkdir multisource-build-Os
cd multisource-build-Os
cmake .. \
  -DCMAKE_C_COMPILER=gcc \
  -DCMAKE_C_FLAGS="-std=gnu89 -Os -g -save-temps" \
  -DTEST_SUITE_SUBDIRS="MultiSource/Applications" \
  -DTEST_SUITE_COLLECT_CODE_SIZE=OFF
make -j$(nproc)
cd MultiSource/Applications
cp ../../../../../tools/organize_llvm_asm.sh ./
bash ./organize_llvm_asm.sh

# 编译 MultiSource/Applications（Ofast 级别）
mkdir multisource-build-Ofast
cd multisource-build-Ofast
cmake .. \
  -DCMAKE_C_COMPILER=gcc \
  -DCMAKE_C_FLAGS="-std=gnu89 -Ofast -g -save-temps" \
  -DTEST_SUITE_SUBDIRS="MultiSource/Applications" \
  -DTEST_SUITE_COLLECT_CODE_SIZE=OFF
make -j$(nproc)
cd MultiSource/Applications
cp ../../../../../tools/organize_llvm_asm.sh ./
bash ./organize_llvm_asm.sh
```

## 三、代码运行指南

#### 1\. evisymbol.py

 - 功能：该 Python 脚本用于分析二进制文件，并提取满足特定证据条件的立即数。
 - 使用方法：`python3 ./evisymbol/evisymbol.py <binary_file_path> <asm_path> ` 
 - 输入：二进制文件 <binary_file_path> 和要生成的目标汇编文件自定义路径。
 - 输出：符号化信息文件，标记每条指令的立即数及其对应的证据类型。
 - 运行示例：`python3 ./evisymbol/evisymbol.py ./demos/cpp_demo/bin/simple_inheritance ./evi.s`

#### 2\. evisymbol.sh

 - 自动化调度运行 evisymbol.py，自动创建日志目录、保存运行日志与结果文件
 - 使用方法：`bash evisymbol.sh <stripped_binary_path> [-pie|-nonpie] [-O0|-O1|-O2|-O3|-Os|-Ofast] [-name program]`

 - 输入：已剥离二进制文件路径，可选传入编译模式、优化等级、程序名称等参数。
 - 输出：自动生成带时间戳与参数标识的日志文件夹，保存完整运行日志及分析结果。
 - 运行示例：`bash ./evisymbol.sh ./demos/switch_demo-PIC/bin/hello-stripped -pie -O2 -name switch_demo`

#### 3. symbolGT.sh

 - 功能：生成ground truth 数据文件
 - 使用方法：`bash symbolGT.sh <unstripped_binary_path> <asm_dir_path>`
 - 输入：未剥离二进制文件  和编译生成的汇编文件所在目录。
 - 输出：ground truth 数据文件，记录程序中每条指令对应的符号化信息。
 - 运行示例：`bash ./symbolGT.sh ./demos/switch_demo-PIC/bin/hello-nonstripped ./demos/switch_demo-PIC/asm/`

#### 4\. threshold.py

 - 功能：该脚本用于基于未剥离二进制文件和对应汇编目录，自动执行 symbolGT.sh 与 evisymbol.py，收集符号化相关的立即数统计结果，并按 PIE/优化级别等参数生成结构化日志目录保存所有中间结果与日志。
 - 使用方法：`bash ./threshold.sh <unstripped_binary_path> <asm_dir_path> [-pie|-nonpie] [-O0|-O1|-O2|-O3|-Os|-Ofast] [-name program]`
 - 输入：须传入未剥离的二进制文件路径和汇编文件目录，后面的 `-pie/-nonpie`、优化等级、`-name 程序名` 均为选填参数，主要用于自动生成日志名称。
 - 输出：最终统计结果，展示各类证据的权重比例，可用于进一步分析。
 - 运行示例：`bash ./threshold.sh ./demos/switch_demo-PIC/bin/hello-nonstripped ./demos/switch_demo-PIC/asm/ -pie -name hello`

## 四、实验数据复现

获取文件中所有满足证据的立即数、gt中满足证据立即数及相关占比

**注意：运行前请确保EviProject/logs为空文件夹**

```bash
# 清空logs目录（谨慎：会删除所有文件，建议对原logs内容备份重命名）
rm -rf EviProject/logs/*
```

#### 1. 获取findutils数据 (nonpie)

```bash
# EviProject根目录执行
bash ./threshold.sh ./weight_database/findutils-4.9.0/build-O0/find/find ./weight_database/findutils-4.9.0/build-O0/intermediate/asm/ -nonpie -O0 -name find
bash ./threshold.sh ./weight_database/findutils-4.9.0/build-O1/find/find ./weight_database/findutils-4.9.0/build-O1/intermediate/asm/ -nonpie -O1 -name find
bash ./threshold.sh ./weight_database/findutils-4.9.0/build-O2/find/find ./weight_database/findutils-4.9.0/build-O2/intermediate/asm/ -nonpie -O2 -name find
bash ./threshold.sh ./weight_database/findutils-4.9.0/build-O3/find/find ./weight_database/findutils-4.9.0/build-O3/intermediate/asm/ -nonpie -O3 -name find
bash ./threshold.sh ./weight_database/findutils-4.9.0/build-Os/find/find ./weight_database/findutils-4.9.0/build-Os/intermediate/asm/ -nonpie -Os -name find
bash ./threshold.sh ./weight_database/findutils-4.9.0/build-Ofast/find/find ./weight_database/findutils-4.9.0/build-Ofast/intermediate/asm/ -nonpie -Ofast -name find
```

#### 2. 获取sed数据 (nonpie)

```bash
# EviProject根目录执行
bash ./threshold.sh ./weight_database/sed-4.9/build-O0/sed/sed ./weight_database/sed-4.9/build-O0/intermediate/asm/ -nonpie -O0 -name sed
bash ./threshold.sh ./weight_database/sed-4.9/build-O1/sed/sed ./weight_database/sed-4.9/build-O1/intermediate/asm/ -nonpie -O1 -name sed
bash ./threshold.sh ./weight_database/sed-4.9/build-O2/sed/sed ./weight_database/sed-4.9/build-O2/intermediate/asm/ -nonpie -O2 -name sed
bash ./threshold.sh ./weight_database/sed-4.9/build-O3/sed/sed ./weight_database/sed-4.9/build-O3/intermediate/asm/ -nonpie -O3 -name sed
bash ./threshold.sh ./weight_database/sed-4.9/build-Os/sed/sed ./weight_database/sed-4.9/build-Os/intermediate/asm/ -nonpie -Os -name sed
bash ./threshold.sh ./weight_database/sed-4.9/build-Ofast/sed/sed ./weight_database/sed-4.9/build-Ofast/intermediate/asm/ -nonpie -Ofast -name sed
```

#### 3. 获取grep数据 (nonpie)

```bash
# EviProject根目录执行
bash ./threshold.sh ./weight_database/grep-3.12/build-O0/src/grep ./weight_database/grep-3.12/build-O0/intermediate/asm/ -nonpie -O0 -name grep
bash ./threshold.sh ./weight_database/grep-3.12/build-O1/src/grep ./weight_database/grep-3.12/build-O1/intermediate/asm/ -nonpie -O1 -name grep
bash ./threshold.sh ./weight_database/grep-3.12/build-O2/src/grep ./weight_database/grep-3.12/build-O2/intermediate/asm/ -nonpie -O2 -name grep
bash ./threshold.sh ./weight_database/grep-3.12/build-O3/src/grep ./weight_database/grep-3.12/build-O3/intermediate/asm/ -nonpie -O3 -name grep
bash ./threshold.sh ./weight_database/grep-3.12/build-Os/src/grep ./weight_database/grep-3.12/build-Os/intermediate/asm/ -nonpie -Os -name grep
bash ./threshold.sh ./weight_database/grep-3.12/build-Ofast/src/grep ./weight_database/grep-3.12/build-Ofast/intermediate/asm/ -nonpie -Ofast -name grep
```

#### 4. 获取gawk数据 (nonpie)

```bash
# EviProject根目录执行
bash ./threshold.sh ./weight_database/gawk-5.2.2/build-O0/gawk ./weight_database/gawk-5.2.2/build-O0/intermediate/asm/ -nonpie -O0 -name gawk
bash ./threshold.sh ./weight_database/gawk-5.2.2/build-O1/gawk ./weight_database/gawk-5.2.2/build-O1/intermediate/asm/ -nonpie -O1 -name gawk
bash ./threshold.sh ./weight_database/gawk-5.2.2/build-O2/gawk ./weight_database/gawk-5.2.2/build-O2/intermediate/asm/ -nonpie -O2 -name gawk
bash ./threshold.sh ./weight_database/gawk-5.2.2/build-O3/gawk ./weight_database/gawk-5.2.2/build-O3/intermediate/asm/ -nonpie -O3 -name gawk
bash ./threshold.sh ./weight_database/gawk-5.2.2/build-Os/gawk ./weight_database/gawk-5.2.2/build-Os/intermediate/asm/ -nonpie -Os -name gawk
bash ./threshold.sh ./weight_database/gawk-5.2.2/build-Ofast/gawk ./weight_database/gawk-5.2.2/build-Ofast/intermediate/asm/ -nonpie -Ofast -name gawk
```

#### 5. 获取llvm-test-suite数据 (nonpie)

注：不同优化级别的命令区别就是O0全部替换成O1，O1全部替换成O2，以此类推

##### （1）O0级别

```bash
# EviProject根目录执行
# aha
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/aha/intermediate/binary/aha ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/aha/intermediate/asm -nonpie -O0 -name aha
# Burg
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/Burg/intermediate/binary/burg ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/Burg/intermediate/asm -nonpie -O0 -name burg
# ClamAV
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/ClamAV/intermediate/binary/clamscan ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/ClamAV/intermediate/asm -nonpie -O0 -name clamscan
# d
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/d/intermediate/binary/make_dparser ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/d/intermediate/asm -nonpie -O0 -name d
# lemon
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/lemon/intermediate/binary/lemon ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/lemon/intermediate/asm -nonpie -O0 -name lemon
# lua
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/lua/intermediate/binary/lua ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/lua/intermediate/asm -nonpie -O0 -name lua
# obsequi
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/obsequi/intermediate/binary/Obsequi ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/obsequi/intermediate/asm -nonpie -O0 -name Obsequi
# sgefa
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/sgefa/intermediate/binary/sgefa ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/sgefa/intermediate/asm -nonpie -O0 -name sgefa
# SIBsim4
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/SIBsim4/intermediate/binary/SIBsim4 ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/SIBsim4/intermediate/asm -nonpie -O0 -name SIBsim4
# siod
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/siod/intermediate/binary/siod ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/siod/intermediate/asm -nonpie -O0 -name siod
# SPASS
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/SPASS/intermediate/binary/SPASS ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/SPASS/intermediate/asm -nonpie -O0 -name SPASS
# spiff
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/spiff/intermediate/binary/spiff ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/spiff/intermediate/asm -nonpie -O0 -name spiff
# sqlite3
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/sqlite3/intermediate/binary/sqlite3 ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/sqlite3/intermediate/asm -nonpie -O0 -name sqlite3
# viterbi
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/viterbi/intermediate/binary/viterbi ./weight_database/llvm-test-suite/multisource-build-O0/MultiSource/Applications/viterbi/intermediate/asm -nonpie -O0 -name viterbi
```

##### （2）O1级别

```bash
# EviProject根目录执行
# aha
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/aha/intermediate/binary/aha ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/aha/intermediate/asm -nonpie -O1 -name aha
# Burg
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/Burg/intermediate/binary/burg ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/Burg/intermediate/asm -nonpie -O1 -name burg
# ClamAV
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/ClamAV/intermediate/binary/clamscan ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/ClamAV/intermediate/asm -nonpie -O1 -name clamscan
# d
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/d/intermediate/binary/make_dparser ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/d/intermediate/asm -nonpie -O1 -name d
# lemon
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/lemon/intermediate/binary/lemon ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/lemon/intermediate/asm -nonpie -O1 -name lemon
# lua
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/lua/intermediate/binary/lua ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/lua/intermediate/asm -nonpie -O1 -name lua
# obsequi
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/obsequi/intermediate/binary/Obsequi ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/obsequi/intermediate/asm -nonpie -O1 -name Obsequi
# sgefa
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/sgefa/intermediate/binary/sgefa ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/sgefa/intermediate/asm -nonpie -O1 -name sgefa
# SIBsim4
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/SIBsim4/intermediate/binary/SIBsim4 ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/SIBsim4/intermediate/asm -nonpie -O1 -name SIBsim4
# siod
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/siod/intermediate/binary/siod ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/siod/intermediate/asm -nonpie -O1 -name siod
# SPASS
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/SPASS/intermediate/binary/SPASS ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/SPASS/intermediate/asm -nonpie -O1 -name SPASS
# spiff
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/spiff/intermediate/binary/spiff ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/spiff/intermediate/asm -nonpie -O1 -name spiff
# sqlite3
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/sqlite3/intermediate/binary/sqlite3 ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/sqlite3/intermediate/asm -nonpie -O1 -name sqlite3
# viterbi
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/viterbi/intermediate/binary/viterbi ./weight_database/llvm-test-suite/multisource-build-O1/MultiSource/Applications/viterbi/intermediate/asm -nonpie -O1 -name viterbi
```

##### （3）O2级别

```bash
# EviProject根目录执行
# aha
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/aha/intermediate/binary/aha ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/aha/intermediate/asm -nonpie -O2 -name aha
# Burg
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/Burg/intermediate/binary/burg ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/Burg/intermediate/asm -nonpie -O2 -name burg
# ClamAV
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/ClamAV/intermediate/binary/clamscan ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/ClamAV/intermediate/asm -nonpie -O2 -name clamscan
# d
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/d/intermediate/binary/make_dparser ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/d/intermediate/asm -nonpie -O2 -name d
# lemon
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/lemon/intermediate/binary/lemon ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/lemon/intermediate/asm -nonpie -O2 -name lemon
# lua
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/lua/intermediate/binary/lua ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/lua/intermediate/asm -nonpie -O2 -name lua
# obsequi
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/obsequi/intermediate/binary/Obsequi ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/obsequi/intermediate/asm -nonpie -O2 -name Obsequi
# sgefa
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/sgefa/intermediate/binary/sgefa ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/sgefa/intermediate/asm -nonpie -O2 -name sgefa
# SIBsim4
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/SIBsim4/intermediate/binary/SIBsim4 ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/SIBsim4/intermediate/asm -nonpie -O2 -name SIBsim4
# siod
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/siod/intermediate/binary/siod ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/siod/intermediate/asm -nonpie -O2 -name siod
# SPASS
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/SPASS/intermediate/binary/SPASS ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/SPASS/intermediate/asm -nonpie -O2 -name SPASS
# spiff
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/spiff/intermediate/binary/spiff ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/spiff/intermediate/asm -nonpie -O2 -name spiff
# sqlite3
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/sqlite3/intermediate/binary/sqlite3 ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/sqlite3/intermediate/asm -nonpie -O2 -name sqlite3
# viterbi
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/viterbi/intermediate/binary/viterbi ./weight_database/llvm-test-suite/multisource-build-O2/MultiSource/Applications/viterbi/intermediate/asm -nonpie -O2 -name viterbi
```

##### （4）O3级别

```bash
# EviProject根目录执行
# aha
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/aha/intermediate/binary/aha ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/aha/intermediate/asm -nonpie -O3 -name aha
# Burg
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/Burg/intermediate/binary/burg ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/Burg/intermediate/asm -nonpie -O3 -name burg
# ClamAV
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/ClamAV/intermediate/binary/clamscan ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/ClamAV/intermediate/asm -nonpie -O3 -name clamscan
# d
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/d/intermediate/binary/make_dparser ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/d/intermediate/asm -nonpie -O3 -name d
# lemon
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/lemon/intermediate/binary/lemon ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/lemon/intermediate/asm -nonpie -O3 -name lemon
# lua
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/lua/intermediate/binary/lua ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/lua/intermediate/asm -nonpie -O3 -name lua
# obsequi
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/obsequi/intermediate/binary/Obsequi ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/obsequi/intermediate/asm -nonpie -O3 -name Obsequi
# sgefa
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/sgefa/intermediate/binary/sgefa ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/sgefa/intermediate/asm -nonpie -O3 -name sgefa
# SIBsim4
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/SIBsim4/intermediate/binary/SIBsim4 ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/SIBsim4/intermediate/asm -nonpie -O3 -name SIBsim4
# siod
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/siod/intermediate/binary/siod ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/siod/intermediate/asm -nonpie -O3 -name siod
# SPASS
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/SPASS/intermediate/binary/SPASS ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/SPASS/intermediate/asm -nonpie -O3 -name SPASS
# spiff
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/spiff/intermediate/binary/spiff ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/spiff/intermediate/asm -nonpie -O3 -name spiff
# sqlite3
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/sqlite3/intermediate/binary/sqlite3 ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/sqlite3/intermediate/asm -nonpie -O3 -name sqlite3
# viterbi
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/viterbi/intermediate/binary/viterbi ./weight_database/llvm-test-suite/multisource-build-O3/MultiSource/Applications/viterbi/intermediate/asm -nonpie -O3 -name viterbi
```

##### （5）Os级别

```bash
# EviProject根目录执行
# aha
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/aha/intermediate/binary/aha ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/aha/intermediate/asm -nonpie -Os -name aha
# Burg
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/Burg/intermediate/binary/burg ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/Burg/intermediate/asm -nonpie -Os -name burg
# ClamAV
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/ClamAV/intermediate/binary/clamscan ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/ClamAV/intermediate/asm -nonpie -Os -name clamscan
# d
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/d/intermediate/binary/make_dparser ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/d/intermediate/asm -nonpie -Os -name d
# lemon
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/lemon/intermediate/binary/lemon ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/lemon/intermediate/asm -nonpie -Os -name lemon
# lua
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/lua/intermediate/binary/lua ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/lua/intermediate/asm -nonpie -Os -name lua
# obsequi
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/obsequi/intermediate/binary/Obsequi ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/obsequi/intermediate/asm -nonpie -Os -name Obsequi
# sgefa
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/sgefa/intermediate/binary/sgefa ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/sgefa/intermediate/asm -nonpie -Os -name sgefa
# SIBsim4
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/SIBsim4/intermediate/binary/SIBsim4 ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/SIBsim4/intermediate/asm -nonpie -Os -name SIBsim4
# siod
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/siod/intermediate/binary/siod ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/siod/intermediate/asm -nonpie -Os -name siod
# SPASS
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/SPASS/intermediate/binary/SPASS ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/SPASS/intermediate/asm -nonpie -Os -name SPASS
# spiff
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/spiff/intermediate/binary/spiff ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/spiff/intermediate/asm -nonpie -Os -name spiff
# sqlite3
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/sqlite3/intermediate/binary/sqlite3 ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/sqlite3/intermediate/asm -nonpie -Os -name sqlite3
# viterbi
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/viterbi/intermediate/binary/viterbi ./weight_database/llvm-test-suite/multisource-build-Os/MultiSource/Applications/viterbi/intermediate/asm -nonpie -Os -name viterbi
```

##### （6）Ofast级别

```bash
# EviProject根目录执行
# aha
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/aha/intermediate/binary/aha ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/aha/intermediate/asm -nonpie -Ofast -name aha
# Burg
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/Burg/intermediate/binary/burg ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/Burg/intermediate/asm -nonpie -Ofast -name burg
# ClamAV
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/ClamAV/intermediate/binary/clamscan ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/ClamAV/intermediate/asm -nonpie -Ofast -name clamscan
# d
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/d/intermediate/binary/make_dparser ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/d/intermediate/asm -nonpie -Ofast -name d
# lemon
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/lemon/intermediate/binary/lemon ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/lemon/intermediate/asm -nonpie -Ofast -name lemon
# lua
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/lua/intermediate/binary/lua ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/lua/intermediate/asm -nonpie -Ofast -name lua
# obsequi
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/obsequi/intermediate/binary/Obsequi ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/obsequi/intermediate/asm -nonpie -Ofast -name Obsequi
# sgefa
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/sgefa/intermediate/binary/sgefa ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/sgefa/intermediate/asm -nonpie -Ofast -name sgefa
# SIBsim4
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/SIBsim4/intermediate/binary/SIBsim4 ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/SIBsim4/intermediate/asm -nonpie -Ofast -name SIBsim4
# siod
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/siod/intermediate/binary/siod ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/siod/intermediate/asm -nonpie -Ofast -name siod
# SPASS
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/SPASS/intermediate/binary/SPASS ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/SPASS/intermediate/asm -nonpie -Ofast -name SPASS
# spiff
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/spiff/intermediate/binary/spiff ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/spiff/intermediate/asm -nonpie -Ofast -name spiff
# sqlite3
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/sqlite3/intermediate/binary/sqlite3 ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/sqlite3/intermediate/asm -nonpie -Ofast -name sqlite3
# viterbi
bash ./threshold.sh ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/viterbi/intermediate/binary/viterbi ./weight_database/llvm-test-suite/multisource-build-Ofast/MultiSource/Applications/viterbi/intermediate/asm -nonpie -Ofast -name viterbi
```

#### 6\. logs汇总数据统计

```bash
# EviProject根目录执行
mv ./logs ./weight-logs
cp ./tools/summarize_threshold_stats.py ./
# 按照绝对地址就是复制这个脚本：cp EviProject/tools/summarize_threshold_stats.py EviProject/
python3 summarize_threshold_stats.py
# 生成的汇总数据位于weight.txt以及weight.xlsx中
```

# 第四章 符号化准确率复现

## 一、功能介绍

### 核心功能

- 复现符号化准确性实验数据

### 依赖工具

- evisymbol：核心工具，用于二进制重写场景下的立即数符号化决策。
- reassessor：用于生成符号化 ground truth（基准数据），用于准确率验证与对比。
- SPEC CPU2006：用于大规模基准测试，验证工具在真实场景下的性能。
- coreutils/binutils：补充基准测试场景，覆盖不同类型的二进制程序。

## 二、环境准备

### 1. EviSymbol安装

参考前述EviSymbol安装

### 2. reassessor 环境安装

reassessor 依赖 pyelftools (≥ 0.29) 和 capstone (≥4.0.2)，其中 capstone 需指定版本 5.0.0.post1（5.0.1 与 angr 存在兼容性问题）：

```bash
# 进入reassessor
cd EviProject/reassessor

# 安装依赖
sudo pip3 install -r requirements.txt

# 安装 reassessor
python3 setup.py install --user

# 安装指定版本 capstone（解决兼容性问题，理论上Evisymbol已完成安装，由于安装 reassessor可能覆盖原有安装结果，建议重装）
# 验证capstone版本是否为5.0.0.post1
pip3 show capstone
pip3 uninstall capstone
pip3 install capstone==5.0.0.post1
```

### 3. SPEC2006 环境安装

SPEC2006 运行需依赖 gcc-4.9 及以下版本，同时需处理 Ubuntu 18.04 的软件源问题，步骤如下：

#### 3.1 获取SPEC 2006

```bash
# 进入项目根目录
cd EviProject
mkdir accuracy_database
cd accuracy_database
# 下载获取SPEC2006至此

# 进入spec
cd ./speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1
```

#### 3.2 安装 gcc-4.9 系列编译器

（若已安装，可跳过该步骤）

```bash
# 修改软件源（解决 Ubuntu 18.04 无 gcc-4.9 候选问题）
sudo gedit /etc/apt/sources.list

# 在文件末尾添加以下源
deb http://dk.archive.ubuntu.com/ubuntu/ xenial main
deb http://dk.archive.ubuntu.com/ubuntu/ xenial universe

# 更新源
sudo apt update

# 安装 gcc-4.9、g++-4.9、gfortran-4.9
sudo apt install g++-4.9
sudo apt install gcc-4.9
sudo apt install gfortran-4.9

# 查看编译器安装位置
which {gcc,g++,gfortran}-4.9

# 切换默认编译器版本（若当前版本不是 4.9）
# 切换 gcc
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-7 50
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-4.9 40
sudo update-alternatives --config gcc  # 输入 4.9 版本对应的序号

# 切换 g++
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-7 50
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-4.9 40
sudo update-alternatives --config g++  # 输入 4.9 版本对应的序号

# 切换 gfortran
sudo apt install gfortran  # 若未安装 gfortran 先执行此步骤
sudo update-alternatives --install /usr/bin/gfortran gfortran /usr/bin/gfortran-7 50
sudo update-alternatives --install /usr/bin/gfortran gfortran /usr/bin/gfortran-4.9 40
sudo update-alternatives --config gfortran  # 输入 4.9 版本对应的序号

# 验证默认版本（均需显示 4.9）
gcc --version
g++ --version
gfortran --version
```

#### 3.3 安装交叉编译工具

```bash
sudo apt install -y {gcc,g++,gfortran}-4.9-aarch64-linux-gnu
```

#### 3.4 编译安装 SPEC2006

```bash
# 进入 SPEC2006 工具源码目录
speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1$ cd ./tools/src

# 替换写好的Ubuntu18下的buildtools文件
mv ./buildtools "./buildtools(copy)"
cp ../../../../../tools/spec_tools/buildtools ./
# 执行 buildtools 脚本（Ubuntu 18.04 需修改脚本解决兼容性问题）
sudo bash ./buildtools

# 若遇到 Permission denied 问题（如 ./configure: Permission denied），修改 buildtools 脚本：
# 在 ./configure 前添加 chmod +x ./configure，示例：
# LIBS="$ALLLIBS $MAKELIBS"; export LIBS
# chmod +x ./configure  # 新增该行
# ./configure $CONFIGFLAGS $MAKECONFFLAGS --prefix=$INSTALLDIR;

# 若遇到 undefined reference to `__alloca' in gloc.c 问题：
# 找到 glob.c 文件，在最顶部添加：#define __alloca alloca
```

#### 3.5 配置SPEC2006配置文件

根据实际需要可选配置，若要复现完整实验则均需配置，其中编译器路径修改保持一致，不同配置文件间仅编译选项不同

##### （1）nonpie-O0-nonstripped配置

```bash
# 进入 config 目录，复制配置文件模板并修改
cd EviProject/accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/config
cp linux64-amd64-gcc42.cfg nonpie-O0-nonstripped-linux64-amd64-gcc42.cfg

# 修改配置文件中的编译器路径
# 原配置（注释掉）：
# CC           = /usr/local/sles9/gcc42-0325/bin/gcc
# CXX          = /usr/local/sles9/gcc42-0325/bin/g++
# FC           = /usr/local/sles9/gcc42-0325/bin/gfortran
# 修改后：
CC           = /usr/bin/gcc-4.9
CXX          = /usr/bin/g++-4.9 -include cstddef -include cstdlib -include cstring
FC           = /usr/bin/gfortran-4.9

# 原配置（注释掉）：
# COPTIMIZE     = -O2
# CXXOPTIMIZE  = -O2 
# FOPTIMIZE    = -O2
# 修改后：
COPTIMIZE     = -O0 -g -save-temps=obj
CXXOPTIMIZE  = -O0 -g -save-temps=obj
FOPTIMIZE    = -O0 -g -save-temps=obj
```

##### （2）nonpie-O1-nonstripped配置

```bash
# 进入 config 目录，复制配置文件模板并修改
cd EviProject/accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/config
cp linux64-amd64-gcc42.cfg nonpie-O1-nonstripped-linux64-amd64-gcc42.cfg

# 修改配置文件中的编译器路径
# 原配置（注释掉）：
# CC           = /usr/local/sles9/gcc42-0325/bin/gcc
# CXX          = /usr/local/sles9/gcc42-0325/bin/g++
# FC           = /usr/local/sles9/gcc42-0325/bin/gfortran
# 修改后：
CC           = /usr/bin/gcc-4.9
CXX          = /usr/bin/g++-4.9 -include cstddef -include cstdlib -include cstring
FC           = /usr/bin/gfortran-4.9

# 原配置（注释掉）：
# COPTIMIZE     = -O2
# CXXOPTIMIZE  = -O2 
# FOPTIMIZE    = -O2
# 修改后：
COPTIMIZE     = -O1 -g -save-temps=obj
CXXOPTIMIZE  = -O1 -g -save-temps=obj
FOPTIMIZE    = -O1 -g -save-temps=obj
```

##### （3）nonpie-O2-nonstripped配置

```bash
# 进入 config 目录，复制配置文件模板并修改
cd EviProject/accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/config
cp linux64-amd64-gcc42.cfg nonpie-O2-nonstripped-linux64-amd64-gcc42.cfg

# 修改配置文件中的编译器路径
# 原配置（注释掉）：
# CC           = /usr/local/sles9/gcc42-0325/bin/gcc
# CXX          = /usr/local/sles9/gcc42-0325/bin/g++
# FC           = /usr/local/sles9/gcc42-0325/bin/gfortran
# 修改后：
CC           = /usr/bin/gcc-4.9
CXX          = /usr/bin/g++-4.9 -include cstddef -include cstdlib -include cstring
FC           = /usr/bin/gfortran-4.9

# 原配置（注释掉）：
# COPTIMIZE     = -O2
# CXXOPTIMIZE  = -O2 
# FOPTIMIZE    = -O2
# 修改后：
COPTIMIZE     = -O2 -g -save-temps=obj
CXXOPTIMIZE  = -O2 -g -save-temps=obj
FOPTIMIZE    = -O2 -g -save-temps=obj
```

##### （4）nonpie-O3-nonstripped配置

```bash
# 进入 config 目录，复制配置文件模板并修改
cd EviProject/accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/config
cp linux64-amd64-gcc42.cfg nonpie-O3-nonstripped-linux64-amd64-gcc42.cfg

# 修改配置文件中的编译器路径
# 原配置（注释掉）：
# CC           = /usr/local/sles9/gcc42-0325/bin/gcc
# CXX          = /usr/local/sles9/gcc42-0325/bin/g++
# FC           = /usr/local/sles9/gcc42-0325/bin/gfortran
# 修改后：
CC           = /usr/bin/gcc-4.9
CXX          = /usr/bin/g++-4.9 -include cstddef -include cstdlib -include cstring
FC           = /usr/bin/gfortran-4.9

# 原配置（注释掉）：
# COPTIMIZE     = -O2
# CXXOPTIMIZE  = -O2 
# FOPTIMIZE    = -O2
# 修改后：
COPTIMIZE     = -O3 -g -save-temps=obj
CXXOPTIMIZE  = -O3 -g -save-temps=obj
FOPTIMIZE    = -O3 -g -save-temps=obj
```

##### （5）nonpie-Os-nonstripped配置

```bash
# 进入 config 目录，复制配置文件模板并修改
cd EviProject/accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/config
cp linux64-amd64-gcc42.cfg nonpie-Os-nonstripped-linux64-amd64-gcc42.cfg

# 修改配置文件中的编译器路径
# 原配置（注释掉）：
# CC           = /usr/local/sles9/gcc42-0325/bin/gcc
# CXX          = /usr/local/sles9/gcc42-0325/bin/g++
# FC           = /usr/local/sles9/gcc42-0325/bin/gfortran
# 修改后：
CC           = /usr/bin/gcc-4.9
CXX          = /usr/bin/g++-4.9 -include cstddef -include cstdlib -include cstring
FC           = /usr/bin/gfortran-4.9

# 原配置（注释掉）：
# COPTIMIZE     = -O2
# CXXOPTIMIZE  = -O2 
# FOPTIMIZE    = -O2
# 修改后：
COPTIMIZE     = -Os -g -save-temps=obj
CXXOPTIMIZE  = -Os -g -save-temps=obj
FOPTIMIZE    = -Os -g -save-temps=obj
```

##### （6）nonpie-Ofast-nonstripped配置

```bash
# 进入 config 目录，复制配置文件模板并修改
cd EviProject/accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/config
cp linux64-amd64-gcc42.cfg nonpie-Ofast-nonstripped-linux64-amd64-gcc42.cfg

# 修改配置文件中的编译器路径
# 原配置（注释掉）：
# CC           = /usr/local/sles9/gcc42-0325/bin/gcc
# CXX          = /usr/local/sles9/gcc42-0325/bin/g++
# FC           = /usr/local/sles9/gcc42-0325/bin/gfortran
# 修改后：
CC           = /usr/bin/gcc-4.9
CXX          = /usr/bin/g++-4.9 -include cstddef -include cstdlib -include cstring
FC           = /usr/bin/gfortran-4.9

# 原配置（注释掉）：
# COPTIMIZE     = -O2
# CXXOPTIMIZE  = -O2 
# FOPTIMIZE    = -O2
# 修改后：
COPTIMIZE     = -Ofast -g -save-temps=obj
CXXOPTIMIZE  = -Ofast -g -save-temps=obj
FOPTIMIZE    = -Ofast -g -save-temps=obj
```

##### （7）pie-O0-nonstripped配置

```bash
# 进入 config 目录，复制配置文件模板并修改
cd EviProject/accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/config
cp linux64-amd64-gcc42.cfg pie-O0-nonstripped-linux64-amd64-gcc42.cfg

# 修改配置文件中的编译器路径
# 原配置（注释掉）：
# CC           = /usr/local/sles9/gcc42-0325/bin/gcc
# CXX          = /usr/local/sles9/gcc42-0325/bin/g++
# FC           = /usr/local/sles9/gcc42-0325/bin/gfortran
# 修改后：
CC           = /usr/bin/gcc-4.9
CXX          = /usr/bin/g++-4.9 -include cstddef -include cstdlib -include cstring
FC           = /usr/bin/gfortran-4.9

# 原配置（注释掉）：
# COPTIMIZE     = -O2
# CXXOPTIMIZE  = -O2 
# FOPTIMIZE    = -O2
# 修改后：
COPTIMIZE     = -O0 -fPIE -pie -g -save-temps=obj
CXXOPTIMIZE  = -O0 -fPIE -pie -g -save-temps=obj
FOPTIMIZE    = -O0 -fPIE -pie -g -save-temps=obj
```

##### （8）pie-O1-nonstripped配置

```bash
# 进入 config 目录，复制配置文件模板并修改
cd EviProject/accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/config
cp linux64-amd64-gcc42.cfg pie-O1-nonstripped-linux64-amd64-gcc42.cfg

# 修改配置文件中的编译器路径
# 原配置（注释掉）：
# CC           = /usr/local/sles9/gcc42-0325/bin/gcc
# CXX          = /usr/local/sles9/gcc42-0325/bin/g++
# FC           = /usr/local/sles9/gcc42-0325/bin/gfortran
# 修改后：
CC           = /usr/bin/gcc-4.9
CXX          = /usr/bin/g++-4.9 -include cstddef -include cstdlib -include cstring
FC           = /usr/bin/gfortran-4.9

# 原配置（注释掉）：
# COPTIMIZE     = -O2
# CXXOPTIMIZE  = -O2 
# FOPTIMIZE    = -O2
# 修改后：
COPTIMIZE     = -O1 -fPIE -pie -g -save-temps=obj
CXXOPTIMIZE  = -O1 -fPIE -pie -g -save-temps=obj
FOPTIMIZE    = -O1 -fPIE -pie -g -save-temps=obj
```

##### （9）pie-O2-nonstripped配置

```bash
# 进入 config 目录，复制配置文件模板并修改
cd EviProject/accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/config
cp linux64-amd64-gcc42.cfg pie-O2-nonstripped-linux64-amd64-gcc42.cfg

# 修改配置文件中的编译器路径
# 原配置（注释掉）：
# CC           = /usr/local/sles9/gcc42-0325/bin/gcc
# CXX          = /usr/local/sles9/gcc42-0325/bin/g++
# FC           = /usr/local/sles9/gcc42-0325/bin/gfortran
# 修改后：
CC           = /usr/bin/gcc-4.9
CXX          = /usr/bin/g++-4.9 -include cstddef -include cstdlib -include cstring
FC           = /usr/bin/gfortran-4.9

# 原配置（注释掉）：
# COPTIMIZE     = -O2
# CXXOPTIMIZE  = -O2 
# FOPTIMIZE    = -O2
# 修改后：
COPTIMIZE     = -O2 -fPIE -pie -g -save-temps=obj
CXXOPTIMIZE  = -O2 -fPIE -pie -g -save-temps=obj
FOPTIMIZE    = -O2 -fPIE -pie -g -save-temps=obj
```

##### （10）pie-O3-nonstripped配置

```bash
# 进入 config 目录，复制配置文件模板并修改
cd EviProject/accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/config
cp linux64-amd64-gcc42.cfg pie-O3-nonstripped-linux64-amd64-gcc42.cfg

# 修改配置文件中的编译器路径
# 原配置（注释掉）：
# CC           = /usr/local/sles9/gcc42-0325/bin/gcc
# CXX          = /usr/local/sles9/gcc42-0325/bin/g++
# FC           = /usr/local/sles9/gcc42-0325/bin/gfortran
# 修改后：
CC           = /usr/bin/gcc-4.9
CXX          = /usr/bin/g++-4.9 -include cstddef -include cstdlib -include cstring
FC           = /usr/bin/gfortran-4.9

# 原配置（注释掉）：
# COPTIMIZE     = -O2
# CXXOPTIMIZE  = -O2 
# FOPTIMIZE    = -O2
# 修改后：
COPTIMIZE     = -O3 -fPIE -pie -g -save-temps=obj
CXXOPTIMIZE  = -O3 -fPIE -pie -g -save-temps=obj
FOPTIMIZE    = -O3 -fPIE -pie -g -save-temps=obj
```

##### （11）pie-Os-nonstripped配置

```bash
# 进入 config 目录，复制配置文件模板并修改
cd EviProject/accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/config
cp linux64-amd64-gcc42.cfg pie-Os-nonstripped-linux64-amd64-gcc42.cfg

# 修改配置文件中的编译器路径
# 原配置（注释掉）：
# CC           = /usr/local/sles9/gcc42-0325/bin/gcc
# CXX          = /usr/local/sles9/gcc42-0325/bin/g++
# FC           = /usr/local/sles9/gcc42-0325/bin/gfortran
# 修改后：
CC           = /usr/bin/gcc-4.9
CXX          = /usr/bin/g++-4.9 -include cstddef -include cstdlib -include cstring
FC           = /usr/bin/gfortran-4.9

# 原配置（注释掉）：
# COPTIMIZE     = -O2
# CXXOPTIMIZE  = -O2 
# FOPTIMIZE    = -O2
# 修改后：
COPTIMIZE     = -Os -fPIE -pie -g -save-temps=obj
CXXOPTIMIZE  = -Os -fPIE -pie -g -save-temps=obj
FOPTIMIZE    = -Os -fPIE -pie -g -save-temps=obj
```

##### （12）pie-Ofast-nonstripped配置

```bash
# 进入 config 目录，复制配置文件模板并修改
cd EviProject/accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/config
cp linux64-amd64-gcc42.cfg pie-Ofast-nonstripped-linux64-amd64-gcc42.cfg

# 修改配置文件中的编译器路径
# 原配置（注释掉）：
# CC           = /usr/local/sles9/gcc42-0325/bin/gcc
# CXX          = /usr/local/sles9/gcc42-0325/bin/g++
# FC           = /usr/local/sles9/gcc42-0325/bin/gfortran
# 修改后：
CC           = /usr/bin/gcc-4.9
CXX          = /usr/bin/g++-4.9 -include cstddef -include cstdlib -include cstring
FC           = /usr/bin/gfortran-4.9

# 原配置（注释掉）：
# COPTIMIZE     = -O2
# CXXOPTIMIZE  = -O2 
# FOPTIMIZE    = -O2
# 修改后：
COPTIMIZE     = -Ofast -fPIE -pie -g -save-temps=obj
CXXOPTIMIZE  = -Ofast -fPIE -pie -g -save-temps=obj
FOPTIMIZE    = -Ofast -fPIE -pie -g -save-temps=obj
```

#### 3.6 配置 SPEC2006 环境变量

```bash
# 进入 SPEC2006 根目录
cd EviProject/accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1

# 配置环境变量（每次打开终端运行spec时需重新执行）
source ./shrc
```

### 4. coreutils 环境安装

安装路径：EviProject/accuracy_database（根目录下需提前创建accuracy_database文件夹）

下载编译好的所需文件：直接下载公布好得基准数据集即可[Reassembly is Hard: A Reflection on Challenges and Strategies](https://zenodo.org/records/7178116)

## 三、代码运行指南

#### 1\. evisymbol.py

 - 功能：该 Python 脚本用于分析二进制文件，并提取满足特定证据条件的立即数。
 - 使用方法：`python3 ./evisymbol/evisymbol.py <binary_file_path> <asm_path> ` 
 - 输入：二进制文件 <binary_file_path> 和要生成的目标汇编文件自定义路径。
 - 输出：符号化信息文件，标记每条指令的立即数及其对应的证据类型。
 - 运行示例：`python3 ./evisymbol/evisymbol.py ./demos/cpp_demo/bin/simple_inheritance ./evi.s`

#### 2\. evisymbol.sh

 - 自动化调度运行 evisymbol.py，自动创建日志目录、保存运行日志与结果文件
 - 使用方法：`bash evisymbol.sh <stripped_binary_path> [-pie|-nonpie] [-O0|-O1|-O2|-O3|-Os|-Ofast] [-name program]`

 - 输入：已剥离二进制文件路径，可选传入编译模式、优化等级、程序名称等参数。
 - 输出：自动生成带时间戳与参数标识的日志文件夹，保存完整运行日志及分析结果。
 - 运行示例：`bash ./evisymbol.sh ./demos/switch_demo-PIC/bin/hello-stripped -pie -O2 -name switch_demo`

#### 3\. symbolGT.sh

 - 功能：生成ground truth 数据文件。
 - 使用方法：`bash symbolGT.sh <binary_file_path> <asm_directory_path>`
 - 输入：未剥离二进制文件和编译生成的汇编文件所在目录。
 - 输出：ground truth 数据文件，记录程序中每条指令对应的符号化信息。
 - 运行示例：`bash ./symbolGT.sh ./demos/switch_demo-PIC/bin/hello-nonstripped ./demos/switch_demo-PIC/asm/`

#### 4\. eviaccuracy.sh

 - 功能：该脚本用于统计每种类型识别的准确度。
 - 使用方法：`bash eviaccuracy.sh <stripped_binary_path> <unstripped_binary_path> <asm_dir_path> [-pie|-nonpie] [-O0|-O1|-O2|-O3|-Os|-Ofast] [-name program]`
 - 输入：须传入剥离二进制文件、未剥离二进制文件、编译生成的汇编文件所在目录，后面的 `-pie/-nonpie`、优化等级、`-name 程序名` 均为选填参数，主要用于自动生成日志名称。
 - 输出：对应的符号化准确率结果。
 - 运行示例：`bash ./eviaccuracy.sh ./demos/cpp_demo/bin/simple_inheritance ./demos/cpp_demo/bin/simple_inheritance ./demos/cpp_demo/asm -nonpie -O0 -name inheritance`

## 四、实验数据复现

准确率复现分为 SPEC2006（单个/集体）、coreutils/binutils 三个场景，核心是通过脚本对比 EviSymbol 符号化结果与 ground truth，统计准确率。

#### 1\. SPEC2006 准确率（单个复现）

##### （1）编译473程序获得未剥离的二进制文件和汇编文件

```bash
# 1. 编译 473.astar 未剥离版本（nonstripped）
cd EviProject/accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1
source ./shrc
runspec -a build -c nonpie-O0-nonstripped-linux64-amd64-gcc42.cfg -i ref --tuning=base 473

# 整理未剥离版本的二进制文件和汇编文件
cd ./benchspec/CPU2006/473.astar/exe/
mkdir nonpie && cd nonpie && mkdir O0
mv astar_base.amd64-m64-gcc42-nn O0/nonstripped

cd /benchspec/CPU2006/473.astar/run/
mkdir nonpie && cd nonpie && mkdir O0
mv build_base_amd64-m64-gcc42-nn.0000 O0/nonstripped
cd O0/nonstripped
mkdir -p intermediate/asm
find . -name "*.s" -exec mv {} intermediate/asm/ \;
```

##### （2）编译473程序获得剥离的二进制文件

```bash
# 编译 473.astar 剥离版本（stripped）
cd EviProject/accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1
source ./shrc
runspec -a build -c nonpie-O0-stripped-linux64-amd64-gcc42.cfg -i ref --tuning=base 473

# 整理剥离版本的二进制文件和汇编文件
cd ./benchspec/CPU2006/473.astar/exe/
cd nonpie
mv astar_base.amd64-m64-gcc42-nn O0/stripped
```

##### （3）计算准确率

```bash
# 计算准确率（未剥离符号信息的准确率）
bash ./eviaccuracy.sh ./speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/benchspec/CPU2006/473.astar/exe/nonpie/O0/nonstripped ./speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/benchspec/CPU2006/473.astar/exe/nonpie/O0/nonstripped ./speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/benchspec/CPU2006/473.astar/run/nonpie/O0/nonstripped/intermediate/asm/

# 计算准确率（剥离符号信息的准确率）
bash ./eviaccuracy.sh ./speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/benchspec/CPU2006/473.astar/exe/nonpie/O0/stripped ./speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/benchspec/CPU2006/473.astar/exe/nonpie/O0/nonstripped ./speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1/benchspec/CPU2006/473.astar/run/nonpie/O0/nonstripped/intermediate/asm/
```

#### 2\. SPEC2006 准确率（集体复现）

##### （1）准备配置文件

```bash
# 配置文件模板修改参考前节，需准备以下配置文件（共12个）：
# nonpie 未剥离：nonpie-O0~Ofast-nonstripped-linux64-amd64-gcc42.cfg
# nonpie 剥离：nonpie-O0~Ofast-stripped-linux64-amd64-gcc42.cfg
```

##### （2）批量编译未剥离nonPIE文件

注意：建议开两个终端**（按顺序执行，终端1命令执行完了再执行终端2的命令）**

- 终端1目录：EviProject/accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1
- 终端2目录：EviProject/tools/spec_tools

```bash
# nonpie-O0-nonstripped
# 终端1：编译生成二进制文件及中间文件
终端1$ source ./shrc
终端1$ runspec -a build -c nonpie-O0-nonstripped-linux64-amd64-gcc42.cfg -i ref --tuning=base all
# 终端2：重新组织生成的二进制文件和过程汇编文件结构，便于后续操作
终端2$ bash ./organize_spec_binaries.sh nonpie O0 nonstripped

# nonpie-O1-nonstripped（执行时长约半小时）
终端1$ runspec -a build -c nonpie-O1-nonstripped-linux64-amd64-gcc42.cfg -i ref --tuning=base all
终端2$ bash ./organize_spec_binaries.sh nonpie O1 nonstripped

# nonpie-O2-nonstripped（执行时长约半小时）
终端1$ runspec -a build -c nonpie-O2-nonstripped-linux64-amd64-gcc42.cfg -i ref --tuning=base all
终端2$ bash ./organize_spec_binaries.sh nonpie O2 nonstripped

# nonpie-O3-nonstripped（执行时长约半小时）
终端1$ runspec -a build -c nonpie-O3-nonstripped-linux64-amd64-gcc42.cfg -i ref --tuning=base all
终端2$ bash ./organize_spec_binaries.sh nonpie O3 nonstripped

# nonpie-Os-nonstripped（执行时长约半小时）
终端1$ runspec -a build -c nonpie-Os-nonstripped-linux64-amd64-gcc42.cfg -i ref --tuning=base all
终端2$ bash ./organize_spec_binaries.sh nonpie Os nonstripped

# nonpie-Ofast-nonstripped（执行时长约半小时）
终端1$ runspec -a build -c nonpie-Ofast-nonstripped-linux64-amd64-gcc42.cfg -i ref --tuning=base all
终端2$  bash ./organize_spec_binaries.sh nonpie Ofast nonstripped
```

##### （3）批量编译未剥离PIE文件（按顺序执行）

注意：建议开两个终端

- 终端1目录：EviProject/accuracy_database/speccpu2006-v1.0.1-newest/speccpu2006-v1.0.1
- 终端2目录：EviProject/tools/spec_tools

```bash
# pie-O0-nonstripped
# 终端1：编译生成二进制文件及中间文件
终端1$ source ./shrc
终端1$ runspec -a build -c pie-O0-nonstripped-linux64-amd64-gcc42.cfg -i ref --tuning=base all
# 终端2：重新组织生成的二进制文件和过程汇编文件结构，便于后续操作
终端2$ bash ./organize_spec_binaries.sh pie O0 nonstripped

# pie-O1-nonstripped
终端1$ runspec -a build -c pie-O1-nonstripped-linux64-amd64-gcc42.cfg -i ref --tuning=base all
终端2$ bash ./organize_spec_binaries.sh pie O1 nonstripped

# pie-O2-nonstripped
终端1$ runspec -a build -c pie-O2-nonstripped-linux64-amd64-gcc42.cfg -i ref --tuning=base all
终端2$ bash ./organize_spec_binaries.sh pie O2 nonstripped

# pie-O3-nonstripped
终端1$ runspec -a build -c pie-O3-nonstripped-linux64-amd64-gcc42.cfg -i ref --tuning=base all
myProject/tools/spec_tools$ bash ./organize_spec_binaries.sh pie O3 nonstripped

# pie-Os-nonstripped
终端1$ runspec -a build -c pie-Os-nonstripped-linux64-amd64-gcc42.cfg -i ref --tuning=base all
终端2$ bash ./organize_spec_binaries.sh pie Os nonstripped

# pie-Ofast-nonstripped
终端1$ runspec -a build -c pie-Ofast-nonstripped-linux64-amd64-gcc42.cfg -i ref --tuning=base all
终端2$ bash ./organize_spec_binaries.sh pie Ofast nonstripped
```

##### （4）获取剥离后的nonPIE和PIE文件

```bash
# 剥离nonstripped得符号信息，生成stripped文件
cd EviProject/tools/spec_tools
bash ./prepare_stripped_bins.sh
```

##### （5）批量运行获取spec准确率

```bash
cd EviProject

# 清空logs目录（谨慎：会删除所有文件，建议logs重命名备份）
rm -rf EviProject/logs/*
# 复制测试脚本至当前工作目录
EviProject$ cp ./tools/run_spec_accuracy.sh ./

# 执行批量准确率测试脚本
# 预计耗时：约 48 小时
EviProject$ bash ./run_spec_accuracy.sh
```

##### （6）整理统计数据

```bash
# 注意：默认整理 logs 文件夹下的所有日志文件；若已将 logs 重命名为 spec-logs，请修改 summarize_symbolization_logs.py 中的 LOG_ROOT 变量路径

# 进入工具目录
cd EviProject/tools

# 执行日志统计分析脚本
EviProject/tools$ python3 summarize_symbolization_logs.py

# 统计结果输出文件
# 详细结果：EviProject/tools/accuracy.txt
# 汇总表格：EviProject/tools/accuracy_summary.xlsx
```

#### 3\. coreutils/binutils 准确率复现

##### （1）前置准备工作

- 改名：把EviProject/accuracy_database/benchmark的所有nopie文件夹改成nonpie文件夹**（纯属作者习惯，若想复现必须改）**

- 改名：把EviProject/accuracy_database/benchmark的所有优化级别开头命名的文件夹小写o改成大写O，例如o1-bfd改成O1-bfd**（纯属作者习惯，若想复现必须改）**

##### （2）批量运行获取coreutils/binutils准确率

```bash
cd EviProject

# 手动清空 EviProject/logs 目录下的所有内容
# 复制测试脚本至当前工作目录
EviProject$ cp ./tools/run_benchmarks_accuracy.sh ./

# 执行批量准确率测试脚本
# 预计耗时：coreutils（24小时）+ binutils（39小时），总计约63小时
# 如需单独运行某一项，可注释脚本中 BASES 数组内对应条目
EviProject$ bash ./run_benchmarks_accuracy.sh
```

##### （3）整理统计数据

```bash
# 注意：默认整理 logs 文件夹下的所有日志文件；若已将 logs 重命名为 benchmark-logs，请修改 summarize_symbolization_logs.py 中的 LOG_ROOT 变量路径

# 进入工具目录
cd EviProject/tools

# 执行日志统计分析脚本
EviProject/tools$ python3 summarize_symbolization_logs.py

# 统计结果输出文件
# 详细结果：EviProject/tools/accuracy.txt
# 汇总表格：EviProject/tools/accuracy_summary.xlsx
```

#### 4\. 所有数据准确率复现

```bash
# 将spec、coreutils、binutils生成的所有日志放置到同一个logs文件夹中

# 进入工具目录
cd EviProject/tools

# 执行日志统计分析脚本
EviProject/tools$ python3 summarize_symbolization_logs.py

# 统计结果输出文件
# 详细结果：EviProject/tools/accuracy.txt
# 汇总表格：EviProject/tools/accuracy_summary.xlsx
```

##  五、注意事项

- 所有脚本执行前，需确保路径正确（替换为你的实际文件路径），避免因路径错误导致脚本执行失败。
- SPEC2006 编译时间较长（单次编译约 30 分钟），建议按顺序执行编译命令，避免并行编译导致的资源不足。
- capstone 版本必须为 5.0.0.post1，否则会与 angr 产生兼容性问题，导致程序报错。
- 每次打开终端运行 SPEC2006 相关命令前，需先执行`source ./shrc` 配置环境变量。
- 复现过程中产生的日志文件、中间文件建议妥善保存，便于后续问题排查和结果验证。

# 第五章 补充说明

- 完整复现时长较长，大约用时如下：
  - 虚拟机+环境安装：约12小时
  - 证据权重统计复现：
    - findutils/sed/grep/gawk程序下载/安装/编译/复现实验：约3小时
    - llvm-test-suite程序下载/安装：约1个小时
    - llvm-test-suite程序编译/复现实验：约三个半小时
  - 符号化准确率复现：
    - spec编译成各个优化级别的pie和nonpie二进制文件：约7小时
    - 运行spec实验：约48小时
    - 运行coreutils实验：约24小时
    - 运行binutils实验：约39小时
