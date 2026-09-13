"""Exact geometric, monochrome SVG for the diameter-circle coverage test."""

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


def polygon(parent, pts, **attrs):
    return el(parent, "polygon", points=" ".join(f"{x:.4f},{y:.4f}" for x, y in pts), **attrs)


def label(parent, id_, x, y, parts, size=27, anchor=None, italic=True, family=None, **attrs):
    kw = dict(id=id_, x=f"{x:.4f}", y=f"{y:.4f}", font_size=size,
              font_family=family or "Times New Roman, Cambria Math, serif", fill="#111")
    if anchor:
        kw["text_anchor"] = anchor
    if italic:
        kw["font_style"] = "italic"
    kw.update(attrs)
    t = el(parent, "text", **kw)
    for value, role in parts:
        if role == "sub":
            s = el(t, "tspan", font_size="70%", baseline_shift="sub")
        elif role == "sup":
            s = el(t, "tspan", font_size="70%", baseline_shift="super")
        else:
            s = el(t, "tspan")
        s.text = value
    return t


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


root = ET.Element(f"{{{SVG}}}svg", {
    "width": "1672", "height": "941", "viewBox": "0 0 1672 941",
    "role": "img", "aria-label": "Diameter circle counterexample and covering example",
})
el(root, "title").text = "最远点对确定的直径圆仍须逐顶点检验"
el(root, "desc").text = "左：边长为二的等边三角形，其顶点C在AB的直径圆外。右：内接正六边形的六个顶点均在FC的直径圆上。"
defs = el(root, "defs")
marker = el(defs, "marker", id="arrow", markerWidth="8", markerHeight="8", refX="7", refY="4",
            orient="auto", markerUnits="strokeWidth")
el(marker, "path", d="M0,0 L8,4 L0,8 Z", fill="#111")

frames = el(root, "g", id="panel-frames", fill="white", stroke="#111", stroke_width="1.5")
el(frames, "rect", id="panel-counterexample", x="16", y="68", width="805", height="765")
el(frames, "rect", id="panel-covered-example", x="851", y="68", width="805", height="765")

# Left panel: one drawing unit is exactly one half-side length, i.e. 1.
left = el(root, "g", id="equilateral-counterexample")
scale = 250.0
M = (412.0, 570.0)
A = (M[0] - scale, M[1])
B = (M[0] + scale, M[1])
C = (M[0], M[1] - math.sqrt(3) * scale)
assert all(abs(distance(p, q) - 2 * scale) < 1e-9 for p, q in ((A, B), (B, C), (C, A)))
assert abs(distance(A, M) - scale) < 1e-9 and abs(distance(B, M) - scale) < 1e-9
assert abs(distance(C, M) - math.sqrt(3) * scale) < 1e-9
assert distance(C, M) > scale

circle_left = el(left, "g", id="diameter-circle-AB")
el(circle_left, "circle", id="disk-B-M-1", cx=M[0], cy=M[1], r=scale,
   fill="#f1f1f1", stroke="#111", stroke_width="2")
tri = el(left, "g", id="region-triangle-ABC")
polygon(tri, (A, B, C), fill="none", stroke="#111", stroke_width="2.2")
measure_left = el(left, "g", id="measurements-triangle", fill="none", stroke="#111", stroke_width="1.6")
line(measure_left, A, B, id="diameter-AB", stroke_width="2.3")
line(measure_left, M, C, id="altitude-MC", stroke_dasharray="8 6")
radius_endpoint = (M[0] + scale * math.cos(math.radians(20)),
                   M[1] - scale * math.sin(math.radians(20)))
line(measure_left, M, radius_endpoint, id="radius-M-to-circle", stroke_width="1.8")
points_left = el(left, "g", id="vertices-and-midpoint-triangle", fill="#111")
for name, p in (("A", A), ("B", B), ("C", C), ("M", M)):
    el(points_left, "circle", id=f"node-{name}-triangle", cx=f"{p[0]:.4f}", cy=f"{p[1]:.4f}", r="5.7")

texts_left = el(left, "g", id="native-editable-labels-triangle")
label(texts_left, "label-A-triangle", A[0] - 27, A[1] + 8, [("A", "normal")], 29)
label(texts_left, "label-B-triangle", B[0] + 11, B[1] + 8, [("B", "normal")], 29)
label(texts_left, "label-C-triangle", C[0] - 10, C[1] - 20, [("C", "normal")], 29)
label(texts_left, "label-M", M[0] - 10, M[1] + 34, [("M", "normal")], 28)
label(texts_left, "label-AB-equals-2", M[0], 651,
      [("AB = D = 2", "normal")], 27, anchor="middle")
label(texts_left, "label-AM-BM-equal-one", M[0], 699,
      [("AM = BM = 1", "normal")], 25, anchor="middle")
label(texts_left, "label-radius-one", 523, 477, [("r = 1", "normal")], 25)
label(texts_left, "label-radius-from-AB", M[0], 738,
      [("r = AB/2 = 1", "normal")], 24, anchor="middle")
label(texts_left, "label-height-inequality", 511, 302,
      [("MC = √3 > 1 = r", "normal")], 27)
label(texts_left, "label-left-conclusion", M[0], 776,
      [("C 位于圆外：未覆盖", "normal")], 21, anchor="middle", italic=False,
      family="Microsoft YaHei, SimHei, sans-serif")
label(texts_left, "label-not-covered", 591, 145, [("未覆盖", "normal")], 30,
      italic=False, family="Microsoft YaHei, SimHei, sans-serif")
line(left, (572, 137), (C[0] + 23, C[1] + 1), id="leader-uncovered-C",
     stroke="#111", stroke_width="1.5", marker_end="url(#arrow)")

# Right panel: six vertices are generated from a single center and radius.
right = el(root, "g", id="regular-hexagon-covered-example")
O = (1255.0, 456.0)
R = 269.0
angles = {"C": 0, "D": -60, "E": -120, "F": 180, "A": 120, "B": 60}
vertices = {name: (O[0] + R * math.cos(math.radians(deg)),
                   O[1] + R * math.sin(math.radians(deg))) for name, deg in angles.items()}
F, C2 = vertices["F"], vertices["C"]
assert abs(distance(F, C2) - 2 * R) < 1e-9
assert abs((F[0] + C2[0]) / 2 - O[0]) < 1e-9
assert abs((F[1] + C2[1]) / 2 - O[1]) < 1e-9
assert all(abs(distance(p, O) - R) < 1e-9 for p in vertices.values())

circle_right = el(right, "g", id="diameter-circle-FC")
el(circle_right, "circle", id="disk-B-O-R", cx=O[0], cy=O[1], r=R,
   fill="#f7f7f7", stroke="#111", stroke_width="2")
hexagon = el(right, "g", id="region-hexagon-ABCDEF")
polygon(hexagon, [vertices[n] for n in ("A", "B", "C", "D", "E", "F")],
        fill="#e9e9e9", stroke="#111", stroke_width="2.2")
measures_right = el(right, "g", id="measurements-hexagon", fill="none", stroke="#111")
line(measures_right, F, C2, id="diameter-FC", stroke_width="2.3")
line(measures_right, O, vertices["D"], id="radius-O-D", stroke_width="1.7")
points_right = el(right, "g", id="vertices-and-center-hexagon", fill="#111")
for name, p in vertices.items():
    el(points_right, "circle", id=f"node-{name}-hexagon", cx=f"{p[0]:.4f}", cy=f"{p[1]:.4f}", r="5.7")
el(points_right, "circle", id="node-O", cx=O[0], cy=O[1], r="5.7")

texts_right = el(right, "g", id="native-editable-labels-hexagon")
positions = {
    "A": (-9, 35), "B": (9, 35), "C": (13, 9),
    "D": (7, -13), "E": (-24, -13), "F": (-32, 9),
}
for name, point in vertices.items():
    dx, dy = positions[name]
    label(texts_right, f"label-{name}-hexagon", point[0] + dx, point[1] + dy,
          [(name, "normal")], 29)
label(texts_right, "label-O", O[0] - 12, O[1] + 38, [("O", "normal")], 27)
label(texts_right, "label-O-midpoint", O[0], O[1] + 108,
      [("O = (F + C)/2", "normal")], 24, anchor="middle")
label(texts_right, "label-FC-equals-2R", O[0], O[1] - 22,
      [("FC = 2R", "normal")], 27, anchor="middle")
label(texts_right, "label-radius-R", 1351, 336, [("R", "normal")], 27)
label(texts_right, "label-right-conclusion", O[0], 788,
      [("六个顶点均在圆上：覆盖", "normal")], 21, anchor="middle", italic=False,
      family="Microsoft YaHei, SimHei, sans-serif")
label(texts_right, "label-covered", 1515, 133, [("覆盖", "normal")], 30,
      italic=False, family="Microsoft YaHei, SimHei, sans-serif")
line(right, (1510, 146), (1456, 223), id="leader-covered-circle", stroke="#111",
     stroke_width="1.5", marker_end="url(#arrow)")

# Two lines below both panels carry the decision logic, not a visual claim.
footer = el(root, "g", id="coverage-test-footer")
label(footer, "label-algorithm-flow", 836, 872,
      [("最远点对  →  作直径圆  →  逐顶点检验  →  覆盖判定", "normal")],
      25, anchor="middle", italic=False, family="Microsoft YaHei, SimHei, sans-serif")
el(footer, "rect", id="criterion-box", x="565", y="888", width="542", height="43",
   fill="white", stroke="#111", stroke_width="1.3")
label(footer, "label-vertex-criterion", 836, 918,
      [("max { ‖vᵢ − O‖₂ : 1 ≤ i ≤ k } ≤ r + τ", "normal")],
      24, anchor="middle", italic=False)

ET.indent(root, space="  ")
ET.ElementTree(root).write(OUT, encoding="utf-8", xml_declaration=True)
print(OUT)
print("Triangle:", {"A": A, "B": B, "C": C, "M": M, "radius": scale})
print("Hexagon:", {"O": O, "R": R, "vertices": vertices})
