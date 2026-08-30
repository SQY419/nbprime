## G1 硬件性能
CPU	三星S3C2416XH-40，ARM926EJ-S，400MHz

ROM	256MB

RAM	32MB

# 按键事件

## 两种取键方式的区别

| 方式 | 返回 | 无按键时 |
|---|---|---|
| PPL `GETKEY` | 单个键码（事件） | **-1** |
| hpprime `keyboard()`（Python） | 当前按下键的**位掩码** | **0**（无任何位） |

`keyboard()` 的位号与 `GETKEY` 键码**完全一致**：`keyboard() & (1 << N)` 为真 ⇔ 键码 N 正被按下。

## A. 导航 / 功能键

| 键码 | 按键 | 键码 | 按键 |
|---|---|---|---|
| -1 | （GETKEY）无按键 | 6 | plot |
| 0 | apps | 7 | ← 左 |
| 1 | symb | 8 | → 右 |
| 2 | ↑ 上 | 9 | view |
| 3 | help | 10 | CAS |
| 4 | esc | 11 | num |
| 5 | home | 12 | ↓ 下 |
| | | 13 | menu |
| 19 | 退格 Del | 30 | enter 回车 |
| 36 | alpha | 41 | shift |

## B. 字母键（alpha 模式标注）

| 键码 | 字母 | 键码 | 字母 | 键码 | 字母 | 键码 | 字母 |
|---|---|---|---|---|---|---|---|
| 14 | a | 20 | f | 26 | l | 31 | p |
| 15 | b | 21 | g | 27 | m | 32 | q |
| 16 | c | 22 | h | 28 | n | 33 | r |
| 17 | d | 23 | i | 29 | o | 34 | s |
| 18 | e | 24 | j | | | 35 | t |
| | | 25 | k | | | | |
| 37 | u | 42 | y | 44 | # | 48 | . |
| 38 | v | 43 | z | 45 | : | 49 | 空格 |
| 39 | w | | | 47 | " | 50 | ; |
| 40 | x | | | | | | |

# hpprime 库用法提取

## 导入

```python
import hpprime as _hpprime
```

## 1. 绘图 — 直接函数调用

```python
GROB = 1  # 屏幕缓冲 grob 号

_hpprime.dimgrob(GROB, w, h, 底色)              # 创建缓冲 grob（宽,高,底色）
_hpprime.fillrect(GROB, x, y, w, h, 颜色, 填充色)   # 填充矩形
_hpprime.textout(GROB, x, y, "文本", 颜色)          # 写文字
_hpprime.blit(0, 0, 0, GROB)
_hpprime.line(GROB, x0, y0, x1, y1, color)
```

- `dimgrob(grob, w, h, bgcolor)` — 初始化屏幕大小的缓冲 grob，只在启动时调用一次
- `fillrect(grob, x, y, w, h, color, fillcolor)` — 填满指定区域（color 与 fillcolor 相同即纯填充）
- `textout(grob, x, y, text, color)` — 在 grob 上画文字，坐标是文字左上角
- `blit(0, 0, 0, grob)` — 把缓冲 grob 复制到显示（grob 0）。**每个画面画完后必须 blit**，否则显示不更新

## 2. eval() — 透传任意 PPL 命令（返回值转 Python 数组）

```python
_hpprime.eval('TEXTSIZE("text", 0)')        # -> [宽, 高]  #获取字符串打印出来的高度和宽度
_hpprime.eval('TEXTOUT_P("text", G1, x, y, {"2D", 0, 颜色})')  # 等宽小字体
_hpprime.eval('TEXTOUT_P("text", G1, x, y, 2, 颜色)')          # 小字体（font 2）
_hpprime.eval('wait(0.1)')                # 帧节奏
_hpprime.eval('memory(1)')                  # 可用内存 bytes ∈ (0, 33554432)
```

- `TEXTSIZE(text, font)` → `[w, h]`：测量文字像素尺寸，用于自适应布局与按宽度截断文件名
- `TEXTOUT_P` 的 grob 参数写成 `G<编号>`（如 `G1`）；`{"2D", 0, 颜色}` 是微小字体样式
- PPL 返回的列表（如 `{w,h}`）会被自动转成 Python 数组，直接 `r[0]` / `r[1]` 取值

## 3. 输入 — 键盘 / 触摸

```python
k = _hpprime.keyboard()    # int 位掩码；位号 = GETKEY 键码（见 HP_Prime_GETKEY.md）
m = _hpprime.mouse()       # 触摸：[[x, y, x0, y0, type], [x2, y2, ...]]；无触摸为 [[], []]
```

- `keyboard()`：当前按下键的位掩码，`(k & (1 << 键码)) != 0` 即按下；无按键返回 0
- `mouse()`：第一根手指数据在 `m[0]`（`m[0][0]`=x，`m[0][1]`=y）；空列表表示无触摸

## 4. PPL 字符串转义

```python
def _q(s):
    s = s.replace('"', "'").replace('\n', ' ').replace('\r', '')
    return '"' + s + '"'
```

