"""Structure-first SVG of the first-bearing feasible region and paired revisit bands."""

from __future__ import annotations

import math
from pathlib import Path
from xml.etree import ElementTree as ET


OUT = Path(__file__).with_suffix(".svg")
SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)


def el(parent, tag, **attrs):
    return ET.SubElement(parent, f"{{{SVG}}}{tag}", {k.replace("_", "-"): str(v) for k, v in attrs.items()})


def line(parent, a, b, **attrs):
    return el(parent, "line", x1=f"{a[0]:.4f}", y1=f"{a[1]:.4f}",
              x2=f"{b[0]:.4f}", y2=f"{b[1]:.4f}", **attrs)


def label(parent, id_, x, y, value, size=23, anchor=None, math_font=False, **attrs):
    kw = dict(id=id_, x=f"{x:.3f}", y=f"{y:.3f}", font_size=size,
              font_family=("Cambria Math, Times New Roman, serif" if math_font
                           else "Microsoft YaHei, SimHei, sans-serif"), fill="#111")
    if anchor:
        kw["text_anchor"] = anchor
    kw.update(attrs)
    t = el(parent, "text", **kw)
    t.text = value
    return t


def point(parent, id_, p, radius=5.5, fill="#111"):
    return el(parent, "circle", id=id_, cx=f"{p[0]:.4f}", cy=f"{p[1]:.4f}", r=radius, fill=fill)


root = ET.Element(f"{{{SVG}}}svg", {
    "width": "1942", "height": "960", "viewBox": "0 0 1942 960", "role": "img",
    "aria-label": "First bearing sector, paired lateral candidate bands, and post hoc intersection",
})
el(root, "title").text = "首次测向后的双侧第二检测点候选区域"
el(root, "desc").text = "左图按等比例坐标构造首次测向的方向扇形、接收截断和双侧参数候选带；右图为独立的事后方位线交会示意。"
defs = el(root, "defs")
arrow = el(defs, "marker", id="arrow", markerWidth="8", markerHeight="8", refX="7", refY="4",
           orient="auto", markerUnits="strokeWidth")
el(arrow, "path", d="M0,0 L8,4 L0,8 Z", fill="#111")
el(defs, "clipPath", id="main-plot-clip")
el(defs[-1], "rect", x="145", y="270", width="1050", height="495")

frames = el(root, "g", id="panel-frames", fill="white", stroke="#111", stroke_width="1.4")
el(frames, "rect", id="panel-candidate-construction", x="20", y="52", width="1190", height="755")
el(frames, "rect", id="panel-posthoc-intersection", x="1230", y="52", width="692", height="755")

# Equal-scale main coordinates (pixels per metre).  y is inverted for SVG.
S1 = (0.0, 0.0)
alpha = 0.0
epsilon_deg = 1.0051
epsilon = math.radians(epsilon_deg)
distance_bound = 1500.0
target_radius = 1800.0
u = (math.cos(alpha), math.sin(alpha))
u_perp = (-math.sin(alpha), math.cos(alpha))
d_minus, d_plus = 0.0, distance_bound
scale = 0.5


def main_map(p):
    return (270 + scale * p[0], 535 - scale * p[1])


assert u == (1.0, 0.0) and u_perp == (-0.0, 1.0)
assert d_minus == 0 and d_plus == 1500
upper_1500 = (distance_bound * math.cos(epsilon), distance_bound * math.sin(epsilon))
lower_1500 = (upper_1500[0], -upper_1500[1])
upper_1800 = (target_radius * math.cos(epsilon), target_radius * math.sin(epsilon))
lower_1800 = (upper_1800[0], -upper_1800[1])
assert abs(math.degrees(math.atan2(upper_1500[1], upper_1500[0])) - epsilon_deg) < 1e-10

left = el(root, "g", id="first-bearing-and-candidates")
plot = el(left, "g", id="equal-scale-main-plot", clip_path="url(#main-plot-clip)")
target = el(plot, "g", id="target-region-T-background")
el(target, "circle", id="target-circle-r1800", cx=main_map(S1)[0], cy=main_map(S1)[1],
   r=scale * target_radius, fill="none", stroke="#999", stroke_width="1.8", stroke_dasharray="8 6")

# W is angular only. Omega_1 is its exact circular-sector intersection with
# the 1500 m reception disk. T has radius 1800 m, so adds no further cut here.
wedge = el(plot, "g", id="region-W-S1-alpha")
el(wedge, "path", id="angular-sector-displayed-to-1800",
   d=(f"M{main_map(S1)[0]:.4f},{main_map(S1)[1]:.4f} "
      f"L{main_map(upper_1800)[0]:.4f},{main_map(upper_1800)[1]:.4f} "
      f"L{main_map(lower_1800)[0]:.4f},{main_map(lower_1800)[1]:.4f} Z"),
   fill="#eaf7f6")
omega = el(plot, "g", id="region-Omega1")
el(omega, "path", id="reception-truncated-sector",
   d=(f"M{main_map(S1)[0]:.4f},{main_map(S1)[1]:.4f} "
      f"L{main_map(upper_1500)[0]:.4f},{main_map(upper_1500)[1]:.4f} "
      f"A{scale*distance_bound:.4f},{scale*distance_bound:.4f} 0 0 1 "
      f"{main_map(lower_1500)[0]:.4f},{main_map(lower_1500)[1]:.4f} Z"),
   fill="#c6e9e6", stroke="#267f80", stroke_width="1.6")
ray_group = el(plot, "g", id="bearing-boundary-rays", fill="none", stroke="#267f80",
               stroke_width="1.6", stroke_dasharray="7 5")
line(ray_group, main_map(S1), main_map(upper_1800), id="ray-alpha-plus-epsilon")
line(ray_group, main_map(S1), main_map(lower_1800), id="ray-alpha-minus-epsilon")

candidate_main = el(plot, "g", id="candidate-bands-main")
x_min, x_max = 1500 * 0.26, 1500 * 0.35
h_min, h_max = 60.0, 83.0
assert (x_min, x_max) == (390.0, 525.0)
for side, name in ((1, "plus"), (-1, "minus")):
    ys = [side * h_min, side * h_max]
    x0, y0 = main_map((x_min, max(ys)))
    x1, y1 = main_map((x_max, min(ys)))
    el(candidate_main, "rect", id=f"candidate-band-{name}", x=f"{x0:.4f}", y=f"{y0:.4f}",
       width=f"{x1-x0:.4f}", height=f"{y1-y0:.4f}", fill="#ffe3c4",
       stroke="#c96f0c", stroke_width="1.2")

Q3 = {1: (525.0, 60.0), -1: (525.0, -60.0)}
Q4 = {1: (392.69, 82.76), -1: (392.69, -82.76)}
assert abs(Q4[1][0] / 1500 - 0.2617933333333333) < 1e-12
for task, points in ((3, Q3), (4, Q4)):
    for side in (1, -1):
        p = points[side]
        assert x_min <= p[0] <= x_max and h_min <= abs(p[1]) <= h_max
        point(candidate_main, f"node-Q{task}-{('plus' if side==1 else 'minus')}-main",
              main_map(p), radius=5.8, fill="#d37409")

geometry = el(left, "g", id="axes-and-projections", fill="none", stroke="#111")
line(geometry, (145, 535), (1194, 535), id="axis-x", stroke_width="1.7", marker_end="url(#arrow)")
line(geometry, (270, 765), (270, 274), id="axis-y", stroke_width="1.7", marker_end="url(#arrow)")
line(geometry, main_map(S1), main_map((1500, 0)), id="ray-alpha-center",
     stroke="#111", stroke_width="1.8", marker_end="url(#arrow)")
line(geometry, (main_map((1500, 0))[0], 465), (main_map((1500, 0))[0], 610),
     id="projection-d-plus", stroke="#555", stroke_width="1.2", stroke_dasharray="5 5")
for value in (0, 390, 525, 1000, 1500):
    x = main_map((value, 0))[0]
    line(geometry, (x, 535), (x, 544), stroke_width="1.2")
for value in (-500, 500):
    y = main_map((0, value))[1]
    line(geometry, (261, y), (270, y), stroke_width="1.2")
point(left, "node-S1-main", main_map(S1), radius=6.2)

ml = el(left, "g", id="native-editable-labels-main")
label(ml, "label-axis-x", 1105, 605, "x (m)", 23, math_font=True)
label(ml, "label-axis-y", 213, 245, "y (m)", 23, math_font=True)
label(ml, "label-S1-main", 287, 572, "S₁=(0,0)", 23, math_font=True)
for value in (0, 390, 525, 1000, 1500):
    tick_y = 630 if value in (390, 525) else (602 if value == 0 else 572)
    label(ml, f"tick-x-{value}", main_map((value, 0))[0], tick_y,
          str(value), 17, anchor="middle", math_font=True)
for value in (-500, 500):
    label(ml, f"tick-y-{value}", 254, main_map((0, value))[1] + 5,
          str(value), 17, anchor="end", math_font=True)
label(ml, "label-alpha-zero", 682, 526, "α = 0°", 21, math_font=True)
label(ml, "label-epsilon-plus", 840, 500, "+1.0051°", 19, math_font=True, fill="#267f80")
label(ml, "label-epsilon-minus", 840, 590, "−1.0051°", 19, math_font=True, fill="#267f80")
label(ml, "label-d-minus", 292, 485, "d₋ = 0 m", 20, math_font=True)
label(ml, "label-d-plus", 1033, 650, "d₊ = 1500 m", 20, math_font=True)
label(ml, "label-omega1", 1040, 482, "Ω₁", 23, math_font=True, fill="#267f80")
label(ml, "label-target-circle", 820, 690, "𝒯: r = 1800 m（背景）", 19,
      math_font=True, fill="#666")
line(left, (1008, 681), (1161, 665), id="leader-target-circle", stroke="#888",
     stroke_width="1.2", marker_end="url(#arrow)")
label(ml, "label-parameters", 307, 368, "Λ=[0.26,0.35]，H=[60,83] m", 20, math_font=True)
label(ml, "label-Q3-coordinate", 307, 404, "Q₃=(525, ±60) m", 20, math_font=True, fill="#a65a07")
label(ml, "label-Q4-coordinate", 307, 435, "Q₄=(392.69, ±82.76) m", 20,
      math_font=True, fill="#a65a07")
label(ml, "label-task-distinction", 385, 742, "Q₃ 与 Q₄ 属于不同任务参数配置；实际只选择一侧复测。",
      19, fill="#444")

# An exact-coordinate local inset enlarges only the area around C_2.
inset = el(left, "g", id="candidate-band-local-inset")
el(inset, "rect", id="inset-frame", x="730", y="70", width="400", height="360",
   fill="white", stroke="#111", stroke_width="1.25")
label(inset, "label-inset-title", 930, 103, "双侧候选带（局部放大）", 21, anchor="middle")


def inset_map(p):
    return (730 + 1.5 * (p[0] - 350), 265 - 1.5 * p[1])


line(inset, (770, 265), (1090, 265), id="inset-centerline", stroke="#777",
     stroke_width="1.2", stroke_dasharray="5 4")
inset_bands = el(inset, "g", id="candidate-bands-magnified")
for side, name in ((1, "plus"), (-1, "minus")):
    ys = [side * h_min, side * h_max]
    x0, y0 = inset_map((x_min, max(ys)))
    x1, y1 = inset_map((x_max, min(ys)))
    el(inset_bands, "rect", id=f"candidate-band-{name}-magnified",
       x=f"{x0:.4f}", y=f"{y0:.4f}", width=f"{x1-x0:.4f}", height=f"{y1-y0:.4f}",
       fill="#ffe3c4", stroke="#c96f0c", stroke_width="1.4")
for task, points in ((3, Q3), (4, Q4)):
    for side in (1, -1):
        point(inset, f"node-Q{task}-{('plus' if side==1 else 'minus')}",
              inset_map(points[side]), radius=6.5, fill="#d37409")
label(inset, "label-Q4-plus", 770, 125, "Q₄⁽⁺⁾", 19, math_font=True, fill="#a65a07")
label(inset, "label-Q3-plus", 1005, 162, "Q₃⁽⁺⁾", 19, math_font=True, fill="#a65a07")
label(inset, "label-Q3-minus", 1005, 343, "Q₃⁽⁻⁾", 19, math_font=True, fill="#a65a07")
label(inset, "label-Q4-minus", 770, 415, "Q₄⁽⁻⁾", 19, math_font=True, fill="#a65a07")

# Post-hoc geometry is independent of candidate generation in the left panel.
right = el(root, "g", id="posthoc-bearing-intersection")
S1_post = (0.0, 0.0)
S2_post = (-200.0, 600.0)
G = (1000.0, 0.0)
post_scale = 0.37


def post_map(p):
    return (1370 + post_scale * p[0], 612 - post_scale * p[1])


gamma = math.degrees(math.atan2(600, 1200))
assert abs(gamma - 26.56505117707799) < 1e-10
axes = el(right, "g", id="posthoc-axes", fill="none", stroke="#111", stroke_width="1.4")
line(axes, (1260, 612), (1876, 612), id="posthoc-axis-x", marker_end="url(#arrow)")
line(axes, (1370, 667), (1370, 281), id="posthoc-axis-y", marker_end="url(#arrow)")
for value in (0, 500, 1000):
    x = post_map((value, 0))[0]
    line(axes, (x, 612), (x, 620), stroke_width="1")
    label(right, f"posthoc-x-{value}", x, 640, str(value), 17, anchor="middle", math_font=True)
for value in (0, 600):
    y = post_map((0, value))[1]
    line(axes, (1362, y), (1370, y), stroke_width="1")
    label(right, f"posthoc-y-{value}", 1353, y + 5, str(value), 17, anchor="end", math_font=True)
first_bearing = el(right, "g", id="posthoc-first-bearing")
line(first_bearing, post_map(S1_post), post_map(G), id="line-S1-G", stroke="#111", stroke_width="2.2")
second_bearing = el(right, "g", id="posthoc-second-bearing")
line(second_bearing, post_map(S2_post), post_map(G), id="line-S2-G", stroke="#111", stroke_width="2.2")
point(right, "node-S1-posthoc", post_map(S1_post), radius=6.2)
point(right, "node-S2-posthoc", post_map(S2_post), radius=6.2)
point(right, "node-G-posthoc", post_map(G), radius=6.8, fill="#b33434")

center = post_map(G)
arc_r = 71.0
arc_start = (center[0] - arc_r, center[1])
arc_end = (center[0] - arc_r * math.cos(math.radians(gamma)),
           center[1] - arc_r * math.sin(math.radians(gamma)))
el(right, "path", id="angle-gamma", d=(f"M{arc_start[0]:.4f},{arc_start[1]:.4f} "
    f"A{arc_r},{arc_r} 0 0 0 {arc_end[0]:.4f},{arc_end[1]:.4f}"),
    fill="none", stroke="#111", stroke_width="1.5")

pr = el(right, "g", id="native-editable-labels-posthoc")
label(pr, "label-posthoc-title", 1577, 112, "事后交会示意", 28, anchor="middle")
label(pr, "label-posthoc-axis-x", 1834, 644, "x (m)", 21, math_font=True)
label(pr, "label-posthoc-axis-y", 1322, 287, "y (m)", 21, math_font=True)
label(pr, "label-S1-posthoc", 1382, 685, "S₁=(0,0)", 21, math_font=True)
label(pr, "label-S2-posthoc", 1265, 369, "S₂=(−200,600)", 21, math_font=True)
label(pr, "label-G-posthoc", 1743, 590, "G=(1000,0)", 21, math_font=True, fill="#a22")
label(pr, "label-gamma", 1470, 582, f"γ ≈ {gamma:.3f}°", 20, math_font=True)
label(pr, "label-G-posthoc-only", 1577, 721, "G 是事后验证位置，不参与候选点生成。",
      19, anchor="middle", fill="#444")
label(pr, "label-S2-example-only", 1577, 749, "此处 S₂ 仅用于交会示意，与左图候选参数独立。",
      18, anchor="middle", fill="#444")
label(pr, "label-h-zero", 1268, 775, "h=0：近共线，交会角小", 18)
label(pr, "label-h-tradeoff", 1550, 775, "h 增大：交会角与路程均增大", 18)

footer = el(root, "g", id="algorithm-footer")
label(footer, "label-candidate-formula", 971, 862,
      "S₂⁽±⁾ = S₁ + [d₋ + λ(d₊ − d₋)]u ± h u⊥ = (1500λ, ±h)",
      29, anchor="middle", math_font=True)
label(footer, "label-algorithm-flow", 971, 920,
      "首次测向 → 建立扇形可行域 → 求 d₋、d₊ → 沿方向前进 → 向两侧偏移 → 选择一侧复测",
      23, anchor="middle")

ET.indent(root, space="  ")
ET.ElementTree(root).write(OUT, encoding="utf-8", xml_declaration=True)
print(OUT)
print("epsilon:", epsilon_deg, "degrees; sector endpoints:", upper_1500, lower_1500)
print("candidate bands: x", (x_min, x_max), "|y|", (h_min, h_max))
print("gamma:", gamma, "degrees")
