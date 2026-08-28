version 0.9.1c, 2026.02

使用自定义字体的原理：
把ASCII字符画在一张png上，用hpprime库的blit按照ord计算位置，然后复制到grob上。

```python
def drawChar(grob, c, x, y, color):
    j = ord(c) - 33
    if j + 33 > 127:
        hpprime.textout(grob, x, y, c, color2rgb[color])
        return 10 if c in "≤≥≠▶αβ→∞°′″Σ−" else 15
    else:
        if x > 0:
            hpprime.strblit2(grob, x, y, 10, 18, 1, j*10, color*24, 10, 20) # 由于prime图片算法问题，等大blit会出现炸裂效果
        return 10
```
