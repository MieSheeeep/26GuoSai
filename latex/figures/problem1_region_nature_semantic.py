"""Semantic redraw of the three-station bearing intersection and diameter disk.

The polygon and circle are recomputed from the manuscript's unrounded input
bearings through src.problem1.solve; labels are native SVG text.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from src.problem1 import solve  # noqa: E402


OUT = HERE / "problem1_region_nature_semantic.svg"
SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)


def el(parent, tag, **attrs):
    return ET.SubElement(parent, f"{{{SVG}}}{tag}", {k.replace("_", "-"): str(v) for k, v in attrs.items()})


def line(parent, a, b, **attrs):
    return el(parent, "line", x1=f"{a[0]:.4f}", y1=f"{a[1]:.4f}",
              x2=f"{b[0]:.4f}", y2=f"{b[1]:.4f}", **attrs)


def polygon(parent, points, **attrs):
    return el(parent, "polygon", points=" ".join(f"{x:.4f},{y:.4f}" for x, y in points), **attrs)


def label(parent, id_, x, y, value, size=22, anchor=None, math_font=False, **attrs):
    kw = dict(id=id_, x=f"{x:.3f}", y=f"{y:.3f}", font_size=size,
              font_family=("Cambria Math, Times New Roman, serif" if math_font
                           else "Microsoft YaHei, SimHei, sans-serif"), fill="#111")
    if anchor:
        kw["text_anchor"] = anchor
    kw.update(attrs)
    t = el(parent, "text", **kw)
    t.text = value
    return t


def point(parent, id_, p, r=5.2, fill="#111"):
    return el(parent, "circle", id=id_, cx=f"{p[0]:.4f}", cy=f"{p[1]:.4f}", r=r, fill=fill)


def diamond(parent, id_, p, r=8, fill="#a75f25"):
    x, y = p
    return polygon(parent, [(x, y-r), (x+r, y), (x, y+r), (x-r, y)], id=id,
                   fill=fill, stroke="white", stroke_width="1.4")


stations = {
    1: (-500.0, -200.0),
    2: (900.0, -100.0),
    3: (0.0, 1000.0),
}
bearings = {
    1: 37.46989764584402,
    2: 139.3944289077348,
    3: 296.96505117707795,
}
observations = [(stations[i], bearings[i], 1.0) for i in (1, 2, 3)]
result = solve(observations)
vertices = result["polygon"]
V = {i + 1: p for i, p in enumerate(vertices)}
G = (300.0, 400.0)
D = result["diameter"]
diameter_endpoints = result["diameter_endpoints"]
C = result["circle"]["center"]
r = result["circle"]["radius"]
assert len(vertices) == 6 and result["circle"]["covers"]
assert abs(D - 40.87445590816319) < 1e-8
assert abs(math.dist(V[3], V[6]) - D) < 1e-9
assert abs(r - D / 2) < 1e-10
assert abs(C[0] - (V[3][0] + V[6][0]) / 2) < 1e-10
assert abs(C[1] - (V[3][1] + V[6][1]) / 2) < 1e-10
assert all(math.dist(p, C) <= r + 1e-7 for p in vertices)


def in_convex_polygon(p, poly):
    signs = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        cross = (b[0]-a[0])*(p[1]-a[1]) - (b[1]-a[1])*(p[0]-a[0])
        signs.append(cross)
    return min(signs) >= -1e-7 or max(signs) <= 1e-7


assert in_convex_polygon(G, vertices)

# Panel-specific coordinate maps; each map is internally equal-scale.
def overview(p):
    return (335 + 0.47 * p[0], 690 - 0.47 * p[1])


def detail(p):
    return (1292 + 11.5 * (p[0] - 300), 450 - 11.5 * (p[1] - 414))


root = ET.Element(f"{{{SVG}}}svg", {
    "width": "1672", "height": "941", "viewBox": "0 0 1672 941", "role": "img",
    "aria-label": "Three bounded bearings intersect in a convex hexagon with a covering diameter circle",
})
el(root, "title").text = "三站有界测向交会与定位区域直径圆"
el(root, "desc").text = "左幅为三站正负一度测向的全局交会，右幅为六顶点定位多边形及由最远顶点对V3、V6确定的直径圆。"
defs = el(root, "defs")
arrow = el(defs, "marker", id="arrow", markerWidth="8", markerHeight="8", refX="7", refY="4",
           orient="auto", markerUnits="strokeWidth")
el(arrow, "path", d="M0,0 L8,4 L0,8 Z", fill="#111")
clip = el(defs, "clipPath", id="overview-clip")
el(clip, "rect", x="43", y="115", width="835", height="697")

frames = el(root, "g", id="panel-frames", fill="white", stroke="#111", stroke_width="1.4")
el(frames, "rect", id="panel-three-stations", x="16", y="68", width="884", height="792")
el(frames, "rect", id="panel-polygon-detail", x="920", y="68", width="736", height="792")

left = el(root, "g", id="three-station-overview")
label(left, "label-overview-title", 458, 112, "三站有界测向交会", 26, anchor="middle")
axes = el(left, "g", id="overview-axes", fill="none", stroke="#111", stroke_width="1.35")
line(axes, (45, 690), (872, 690), id="overview-x-axis", marker_end="url(#arrow)")
line(axes, (335, 814), (335, 132), id="overview-y-axis", marker_end="url(#arrow)")
for value in (-500, 0, 500, 900):
    x = overview((value, 0))[0]
    line(axes, (x, 690), (x, 698), stroke_width="1")
    label(left, f"overview-x-tick-{value}", x, 721, str(value), 17,
          anchor="middle", math_font=True)
for value in (-200, 0, 400, 1000):
    y = overview((0, value))[1]
    line(axes, (327, y), (335, y), stroke_width="1")
    if value != 0:
        label(left, f"overview-y-tick-{value}", 317, y + 5, str(value), 17,
              anchor="end", math_font=True)
label(left, "overview-axis-x-label", 822, 747, "x (m)", 20, math_font=True)
label(left, "overview-axis-y-label", 277, 120, "y (m)", 20, math_font=True)

bearings_group = el(left, "g", id="bearing-constructions", clip_path="url(#overview-clip)")
for i in (1, 2, 3):
    s = stations[i]
    sg = el(bearings_group, "g", id=f"bearing-S{i}")
    for offset, tag in ((-1, "minus-one-degree"), (0, "center"), (1, "plus-one-degree")):
        theta = math.radians(bearings[i] + offset)
        endpoint = (s[0] + 2000 * math.cos(theta), s[1] + 2000 * math.sin(theta))
        line(sg, overview(s), overview(endpoint), id=f"ray-S{i}-{tag}", fill="none",
             stroke=("#4b5960" if offset == 0 else "#aeb9bc"),
             stroke_width=("1.8" if offset == 0 else "1.3"),
             stroke_dasharray=("8 6" if offset == 0 else "2.5 5"))

poly_overview = el(left, "g", id="region-Omega-overview")
polygon(poly_overview, [overview(p) for p in vertices], fill="#bfdad9",
        stroke="#174d52", stroke_width="2.1")
diamond(left, "node-G-overview", overview(G), r=7)
for i, s in stations.items():
    point(left, f"node-S{i}", overview(s), r=5.7)

el(left, "rect", id="overview-legend-background", x="57", y="132", width="256",
   height="144", fill="white", stroke="#999", stroke_width="0.8")
el(left, "rect", id="overview-G-label-background", x="497", y="449", width="153",
   height="31", fill="white")
legend_left_marks = el(left, "g", id="overview-legend-marks")
line(legend_left_marks, (70, 158), (108, 158), stroke="#4b5960", stroke_width="1.8", stroke_dasharray="8 6")
line(legend_left_marks, (70, 184), (108, 184), stroke="#aeb9bc", stroke_width="1.3", stroke_dasharray="2.5 5")
el(legend_left_marks, "rect", x="76", y="202", width="25", height="17", fill="#bfdad9", stroke="#174d52", stroke_width="1")
point(legend_left_marks, "legend-station-mark", (88, 237), r=4.8)
diamond(legend_left_marks, "legend-true-source-mark", (88, 263), r=5.6)
ol = el(left, "g", id="native-editable-labels-overview")
label(ol, "label-S1-overview", 124, 798, "S₁=(−500,−200)", 20, math_font=True)
label(ol, "label-S2-overview", 612, 773, "S₂=(900,−100)", 20, math_font=True)
label(ol, "label-S3-overview", 350, 207, "S₃=(0,1000)", 20, math_font=True)
label(ol, "label-G-overview", 502, 473, "G=(300,400)", 21,
      math_font=True, fill="#91521f")
line(left, (503, 480), overview(G), id="leader-G-overview", stroke="#91521f", stroke_width="1.1")
label(ol, "label-overview-legend-center", 119, 164, "测向中心线", 16, fill="#444")
label(ol, "label-overview-legend-boundary", 119, 190, "±1° 误差边界", 16, fill="#777")
label(ol, "label-overview-legend-region", 119, 216, "公共区域 Ω", 16)
label(ol, "label-overview-legend-station", 119, 243, "检测点 Sᵢ", 16)
label(ol, "label-overview-legend-source", 119, 269, "真实位置 G", 16)
label(ol, "label-overview-target-circle-offscreen", 458, 837,
      "目标圆半径 1800 m；本局部视图未显示其边界。", 17,
      anchor="middle", fill="#555")

right = el(root, "g", id="six-vertex-polygon-detail")
label(right, "label-detail-title", 1288, 112, "定位区域与直径圆（局部放大）", 25, anchor="middle")
detail_grid = el(right, "g", id="detail-grid", fill="none", stroke="#e5e8e8", stroke_width="1")
for xvalue in (280, 290, 300, 310, 320):
    x = detail((xvalue, 414))[0]
    line(detail_grid, (x, 178), (x, 725))
for yvalue in (390, 400, 410, 420, 430):
    y = detail((300, yvalue))[1]
    line(detail_grid, (1040, y), (1540, y))
detail_axes = el(right, "g", id="detail-axes", fill="none", stroke="#111", stroke_width="1.2")
line(detail_axes, (1040, 725), (1546, 725), id="detail-x-axis", marker_end="url(#arrow)")
line(detail_axes, (1040, 725), (1040, 208), id="detail-y-axis", marker_end="url(#arrow)")
dl = el(right, "g", id="native-editable-labels-detail")
for value in (280, 290, 300, 310, 320):
    label(dl, f"detail-x-tick-{value}", detail((value, 414))[0], 752,
          str(value), 17, anchor="middle", math_font=True)
for value in (390, 400, 410, 420, 430):
    label(dl, f"detail-y-tick-{value}", 1028, detail((300, value))[1] + 6,
          str(value), 17, anchor="end", math_font=True)
label(dl, "detail-axis-x-label", 1519, 781, "x (m)", 20, math_font=True)
label(dl, "detail-axis-y-label", 968, 222, "y (m)", 20, math_font=True)

diameter_circle = el(right, "g", id="diameter-circle")
el(diameter_circle, "circle", id="circle-center-C-radius-r", cx=f"{detail(C)[0]:.4f}",
   cy=f"{detail(C)[1]:.4f}", r=f"{11.5*r:.4f}", fill="none", stroke="#386c65",
   stroke_width="2.1", stroke_dasharray="9 7")
region = el(right, "g", id="region-Omega-detail")
polygon(region, [detail(p) for p in vertices], fill="#dbe9e9",
        stroke="#174d52", stroke_width="2.1")
diameter = el(right, "g", id="farthest-vertex-pair")
line(diameter, detail(V[3]), detail(V[6]), id="diameter-V3-V6", stroke="#9e5930", stroke_width="3.2")
for i, p in V.items():
    point(right, f"node-V{i}", detail(p), r=(6.1 if i in (3, 6) else 4.7), fill="#174d52")
diamond(right, "node-G-detail", detail(G), r=7)
point(right, "node-C-center", detail(C), r=4.8, fill="#111")

positions = {
    1: (12, -10), 2: (-47, 24), 3: (7, 29),
    4: (10, 10), 5: (23, 8), 6: (-48, -13),
}
for i, p in V.items():
    dx, dy = positions[i]
    label(dl, f"label-V{i}", detail(p)[0] + dx, detail(p)[1] + dy,
          f"V{i}", 20, math_font=True)
label(dl, "label-C-center", detail(C)[0] + 15, detail(C)[1] + 9,
      "C", 21, math_font=True)
label(dl, "label-G-detail", detail(G)[0] - 33, detail(G)[1] + 4,
      "G", 21, math_font=True, fill="#91521f")
label(dl, "label-detail-circle-center", 1288, 886,
      f"C=({C[0]:.4f},{C[1]:.4f}) m", 18, anchor="middle", math_font=True)
label(dl, "label-diameter", 1288, 799, f"V₃—V₆：D={D:.4f} m；r={r:.4f} m", 19,
      anchor="middle", math_font=True)
label(dl, "label-detail-covered", 1288, 837,
      "六个顶点均在圆内；本算例覆盖。", 19, anchor="middle")
el(right, "rect", id="detail-legend-background", x="941", y="128",
   width="694", height="67", fill="white", stroke="#999", stroke_width="0.8")
legend_detail_marks = el(right, "g", id="detail-legend-marks")
line(legend_detail_marks, (957, 150), (995, 150), stroke="#386c65", stroke_width="2", stroke_dasharray="9 7")
el(legend_detail_marks, "rect", x="1159", y="140", width="24", height="17", fill="#dbe9e9", stroke="#174d52", stroke_width="1")
line(legend_detail_marks, (1370, 150), (1401, 150), stroke="#9e5930", stroke_width="3")
point(legend_detail_marks, "legend-vertex-mark", (976, 179), r=4.3, fill="#174d52")
point(legend_detail_marks, "legend-center-mark", (1183, 179), r=4.3)
diamond(legend_detail_marks, "legend-G-mark", (1385, 179), r=5.5)
label(dl, "label-legend-diameter-circle", 1005, 156, "直径圆", 16)
label(dl, "label-legend-polygon", 1194, 156, "定位六边形 Ω", 16)
label(dl, "label-legend-diameter", 1412, 156, "直径 V₃V₆", 16)
label(dl, "label-legend-vertex", 993, 185, "顶点 Vᵢ", 16)
label(dl, "label-legend-center", 1200, 185, "圆心 C", 16)
label(dl, "label-legend-source", 1402, 185, "真实位置 G", 16)
right.remove(dl)
right.append(dl)

footer = el(root, "g", id="figure-conclusion")
label(footer, "label-footer-conclusion", 836, 916,
      "三站 ±1° 示向 → 求凸六边形 → 最远点对 V₃、V₆ → 作直径圆 → 逐顶点检验",
      22, anchor="middle")

ET.indent(root, space="  ")
ET.ElementTree(root).write(OUT, encoding="utf-8", xml_declaration=True)
print(OUT)
print("vertices:", vertices)
print("diameter:", D, "endpoints:", diameter_endpoints)
print("circle:", C, r, "covers:", result["circle"]["covers"])
