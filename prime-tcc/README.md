# primetcc — TCC (TinyCC) 移植到 HP Prime G1 计算器

在 **HP Prime G1**（ARM926EJ-S / ARMv5TEJ, 软浮点）上运行的**TinyCC (mob / master)** 移植。TCC 本体交叉编译为单文件 ELF，由计算器上的MicroPython 加载器（shellcode）装入内存运行；在计算器上把用户 C 源码编译成ARM ELF（`code.elf`），再用同一个加载器运行它，输出通过 PRIMELOG 环形缓冲回显。

```
在计算器上:  写 C 源码 (main.py 的 PRIME-C-CODE 区段)
             └─► TCC (tcc.elf, 在计算器上运行)
                  │  -nostdlib -shared -Wl,-e,hp_entry
                  │  -I . code.c rt_core.o rt_svc.o rt_aeabi.o rt_math.o
                  ▼
             code.elf ──► shellcode loader ──► hp_entry ──► main()
                       └─► PRIMELOG 输出 / 安全拆钩子 / 安全释放
```

只有用户的 `code.c` 在计算器上编译。
运行时（`rt/` 下的 hp_rt/hp_gfx/hp_input/hp_math/hp_string）主机侧预编译成 **`rt_core.o`**，编译耗时因此降到原来的约 1/4。

## 目录

```
primetcc/
├── API.md             每个头文件的函数用法速查（新手从这里开始）
├── Makefile            构建（主机侧交叉编译）
├── hp/
│   ├── hp_libc.h       迷你 C 运行库声明（TCC 二进制自己用的）
│   ├── hp_libc.c       文件IO/内存/字符串/exit… 全部走固件 SVC
│   ├── hp_vsnprintf.c  vsnprintf 核心
│   ├── hp_svc.s        SVC 包装 (push{r0};push{lr};svc N) + setjmp/longjmp + crt0
│   ├── prime.h         用户程序头文件（TCC 编译的用户代码用）
│   └── include/        给 TCC 源码编译用的桩头文件 (stdio.h 等, 遮蔽 newlib)
├── rt/                 用户程序运行时源码（预编译进 rt_core.o）
│   ├── hp_rt.c         printf→PRIMELOG、malloc/free、mem/str、hp_entry 入口、
│   │                   g_hp_input（PRIMEIN 状态地址）
│   ├── hp_gfx.c/h      图形库（GROB 双缓冲、图元、5x8 字体）
│   ├── hp_input.c/h    键盘+触摸客户端（共享队列读写、槽位接管/恢复、看门狗）
│   ├── hp_input_svc.c/h 常驻输入钩子服务——**编入 tcc.elf**，槽位永远指向它
│   ├── hp_math.c/h     数学库声明（实现主体在 openlibm 的 rt_math.o）
│   ├── hp_string.c/h   字符串库（含 ftoa/dtoa 浮点格式化）
│   └── openlibm/       BSD 数学库源码（预编译成 rt_math.o, 1e-16 精度）
├── rt_core.o           预编译运行时（Makefile 生成）
├── rt_math.o           预编译数学库（openlibm, hp_* 改名）
├── rt_svc.o            用户程序的固件 SVC 包装（预编译）
├── rt_aeabi.o          libgcc 除法/软浮点辅助（预编译）
├── calc/
│   └── main.py         计算器端加载器源文件（部署版见 ../primetcc.hpappdir/）
├── tests/
│   ├── emu_arm2.py     ARMv5 解释器 + 固件 SVC 模拟（主机侧验证）
│   ├── harness.py      端到端测试（TCC 编译→加载→运行→比对输出）
│   └── restart_check.py 多轮连续运行按键可达性回归
├── src/tinycc-mob/     TCC 源码（打了少量移植补丁）
└── ../primetcc.hpappdir/   平铺部署目录（整体拷到计算器 C:\DATA\）
```

## 部署到计算器

将`primetcc.hpappdir`使用连接软件传输至计算器，或者放入`C:\DATA\`

```
C:\DATA\primetcc.hpappdir\
├── tcc.elf        TCC 编译器本体
├── main.py        加载器（写源码→调 TCC→加载运行产物→安全释放）
├── prime.h        用户程序头文件
├── hp_gfx.h / hp_input.h / hp_math.h / hp_string.h   用户程序头文件
├── rt_core.o      预编译运行时（hp_rt+hp_gfx+hp_input+hp_math+hp_string）
├── rt_math.o      预编译数学库（openlibm）
├── rt_svc.o       固件 SVC 包装（预编译）
└── rt_aeabi.o     libgcc 除法/软浮点辅助（预编译）
```

`code.c`、`code.elf` 在运行 main.py 时于计算器上生成，`tcc.slot` 记录常驻TCC 的地址，同样平铺在 `primetcc.hpappdir\` 下。

在计算器的 Python 应用里运行：

```python
import main
```

## 构建（主机侧）

需要 `arm-none-eabi-gcc`
Ubuntu: `apt install gcc-arm-none-eabi
binutils-arm-none-eabi libnewlib-arm-none-eabi`

```sh
make tcc.elf rt_core.o rt_math.o rt_svc.o rt_aeabi.o   # 全部产物
python3 tests/harness.py hello     # 主机侧端到端测试（test 列表见 harness.py）
```

重新生成部署目录：

```sh
make deploy    # 重建全部产物并拷贝到 ../primetcc.hpappdir/
```

tcc.elf 形状：ELF32 ET_DYN (PIE)、文本+数据+128KB 栈、156 条
`R_ARM_RELATIVE` 重定位——与现有 Prime shellcode loader 完全兼容。

对 TCC 源码的移植补丁（`src/tinycc-mob/`）：
1. `tcc.h`：`HP_PRIME` 宏启用反斜杠/盘符感知的路径处理（`IS_DIRSEP`/`IS_ABSPATH`）。
2. `arm-gen.c`：`o()` 参数类型 `uint32_t`→`unsigned int`（newlib 的 uint32_t 是
   unsigned long，与 tcc.h 原型冲突）。
3. `arm-link.c`：`R_ARM_V4BX` 归入 `NO_GOTPLT_ENTRY`（纯标记重定位，进 GOT 流程
   会触发 `fill_local_got_entries: huh?`）。
4. `tccrun.c`：sigaction 赋值加类型转换（裸机 newlib 的 sigaction 简化版）。

## 用户程序运行时 API

- **控制台**：`printf(fmt, ...)` / `sprintf(buf, fmt, ...)`——**源码级可变参数**
  （1..8 个值，`printf("x=%d\n", x)` 即可）。TCC-ARM 无 AAPCS 变参调用
  （后端没有 va_start 代码生成，匿名参数会进 r0-r3 而 GCC 运行时从栈上读），
  因此用 C99 变参宏按实参个数分派到固定 8 参引擎（`hp_printf8/hp_sprintf8`）。
  转换符：`%d %i %u %x %X %o %c %s %p` + `-0+空格` 标志与宽度，无 `%f`
  （浮点用 `ftoa/dtoa`）。另有 `puts`、`prints/printd/printx`。输出进
  PRIMELOG 环，main.py 彩色回显。
- **内存**：`malloc/calloc/free`（固件堆，8 字节对齐）。
- **字符串**：`strlen/strcmp/strcpy/memcpy/memset/memcmp/strncmp`（hp_rt.c）+
  `strchr/strstr/strdup/itoa/ltoa/strrev/strcasecmp` 等（hp_string.c）。
- **浮点格式化**：`ftoa(double, buf, dec)` / `dtoa`（hp_string.h）——
  定点输出 + 四舍五入，NaN→"NaN"，∞→"INF"。`hp_double_to_str`（hp_math.h）
  已收敛为 `ftoa` 的薄封装（同一实现，无行为差异）。
- **数学**：`hp_sin/cos/tan/asin/acos/atan/atan2/exp/log/log10/pow/sqrt/sinh/cosh/
  tanh/floor/ceil/fabs/trunc/round/fmod/frexp/modf/ldexp/scalbn/expm1`（rt_math.o，
  openlibm，双精度 1e-16）。
- **图形**：`hp_gfx_init/hp_clear/hp_pixel/hp_line/hp_circle/hp_rect/
  hp_fill_*`、`hp_text` + GROB 双缓冲（hp_gfx.h）。三角形：`hp_triangle`
  （3 条 Bresenham 边轮廓）与 `hp_fill_triangle`（扫描线填充，整数边插值，
  退化三角形退化为线段/单点）。GROB 几何：`hp_grob_w(g)/hp_grob_h(g)`
  （尺寸访问器，避免 TCC 代码直接摸结构体字段，`const hp_grob*` 参数与
  字体访问器一致）、`hp_target_w/h()`（当前绘制目标——屏幕或选中的
  GROB——的尺寸）。
  - **绘制效率**（参照 gbemu 的 LCD 渲染手法重写过热路径）：`get_lcd`
    只在 `hp_gfx_init` 取一次并缓存（不再每笔一 SVC）；`hp_fill_rect`/
    `hp_hline`/`hp_clear` 先整体裁剪一次，再用行指针 + 展开的字存储直接写
    显存（不再逐像素函数调用 + 逐像素越界检查）；`hp_line` 走
    Cohen–Sutherland 裁剪后无检查直写；`hp_text` 整字字形框在目标内时走
    无裁剪快速路径（列位直接落位），只有贴边/出界字符才逐像素裁剪；
    `hp_fill_circle` 半宽逐行单调递推（O(r) 而非每行重扫 O(r²)）；
    `hp_grob_blit` 按行 4 字展开拷贝。所有图元（含 `hp_grob_blit`）统一按
    **当前绘制目标**（屏幕或 GROB）裁剪与写入——`hp_grob_blit` 支持
    grob→grob 拷贝；修掉了旧的"按屏幕尺寸裁剪"在小于屏幕的 GROB 上越界
    写内存的隐患。模拟器基准前后对比见文末「图形库效率」一节。
- **定点数学**（`hp_fixmath.h`）：Q16.16 定点数（`typedef int hp_fx`）——
  `hp_fx_mul/div`（64 位中间量）、`hp_fx_sqrt`、查表+线性插值的
  `hp_fx_sin/cos`（~1e-6）、CORDIC `hp_fx_atan2`（~3e-5）、与 int/double
  互转。软浮点下游戏/图形热路径的首选（比 double 快一个数量级）。
- **随机数与噪声**（`hp_random.h`）：PCG32（`hp_rng_seed/u32/range/fx`，
  确定性可复现）+ 值噪声 `hp_noise2_fx`（整数坐标哈希 + smoothstep 双线性，
  无状态，同输入同输出）。
- **校验/编码**（`hp_codec.h`）：`hp_crc32`（IEEE，查表）、`hp_adler32`、
  `hp_hex_encode/decode`、`hp_b64_encode/decode`（含错误检测）。
- **stdlib 补全**：`strtod/atof`（浮点解析，含指数与 inf/nan，hp_string.h）、
  `qsort/bsearch`（中位数三分快排 + 插入排序兜底）与 `abs/labs`（prime.h）。
- **轻量 GUI**（`hp_gui.h`）：标签 + 按钮 + 单行文本输入（EDIT），触摸与
  键盘双驱动，回调式点击；**文本用 hp_fonts 新字体**（Montserrat 标签/按钮、
  Unifont 输入框），**整帧经 GROB 双缓冲**（`hp_gui_begin/end`，内部复用一个
  全屏后缓冲）——界面不闪烁。按键码映射 `hp_gui_key_char` 同时接受 ASCII 码与
  hp_input.h 的矩阵设备码（不同固件上报方式不同，双映射兜底）。
  示例 `examples/gui.c` 是**终端式计算器**：每次求值把 `> <表达式>` 追加在
  `= <结果>` 上方（从旧到新、可滚动历史，↑↓ 翻页），支持 `+ - * / % ^`、
  括号、一元负号与 sin/cos/tan/ln/log/sqrt/abs/floor/ceil/exp/pow(a,b)/pi/e，
  函数硬键直接插入函数名；每次按键在控制台回显 `KEY <code>`。退出键是
  **ESC / ON**——注意不要用 0x51 当退出键：那是数字 **7/Q** 键的物理码。
  输入钩子安装时**无条件重置 SPSC 队列**（上次运行 OS 卡在钩子里时会遗留
  陈旧队列导致丢键），INPUT DEAD 看门狗放宽到 ~10s 再介入。
  - **TCC-ARM 代码生成缺陷（已在 demo 规避）**：从函数指针表取目标 + 以
    double 为参数的间接调用会被 TCC-ARM 后端错误编译（目标寄存器被 double
    值覆盖，`ldr r0,[r0]` 从数值本身取指针→崩溃）。规避：函数分派改用
    switch 直接调用，不用函数指针表。
- **字体**（`hp_fonts.h`，预渲染 1-bit 位图，rt_core.o 内嵌）：
  - `hp_font_mono(size)` —— **Cascadia Code Light** 等宽（wght=350，OFL-1.1；比 JB 更窄：12px cell=7、16px cell=9，每行容纳更多字符），
    `hp_font_prop(size)` —— **Montserrat** 比例（OFL-1.1），按字号选字重：
    12px 用 wght=450、16/24/32 用 Regular，取最接近的预渲染尺寸；
  - `hp_font_draw(f, x, y, s, c)` —— 画入**当前目标**（屏幕或选中的 GROB），
    `hp_font_draw_bg` 带背景；`hp_font_w(f, s)` 文本宽度、
    `hp_font_h(f)` 行高、`hp_font_advance(f, ch)` 单字符宽；
  - 数据由 `rt/tools/fontgen2.py` 从 TTF 生成（`rt/hp_fonts_data.c`），
    全尺寸原生阈值。曾试验 2x 超采样 + 2x2 多数表决：只对"字重选得太细"
    的字体有效（会给 Semibold 增粗 ~6%、给细字体添半像素鼓包）——
    选一个原生渲染就干净的字重比事后补救更可靠；
    注意 TCC 链接器对非 static 全局的 GOT 缺陷——表用 static + 访问器函数
    （`hp_font_prop_data(i)`），位测试用掩码左移（ARM 寄存器 LSR 量为 0
    时是 LSR #32，GCC 的 `(x >> y) & 1` 重写会丢每 8 列，真机同坑）。
  - **灰度抗锯齿**：字形按 4-bit alpha 覆盖率（16 级）预渲染，
    `hp_pixel_a()` 逐像素与目标做 RGB 插值——细字重不再断笔，同一行内
    笔画粗细平滑过渡（1 位渲染下副标题 1px/2px 跳变的"不均"根源被消除）。
    数据量 ×4（rt_core.o 约 +43KB）。曾试验 1-bit 阈值与 2x 超采样，
    均无法同时满足"细、匀、不断"，最终改灰度 AA（fontgen2.py 注释留档）；
- **输入**：`hp_input_install/hp_poll_event/hp_event_key/...`（hp_input.h）。
  `hp_event_key` 返回物理扫描码 id（HP_KEY_* 宏见 hp_input.h）。
  输入钩子**常驻在 tcc.elf 里**（`rt/hp_input_svc.c`，魔数 `PRIMEIN`）：
  tcc.elf 只加载一次、永不被释放，固件 get_event 槽位（0x307fbfa0）永远指向
  常驻钩子；code.elf 只通过共享队列读写按键（main.py 把 `PRIMEIN` 状态地址
  经 r0 传给 code.elf 入口，hp_entry 存入 `g_hp_input`）。因此：
  - 程序退出/崩溃/卡死都不会让 OS 输入线程落到已释放内存——"画出画面但按键
    失效"的根因（旧架构把钩子放在每轮释放的 code.elf 里）被结构性消灭；
  - `hp_input_install` **强制接管**槽位（即使上一轮卡死留下旧补丁也直接覆盖），
    卡死后的下一轮依然能收到按键，无需复位；
  - code.elf 每轮都可无条件释放，无 leak 保留路径；
  - 退出时 teardown 恢复槽位只是礼节性操作（`RT_EXIT ok`），不再需要等
    在途钩子排空。
  注意：TCC 的 ARM 链接器不给**非 static 全局变量**生成 GOT 修复（字面量池
  全零、写地址 0 崩溃），跨文件共享值必须走函数访问器（`g_hp_input` 是
  static，经 `hp_get_input_state()` 读取）。
- **系统库**（`hp_sys.h`，rt_core.o 内嵌）：依据工作区根目录 `SYSLIB_README.md`
  与 `README.md`（PRIME_APP.DAT 逆向）实现，只暴露**已确认**的固件服务：
  - 时间：**已整体放弃**。固件 svc 0x100A5 真机调用即重启；MicroPython 无 time 模块；设备树 `\\?\` 设备中也无时钟设备。没有任何可行时间源，相关 API 已全部移除。
    tcc 自带 libc（hp_libc.c）的 `time()/gettimeofday()` 也已**去 SVC 化**（返回固定纪元 0）：否则用户程序使用 `__DATE__`/`__TIME__` 宏会触发 tccpp 调 `time()` → svc 0x100A5 → 真机重启。`localtime()` 本就返回固定值；
  - 内存：`hp_sys_malloc/calloc/realloc/free`（固件堆透传）、
    `hp_sys_max_alloc()`（二分探针，安全 alloc+free）、`hp_sys_heap_free()`（粗略）；
  - 系统：`hp_sys_sleep/get_lcd/get_event/thread_create`；
  - debug 设备：`hp_sys_debug_open()`（fopen("debug") → 0xDEADC0DE）；
  - 文件：`hp_sys_fopen`（ASCII 路径自动转 UTF-16LE，模式传 "rb"/"wb+"）等。
  电池/RTC/uptime 在 SYSLIB_README 中标记为**待真机探针**，暂未实现。
- **其它**：`__sleep(ms)`、`hp_svc_fopen/fread/fwrite`（文件 IO）。

## 已知限制

- **未定义符号 = 编译错误（已修复的真机崩溃坑）**：旧版 TCC 对 `-shared` 输出的
  强未定义符号只发警告并生成 `R_ARM_JUMP_SLOT` 重定位——而 shellcode 加载器只
  应用 `R_ARM_RELATIVE`，这类调用会跳到地址 0 让计算器**立即重启**（例：把
  `hp_font_draw` 误写成 `hp_text_draw`）。现已在 `tccelf.c` 打补丁：强未定义
  符号直接报 `undefined symbol 'x' (no dynamic linking on HP Prime -- check
  for typos)` 编译失败（弱符号仍允许）。另补上了 `rt_svc.s` 缺失的
  `hp_svc_create_thread`/`hp_svc_terminate_thread` 包装（`hp_sys.c` 引用，
  之前是潜在悬空符号）；Makefile 为 tcc.o 加了 `-MMD/-MP` 依赖跟踪
  （tcc.c 以 `#include` 聚合后端文件，改 tccelf.c 等会自动触发重建）。
- **可编译程序大小（内存受限，无硬性上限）**：实测（`tests/measure_tcc_size.py`，
  模拟器 ARM TCC）TCC 编译时的固件堆峰值 ≈ **597KB + 3.26 × 源码字节**
  （含源码缓冲、符号表、内存中的输出 ELF；用户代码 → ARM 代码约 1:1）。
  因此最大源码 ≈ `(hp_sys_max_alloc() − 597KB) / 3.26`。参考值：空闲堆 2MB →
  ~450KB 源码；4MB → ~1.05MB；6MB → ~1.7MB。编译耗时 ≈ (26M + 0.64M×KB)
  条指令，真机 100KB 源码约 1–2 秒、1MB 约 5–13 秒。TCC 无源码长度硬上限
  （输入流式读取，符号表/令牌动态增长）。
  ⚠️ `hp_sys_max_alloc()` 的探针上限已保守设为 **512KB**（固件对数百 KB
  大块 malloc/free 的行为尚未完全真机验证；demo 启动阶段不再调用它）。
- **TCC 自身用 -O0 构建**：tcc.o 在 -O1/-O2 下于模拟器中表现异常（预定义阶段
  报 `struct/union/enum already defined`，疑似 gcc 优化与符号表初始化的交互或
  模拟器指令缺口，尚未定论）。真机测试前请保持 -O0。
- **变参函数不可用**：TCC 的 ARM 后端没有 `__builtin_va_start`，因此
  `printf(fmt, ...)` 改为固定 4 参数：`printf(fmt, a0, a1, a2, a3)`，未用传 0。
- **结构体不能按值返回/传参**：TCC-ARM 的 struct-by-value return 有缺陷，用指针。
- **TCC-ARM 无原生浮点**：用户代码里的 double/float 运算经软浮点运行时
  （rt_aeabi.o）正确执行，但 TCC 不识别 `1.5f` 后缀等浮点常量语法细节。
- **`__aeabi_memset` 参数顺序（已修复）**：ARM AEABI 的 `__aeabi_memset` 签名是
  `(void *dest, size_t n, int c)`，与 C 的 `memset(s, c, n)` 顺序相反——TCC/GCC
  生成的结构体零初始化调用都按 AEABI 顺序传参。rt/hp_rt.c 曾按 C 顺序声明并直通
  `memset`，导致 `__aeabi_memset(dest, 52, 0)` 变成 `memset(dest, 52, 0)`
  （count=0 的空操作）：复合字面量临时结构体的**零值字段从未被清零**，残留栈上
  垃圾（表现为 GUI 控件 `cur` 字段读到堆指针 0x31004020、label/id/udata 读到
  编译路径的 UTF-16 残片，计算器 demo 按键全失效）。`__aeabi_memclr` 一直是对的
  （只传 n），仅 memset 一族需交换 n/c；已修复并在 `gui` 回归中验证。
- 用户程序不链接标准库：`-nostdlib`，只提供 `rt/` 里的运行时；
  64 位除法/软浮点的 `__aeabi_*` 来自 libgcc 抽取的 `rt_aeabi.o`。
- **固件堆容量有限**：tcc.elf 与加载器现为常驻（见上文"连续运行崩溃"），
  主要堆流转是每轮的 code.elf（~230KB）。连续运行多次后固件堆碎片/耗尽仍可能
  导致 TCC 编译或程序加载阶段崩溃重启（crash.log 残留上次的 M4）。长时间使用
  后 **reset 复位**是最稳妥的做法；code.elf 的安全释放（RT_EXIT ok）与常驻
  TCC 已把可连续运行次数从 5–9 次提升到远超此数。
- **返回码恒为 2（已修复）**：固件调试接口的 `dbg.call` 对用户程序入口返回的值
  恒为 2，与程序实际返回值无关（旧版 README 误记为"忽略即可"）。现在 `hp_entry`
  把真实退出码以 `RT_RET:<n>` 写入 PRIMELOG 环，main.py 从中解析并报告
  （`user program returned: N (RT_RET; debug interface said 0x...)`）。
  模拟器直接读 r0，两种路径结果一致（`tests/harness.py ret` 验证返回 7）。
- **连续运行崩溃（已缓解）**：旧版每次运行都要在固件堆上 malloc/free 约
  900KB（tcc.elf ~675KB 镜像 + code.elf ~230KB + 加载器），5–9 次后堆碎片化
  崩溃。现在 tcc.elf 与 shellcode 加载器**常驻内存**：首次加载后把
  `{loader_addr, base, entry, log_addr}` 写入 `tcc.slot`，后续运行先校验
  加载器首指令 + ELF 魔数（重启/堆重用会使校验失败自动重载），有效则直接复用，
  每轮只剩 code.elf 的 ~230KB 流转。换了新 tcc.elf 时删除 `tcc.slot`
  （`main.reset_tcc()`）或复位计算器即可强制重载。连续运行次数由此大幅提升，
  但固件堆碎片仍不可能完全避免，长时间使用后 reset 复位仍是最稳妥的做法。
- **输入钩子已重构为常驻（根治"按键永久失效"，真机已验证）**：旧架构把
  get_event 钩子放在每轮释放的 code.elf 里。若退出时 OS 输入循环正阻塞在
  钩子中，该调用会在已释放（或被复用）的内存里醒来，输入系统跑飞；更糟的是
  槽位仍指向已挂起程序的钩子，后续运行的 `hp_input_install` 因"槽位已打补丁"
  拒绝接管，**按键永久失效、重启 Python 应用也没用**（堆复用使故障在连续多轮
  后必现，表现为"画出 sin 但按键无法退出"）。现在钩子+队列在 tcc.elf（常驻，
  魔数 `PRIMEIN`），槽位永远指向不释放的代码，install 强制接管，
  code.elf 每轮安全释放——该故障类被结构性消灭。**真机验证：连续 10+ 次运行
  按键始终正常**（`tests/restart_check.py` 在模拟器中复现同场景）。
  - 钩子运行在 OS 线程上，只做计数（hook_calls/drop_count/in_hook），**绝不做
    文件 IO**；用户程序运行时把诊断采样**逐行落盘追加到 `crash.log`**
    （固件 fopen 只认 `"rb"`/`"wb+"`，见 hp_libc.c `mode_from_flags`；
    每行读-改-写并 fclose，崩溃/reset 不丢内容，见下文）。
    注意：这些日志一律用**绝对路径** `C:\DATA\primetcc.hpappdir\`（真机上
    MicroPython 的 CWD 是上级目录，相对名 `crash.log` 会落到别的文件——
    早期"成功运行却清不掉 crash.log"就是路径不一致造成的；main.py 现在
    读写删除都先试绝对路径再退回相对名）；
  - `hp_input_install` 失败/看门狗（`INPUT DEAD`，约 1s 无钩子调用）都会在
    crash.log 留痕，便于真机排障。
- **GCC 尾调用优化已禁用**：rt_core.o 用 `-fno-optimize-sibling-calls` 编译。
  尾调用（`b func`）配合固件 SVC 的返回机制（svc 从栈弹 lr）会让执行流错乱、
  落入数据区崩溃重启——模拟器宽容处理掩盖了它，真机（及 QEMU 严格模式）会崩。
- **入口 SP 对齐**：调试接口给 code.elf 的入口 SP 可能只 4 字节对齐，而 GCC
  编译的运行时（ftoa/openlibm）用 LDRD/STRD 访问 double，要求 8 字节对齐
  （AAPCS）；ARM926EJ-S 对未对齐 LDRD/STRD 抛数据中止。`hp_entry` 先
  `bic sp, sp, #7` 对齐再进 main。
- **GCC 运行时回调 TCC 代码必须穿"寄存器防护壳"（hp_icall2）**：
  TCC 不保护 r4-r11，这不止影响 hp_entry 边界——rt_core.o（GCC）里的
  hp_gui_handle 调用 on_click（TCC 的 btn_*）后，自己的 r4（hit 指针）
  就变成了垃圾，`return hit->id` 直接野读。qsort/bsearch 的比较回调同理。
  修复：所有 GCC→TCC 间接调用统一走 hp_icall2（裸汇编在 blx 前后保存/
  恢复 r4-r11、ip、lr）。教训同源：**凡是被 TCC 代码回调的边界都要自保**。
- **屏幕按钮的完整触摸链（修复"三个按钮点不动"）**：四个环环相扣的坑——
  1. 钩子把 press/move/release 全都当普通触摸入队，release 的语义丢失，
     hp_gui_handle 永远等不到"抬起"事件 → 现在钩子只入队 press(1)/
     release(8)（丢弃 move 防洪泛），qitem 增加 action 字段；
  2. hp_poll_event 把 release 合成为 touch_count==0 的事件（这是
     hp_gui_handle 设计上触发按钮的信号）；
  3. hp_gui_handle 按下路径先 state=2 再 set_focus，而 set_focus 会把
     所有交互件重写为 0/1，刚打的"按下"标记瞬间被抹 → 先设焦点再标记；
  4. gui.c 曾在每次触摸后把按钮 state 清零 → 删除，只保留输入框焦点。
  模拟器补了 touchprobe 测试（press/release/坐标保真）+ gui 触摸点击
  "="求值、"EXIT"退出两条端到端断言。
- **ftoa 自动显示模式（dec<0）**：整数不带小数点（8 就是 "8"），非整数
  只保留有效小数并去尾零（0.1、1/3→0.333333333333333），|d|≥1e18 或
  <1e-15 转科学计数（1e+20、1.234567890123457e+22）——旧实现的
  u64 上限会打出 ">1e19"。dec≥0 的固定位数模式原样保留。
- **hp_entry 必须守住完整 AAPCS 边界- **hp_entry 必须守住完整 AAPCS 边界（修复"算完按 ESC 重启"的真凶）**：
  加载器 shellcode 按调用约定信任 r4-r11 在调用期间保持不变；而 TCC 生成的
  代码会踩花它们——算式路径（递归下降解析器 + openlibm 全部经过 TCC 代码）
  必然踩，空 main / 轻量 demo 碰巧不踩。于是：不算就正常退出，算完按 ESC
  就在 `bx lr` 之后、Python 拿回控制权之前死在加载器尾部（crash.log 有
  EXIT 无 M0、保存对完好）。修复：hp_entry 在调试栈上
  `push {r4-r11, ip, lr}`（40 字节）做完整保存，返回前原样弹回；保存对
  地址经 g_a8（.bss 全局）跨 main 传递（TCC 连 r7 都不可信）。
  EXIT 轨迹现在同时打印 r4-r7 现场，若再崩可直接看到被踩的寄存器。
  同族教训：跨 main() 的任何状态只能放内存，绝不能放寄存器。
- **非 static 全局变量引用需要重定位修复（"int board[8]; 崩、static 就不崩"）**：
  TCC 在 `-shared` 下对**导出符号**（非 static 文件域变量）的引用发
  `R_ARM_ABS32` 重定位——符号值在 `.dynsym`、字面量 addend 为 0；而设备
  shellcode 加载器与模拟器都只应用 `R_ARM_RELATIVE`，ABS32 被静默跳过，
  `&board` 字面量保持 0，首次访问即野指针复位。加 `static` 后符号变本地、
  TCC 链接期解析完，只发 RELATIVE，所以不崩。修复：main.py 编译后调用
  `ElfTools.patch_shared_relocs("code.elf")`，把 ABS32/REL32 条目改成
  RELATIVE 并把 st_value 折进 addend（`base + S + A`），模拟器 loader 同步
  同一规则——两条路径行为一致。
- **程序栈块的 malloc 余量必须 ≥64（修复"所有程序退出即重启"）**：把
  退出保存对挪进栈块顶部后暴露的第二个真机坑——`malloc(SIZE+32)` 配
  `top = ((p+31) & ~7) + SIZE`，当真机 malloc 返回的 p 只有 4 字节对齐时
  `top+8` 最多**越出块尾 7 字节**，踩坏下一块堆头。真机分配器有元数据：
  运行期间谁都不校验（ball/mandelbrot 照常画、空 main 一生即退出），
  直到第一次 `free()`（ESC 时释放 GROB、或 main.py 释放代码缓冲）走到
  坏头 → 数据中止 → 复位。模拟器的固件 malloc 是无元数据 bump 分配器，
  越界写落进空内存完全无害——18 项测试全绿照样真机全崩。余量改为 +64
  （`top+8 ≤ p+SIZE+39`，可证明安全）。
- **诊断只进 crash.log 且逐行落盘**：旧版运行时诊断写 tcc.log，但句柄从不
  fclose——真机上程序一崩，缓冲里没写盘的内容全部丢失（tcc.log 看不到任何
  本轮痕迹就是这个原因），只剩 main.py finally 块用 "wb" 截断写入的最后一个
  M 标记（所以 crash.log 里永远只有孤零零的 `M4 dbg-closed`）。现在
  `diag_log` 改为对 crash.log 做**持久化追加**：每行先 rb 读旧内容、再 wb+
  重写并立即 fclose，崩溃/reset 后内容仍在（尾部保留最近 8KB 防止无限增长）；
  main.py 的 M1..M4 步骤标记也改为追加（"ab"），不再覆盖运行时的轨迹。
  干净跑完一轮后 main.py 会清掉 stage.txt/tcc.log/crash.log；异常残留时
  会先展示轨迹并询问是否清除再重新编译。
- **模拟器与真机的差异**：emu_arm2 曾漏掉 CLZ 解码（掩码错误）、完全没有
  LDRD/STRD 支持（误解码成其它指令）、不校验 8 字节对齐、对尾调用 svc 返回
  宽容——这些问题都会让模拟器"全过"而真机崩溃。已修复 CLZ/LDRD/STRD 并加
  对齐检查；遇到难以解释的真机崩溃，用 **Unicorn（QEMU 内核）**交叉验证
  （`pip install unicorn`，见 tests/ 下的验证脚本）。

## 测试

主机侧 ARM 模拟器（`tests/emu_arm2.py`）实现 ARMv5 指令集 + 固件 SVC 后端
（fopen/fread/fwrite/malloc… 映射到宿主文件系统与内存），端到端跑通：
TCC 编译 `code.c` + 预编译对象 → `code.elf` → 加载运行 → 输出比对
（含 framebuffer 像素校验与 LDRD/STRD 对齐检查）。

```
$ python3 tests/harness.py hello
[user] hello from TCC on HP Prime!
[user] fib(15) = 610
RESULT: user program exit code = 0
```

测试列表：`hello struct str float gfx math ball rt d ret tri font sys`
（`rt` 覆盖 ftoa/键码/拆钩子，`d` 为纯 double 算术回归，`ret` 验证 RT_RET
真实退出码通道，`varg` 覆盖可变参数 printf/sprintf 的 1..8 实参与各转换符，
`fix` 定点数学、`rng` 随机数/噪声、`codec` 校验与编码、`libc` strtod/qsort/
bsearch、`gui` 运行 `examples/gui.c`（终端计算器：键盘输入表达式、
历史回滚、硬键插入函数名，校验 `2+3*2=8` 与 `sqrt(9)=3`），
`tri` 直接运行 `examples/tri.c` 校验三角形/GROB 新 API，
`gfxtest` 运行 `examples/gfxtest.c` 的 15 项图形自测面板（读回校验），
`gfx` 用例覆盖三角形填充/轮廓、GROB 尺寸访问器与跨目标 blit 的像素级校验）。
另有 `tests/test_main_slot.py`（主机侧单测 main.py 的 tcc.slot 常驻逻辑与
RT_RET 解析，注入 fake uio 模块，无需计算器）和 `tests/mb_check.py`
（完整渲染曼德勃罗特 demo 并校验关键像素）。

默认 demo（`calc/main.py` 的 PRIME-C-CODE 区段）：**系统库测试面板**——依次调用 `hp_sys` 各函数（malloc/calloc/realloc/max_alloc/heap_free/get_lcd/debug_open），用 **Montserrat**（标签）+ **Cascadia Code**（数值）画在 LCD 上；每步先打印 `S1..S7` 控制台标记并写入 crash.log（真机崩溃可定位到具体调用）。**ENTER** 重跑面板，**q/ON/ESC** 退出。曼德勃罗特交互 demo 在 `examples/mandelbrot.c`。

独立示例集中在 `examples/`：`hello.c`（最小 printf+递归）、`ball.c`（双缓冲弹球）、
`sysdemo.c`（系统库测试面板，与 main.py 内嵌 demo 同源）、`mandelbrot.c`
（定点曼德勃罗集），说明见 `examples/README.md`。`tests/restart_check.py` 验证两轮连续运行按键始终可达。

真机崩溃排查工具：
- **PRIMELOG**：用户程序所有输出进环形缓冲，main.py 彩色回显；崩溃重启后
  控制台输出丢失，但 TCC 阶段的输出持久化在 `tcc.log`。
- **crash.log 分层**：demo 关键步骤写 crash.log（S1–S21），hp_entry 退出写
  E1，main.py 收尾写 M1–M4——崩溃重启后再次 `import main` 会显示
  `last crash.log step`，精确定位崩溃层。
- **成功运行自动清理**：main.py 在**完整成功**的一次运行收尾时删除
  `stage.txt`/`tcc.log`/`crash.log`——下一次运行不会把上一次的成功输出
  误显示为 "previous crash trace"；崩溃/重启则保留这些文件用于诊断。
- **Unicorn（QEMU）**：指令语义严格，能抓到模拟器误解码的未定义指令/未对齐
  访问（本次用它定位了尾调用 bug）。

## 图形库效率

热路径重写前后的模拟器指令数对比（`python3 tests/harness.py ball` 的
`[user] ran ... instructions` 一行，TCC 编译时间不计入）：

| 用例 | 重写前 | 重写后 | 变化 |
|------|--------|--------|------|
| ball（3 帧双缓冲弹球：每帧 clear + fill_circle + 文字 + blit） | 2,451,113 | 1,730,557 | **-29.4%**（快 1.42x，渲染像素逐位一致：197 橙色像素不变） |

说明：模拟器为 ARMv5 指令数统计（含固件 SVC 模拟开销），真机绝对耗时
不同，但指令数比例可反映计算器上的相对提速。主要收益来自：裁剪外提后的
无检查直写循环、`hp_text` 快速路径、`hp_fill_circle` 单调半宽递推。

另外借此修复了模拟器 `emu_arm2.py` 的两个指令级 bug（都是"真机正常、
模拟器静默算错"类，README 上部已多次记载此类差异）：

1. `long_mul` 把 SMULL/SMLAL（有符号 64 位乘）按无符号乘计算——寄存器按
   无符号存储时负操作数的高 32 位全错。该 bug 会静默破坏一切"负数 × 正数"
   的 64 位乘法（本次由 `hp_fill_triangle` 的边插值暴露：扫描线 xa/xb 算成
   垃圾值，整行误涂、覆盖已有图形；真机无此问题）。已改为先符号扩展再相乘，
   并加了 SMULL/UMULL 正负操作数单测。库侧三角形插值与直线裁剪同时改用
   32 位整数算术（坐标 ±46340 内精确），不再依赖 64 位乘除辅助例程。
2. 寄存器形式 LSR/ASR 移位量为 0 时被当成 >>32——"0 即 32"的编码怪癖只对
   **立即数**形式成立；寄存器形式 `x >> i` 在 i=0 时必须等于 x（C 编译器
   依赖此语义）。旧行为让一切"首轮移位量为 0 的变量移位循环"算错
   （CORDIC atan2 把 π/4 算成 π/2），`hp_fixmath` 的定点三角因此全错。
   已加 `regshift` 标志区分两条路径，并有 `cordic` 用例回归。

## 固件接口（HP Prime G1）

### 运行内存：为什么每轮编译+运行后自由内存减少 ~0.71MB

不是 primetcc 代码泄漏——模拟器（与真机同一条 tcc.elf + rt_core.o 链路）实测：

| 阶段 | 固件堆峰值 | 阶段结束存活 |
|------|-----------|--------------|
| TCC 编译（code.c + rt_core.o 等链接） | ~602KB（tcc_delete 释放，剩余 28B） | ~0 |
| 用户程序（hello） | 0（无堆分配） | 0 |

每轮运行固件堆的工作集 ≈ **TCC 编译工作集（~600KB）+ code.elf 镜像（~180KB）≈
0.71~0.78MB**，与观测的逐轮下降量一致。代码侧全部 free 了，但 **HP Prime 固件
的堆分配器对释放块复用不佳（碎片化/不回退堆顶）**——README 上部记载的
"~900KB malloc/free churn 导致 5-9 次运行后崩溃"正是同一根因；`tcc.slot`
常驻机制只消除了 tcc.elf（866KB）的每轮加载/释放，**编译工作集的 churn 仍在**。

真机验证：跑 `sysdemo`（S5 heap_free / S4 max_alloc 读数）逐轮对比，或观察
系统自由内存——若每轮下降量 ≈ 0.7MB 即为此行为，非泄漏。缓解：运行若干轮后
`main.reset_tcc()` 并重启计算器复位堆顶；不要在同一会话无限次运行。

SVC 编号（`hp_svc.s` / `rt_svc.s`）：fopen 0x1026f, fclose 0x100ca,
fseek 0x100cf, ftell 0x100d0, fread 0x100d4, fwrite 0x100d7, filesize 0x100cb,
malloc 0x10037, calloc 0x10038, realloc 0x10039, free 0x1003a,
os_sleep 0x10008, get_time 0x100a5, get_lcd 0x1008d, get_event 0x1003f。
调用约定：`push {r0}; push {lr}; svc N`（固件 handler 弹出 LR 返回，结果在 r0）。
路径为 UTF-16LE。详细见 PrimeC 项目的 README。
