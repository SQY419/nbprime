# PrimeC

一个为 HP Prime 设计的微型自托管 C 编译器。  
可直接在计算器上编辑 C 代码，在设备本地编译，并通过 Prime 现有的 ELF 加载器运行生成的 ARM 机器码。

## 目录结构
- `main.py`       MicroPython 启动器 / ELF 加载器（接口保持不变）
- `primec.py`     C 词法分析器、语法分析器、ARMv5TEJ 代码生成器、ELF 写入器
- `ccode.py`      在计算器上直接编辑此文件（存放 C 源码）
- `ccode.elf`     由 main.py 生成
- `Makefile`      主机端便捷构建目标

## ccode.py 文件格式
C 源码必须放在如下标记之间：

```c
/* PRIME-C-CODE-BEGIN */
...
/* PRIME-C-CODE-END */
