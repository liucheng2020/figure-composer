"""V18 布局引擎逻辑自测（不依赖 GUI）。

验证：
  - uniform_fill：选中图乘同一系数后恰好填满指定宽度（保留相对大小、各自比例）。
  - grid_proportional：智能网格每行从左铺满画布宽度、高度不强制相等。
  - flow_import：导入初始铺排不报错、标签连续。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf_utils import PDFInfo
from layout_engine import LayoutEngine

eng = LayoutEngine(297, 210, margin_mm=5, spacing_mm=5)
print("可用宽:", round(eng.available_width, 1), " 可用高:", round(eng.available_height, 1))

print("\n=== uniform_fill：3 张不同大小的图填满 200mm ===")
sizes = [(40, 30), (60, 60), (20, 50)]  # 不同宽高比、不同大小
scale, out = eng.uniform_fill(sizes, span_width=200, gap=5)
total = sum(w for w, _ in out) + (len(out) - 1) * 5
print("scale=", round(scale, 4))
print("结果 (宽,高):", [(round(w, 2), round(h, 2)) for w, h in out])
print("总宽(含间距)=", round(total, 2), " 目标=200  填满=", abs(total - 200) < 1e-6)
# 验证相对大小保留：缩放后宽度比 == 原宽度比
r0 = out[0][0] / out[1][0]; o0 = sizes[0][0] / sizes[1][0]
print("相对大小保留:", abs(r0 - o0) < 1e-9)
# 验证各自比例保留
print("各自宽高比保留:", all(abs((w/h) - (sw/sh)) < 1e-9
                            for (w, h), (sw, sh) in zip(out, sizes)))

print("\n=== grid_proportional：智能网格 2行×2列，每行从左铺满画布宽度 ===")
class FakeItem:  # 模拟带 width/height/pdf_info/label 的选中图
    def __init__(self, w, h, label):
        self.width, self.height, self.label = w, h, label
        self.pdf_info = PDFInfo(filepath=f"{label}.pdf", filename=f"{label}.pdf",
                                width=w, height=h, aspect_ratio=w / h, sort_key=(0, 0))
        self.rotation = 0.0
items = [FakeItem(40, 30, "A"), FakeItem(60, 45, "B"),
         FakeItem(30, 60, "C"), FakeItem(50, 50, "D")]
grid = eng.grid_proportional(items, rows=2, cols=2)
right_limit = 297 - 5
for r in range(2):
    row = grid[r * 2:(r + 1) * 2]
    left = min(l.x for l in row)
    right = max(l.x + l.width for l in row)
    print(f"第{r+1}行 标签={[l.label for l in row]} "
          f"左={round(left,2)}(应=5) 右={round(right,2)}(应={right_limit}) "
          f"铺满={abs(left-5)<1e-6 and abs(right-right_limit)<1e-6}")
# 各自宽高比保留
src = {it.label: (it.width, it.height) for it in items}
print("各自宽高比保留:", all(
    abs((l.width / l.height) - (src[l.label][0] / src[l.label][1])) < 1e-6 for l in grid))
# 高度不强制相等（验证存在不同高度）
print("高度未被强制相等:", len({round(l.height, 2) for l in grid}) > 1)

print("\n=== justified_row：等高填充到指定宽度 ===")
# 等高输入（高都=50，宽不同）→ 输出必须仍等高，且铺满宽度
eq = [(40, 50), (80, 50), (30, 50)]
out = eng.justified_row(eq, span_width=250, gap=5)
total = sum(w for w, _ in out) + (len(out) - 1) * 5
heights = {round(h, 4) for _, h in out}
print("等高输入→输出高度集合:", heights, " 仍等高:", len(heights) == 1)
print("总宽(含间距)=", round(total, 2), " 目标=250 铺满=", abs(total - 250) < 1e-6)
# 不等高输入 → 被拉到同一高度，且各自宽高比保留
ne = [(40, 30), (60, 60), (20, 50)]
out2 = eng.justified_row(ne, span_width=250, gap=5)
h2 = {round(h, 4) for _, h in out2}
print("不等高输入→输出统一高度:", len(h2) == 1,
      " 各自比例保留:", all(abs((w/h) - (sw/sh)) < 1e-9
                            for (w, h), (sw, sh) in zip(out2, ne)))

print("\n=== flow_import：导入 5 张图的初始铺排不报错、标签连续 ===")
pdfs = [PDFInfo(filepath=f"{i}.pdf", filename=f"{i}.pdf",
                width=(i + 1) * 80, height=120, aspect_ratio=(i + 1) * 80 / 120,
                sort_key=(0, i)) for i in range(5)]
lay = eng.flow_import(pdfs)
print("标签:", [l.label for l in lay])
print("无重叠出界(粗检) 最右<=画布:", max(l.x + l.width for l in lay) <= 297 - 5 + 1)
