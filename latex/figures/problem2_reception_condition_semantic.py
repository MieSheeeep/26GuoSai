"""Exact-scale compatible reception disks for two illustrative source sites."""

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


def point(parent, id_, p, fill="#111", r=6.0):
    return el(parent, "circle", id=id_, cx=f"{p[0]:.4f}", cy=f"{p[1]:.4f}", r=r, fill=fill)


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


S1 = (0.0, 0.0)
S2 = (525.0, 60.0)
G_near = (500.0, 0.0)
G_far = (1400.0, 0.0)
rho_near = max(1000.0, dist(G_near, S1))
rho_far = max(1000.0, dist(G_far, S1))
d_near = dist(S2, G_near)
d_far = dist(S2, G_far)
assert rho_near == 1000.0 and rho_far == 1400.0
assert d_near == 65.0 and abs(d_far - math.sqrt(769225)) < 1e-10
assert d_near <= rho_near and d_far <= rho_far
assert dist(S1, G_near) <= rho_near and dist(S1, G_far) <= rho_far

# One uniform scale is used for both circles and all four coordinate points.
SCALE = 0.28


def xy(p):
    return (260 + SCALE * p[0], 485 - SCALE * p[1])


root = ET.Element(f"{{{SVG}}}svg", {
    "width": "1672", "height": "1000", "viewBox": "0 0 1672 1000", "role": "img",
    "aria-label": "Two example compatible reception disks and second detector check",
})
el(root, "title").text = "全向源的最小兼容接收半径与第二检测点"
el(root, "desc").text = "近源虚线圆半径一千米，远源实线圆半径一千四百米；两个检测点位于两圆内，但两点检验不构成整个可行域的保证。"
defs = el(root, "defs")
arrow = el(defs, "marker", id="arrow", markerWidth="8", markerHeight="8", refX="7", refY="4",
           orient="auto", markerUnits="strokeWidth")
el(arrow, "path", d="M0,0 L8,4 L0,8 Z", fill="#111")

frames = el(root, "g", id="panel-frames", fill="white", stroke="#111", stroke_width="1.4")
el(frames, "rect", id="panel-equal-scale-geometry", x="16", y="45", width="1104", height="855")
el(frames, "rect", id="panel-explanation", x="1140", y="45", width="516", height="855")

plot = el(root, "g", id="two-compatible-reception-disks")
far_disk = el(plot, "g", id="disk-G-far-rho-1400")
el(far_disk, "circle", id="circle-far-r1400", cx=xy(G_far)[0], cy=xy(G_far)[1], r=SCALE * rho_far,
   fill="none", stroke="#25765f", stroke_width="2.5")
near_disk = el(plot, "g", id="disk-G-near-rho-1000")
el(near_disk, "circle", id="circle-near-r1000", cx=xy(G_near)[0], cy=xy(G_near)[1], r=SCALE * rho_near,
   fill="none", stroke="#315fa5", stroke_width="2.5", stroke_dasharray="10 7")

axes = el(plot, "g", id="coordinate-axes", fill="none", stroke="#111", stroke_width="1.5")
line(axes, (92, 485), (1084, 485), id="axis-x", marker_end="url(#arrow)")
line(axes, (260, 883), (260, 68), id="axis-y", marker_end="url(#arrow)")
for value in (-500, 0, 1000, 1400, 2000, 2800):
    x = xy((value, 0))[0]
    line(axes, (x, 485), (x, 494), id=f"tick-x-{value}", stroke_width="1.1")
for value in (-1400, -1000, -500, 500, 1000, 1400):
    y = xy((0, value))[1]
    line(axes, (250, y), (260, y), id=f"tick-y-{value}", stroke_width="1.1")

checks = el(plot, "g", id="sample-distance-checks", fill="none", stroke="#a97137", stroke_width="1.3")
line(checks, xy(S2), xy(G_near), id="distance-S2-G-near")
line(checks, xy(S2), xy(G_far), id="distance-S2-G-far", stroke_dasharray="6 5")

points = el(plot, "g", id="stations-and-possible-sources")
point(points, "node-S1", xy(S1), fill="#111", r=6.2)
point(points, "node-S2", xy(S2), fill="#ba6a1a", r=6.5)
point(points, "node-G-near", xy(G_near), fill="#315fa5", r=6.2)
point(points, "node-G-far", xy(G_far), fill="#25765f", r=6.2)

pl = el(plot, "g", id="native-editable-labels-geometry")
label(pl, "label-axis-x", 1049, 556, "x (m)", 23, math_font=True)
label(pl, "label-axis-y", 203, 78, "y (m)", 23, math_font=True)
for value in (-500, 0, 1000, 1400, 2000, 2800):
    x = xy((value, 0))[0]
    label(pl, f"label-tick-x-{value}", x, 518, str(value), 16, anchor="middle", math_font=True)
for value in (-1400, -1000, -500, 500, 1000, 1400):
    y = xy((0, value))[1]
    label(pl, f"label-tick-y-{value}", 241, y + 5, str(value), 16, anchor="end", math_font=True)

label(pl, "label-near-circle", 104, 181, "B(Gₙₑₐᵣ,1000)  虚线", 23,
      math_font=True, fill="#315fa5")
label(pl, "label-far-circle", 755, 80, "B(Gfar,1400)  实线", 23,
      math_font=True, fill="#25765f")
label(pl, "label-S1", 167, 555, "S₁=(0,0)", 22, math_font=True)
label(pl, "label-S2", 450, 424, "S₂=(525,60)", 22, math_font=True, fill="#a65a12")
label(pl, "label-G-near", 359, 560, "Gnear=(500,0)", 22,
      math_font=True, fill="#315fa5")
label(pl, "label-G-far", 631, 548, "Gfar=(1400,0)", 22,
      math_font=True, fill="#25765f")
leaders = el(plot, "g", id="point-label-leaders", fill="none", stroke_width="1.1")
line(leaders, (453, 432), xy(S2), stroke="#a65a12")
line(leaders, (395, 540), xy(G_near), stroke="#315fa5")

notes = el(root, "g", id="distance-logic-notes")
label(notes, "label-notes-title", 1398, 95, "全向源：两点检验", 28, anchor="middle")
label(notes, "label-rho-general", 1168, 153, "ρ(g)=max{1000, ‖g−S₁‖₂}",
      24, math_font=True)
line(notes, (1168, 177), (1628, 177), stroke="#aaa", stroke_width="1")

label(notes, "label-near-heading", 1168, 222, "近源 Gnear=(500,0)", 23,
      math_font=True, fill="#315fa5")
label(notes, "label-near-rho", 1182, 259, "ρ(Gnear)=1000 m", 21,
      math_font=True, fill="#315fa5")
label(notes, "label-near-distance", 1182, 296, f"‖S₂−Gnear‖={d_near:.1f} m", 21,
      math_font=True)
label(notes, "label-near-checked", 1182, 330, "65.0 ≤ 1000：可再次接收", 20)

line(notes, (1168, 359), (1628, 359), stroke="#ccc", stroke_width="1")
label(notes, "label-far-heading", 1168, 404, "远源 Gfar=(1400,0)", 23,
      math_font=True, fill="#25765f")
label(notes, "label-far-rho", 1182, 441, "ρ(Gfar)=1400 m", 21,
      math_font=True, fill="#25765f")
label(notes, "label-far-distance", 1182, 478, f"‖S₂−Gfar‖≈{d_far:.1f} m", 21,
      math_font=True)
label(notes, "label-far-checked", 1182, 512, "877.1 ≤ 1400：可再次接收", 20)

line(notes, (1168, 542), (1628, 542), stroke="#ccc", stroke_width="1")
label(notes, "label-two-samples-only", 1168, 584,
      "两点示意，非整个可行域保证。", 21)
label(notes, "label-directional-limit", 1168, 619,
      "定向源还受朝向限制。", 21)
label(notes, "label-global-intro", 1168, 674,
      "全域保证须对每个 g∈Ω₁ 检验：", 21)
el(notes, "rect", id="all-source-criterion-box", x="1165", y="697", width="466", height="111",
   fill="white", stroke="#111", stroke_width="1.3")
label(notes, "label-all-source-criterion", 1398, 740,
      "∀g∈Ω₁，‖S₂−g‖₂≤ρ(g)", 22, anchor="middle", math_font=True)
label(notes, "label-all-source-intersection", 1398, 780,
      "S₂ ∈ ⋂{B(g,ρ(g)) : g∈Ω₁}", 21, anchor="middle", math_font=True)
label(notes, "label-both-stations-in-disks", 1398, 851,
      "S₁ 在两圆内（远源圆边界上）。", 18,
      anchor="middle", fill="#444")
label(notes, "label-scope-omnidirectional", 1398, 881,
      "S₂ 在两圆内；距离条件仅适用于全向源。", 18,
      anchor="middle", fill="#444")

footer = el(root, "g", id="decision-flow-footer")
label(footer, "label-algorithm-flow", 836, 955,
      "首次成功接收 → 求 ρ(g) → 画兼容接收圆 → 检查 S₂ 是否在圆内 → 判断再次接收",
      24, anchor="middle")

ET.indent(root, space="  ")
ET.ElementTree(root).write(OUT, encoding="utf-8", xml_declaration=True)
print(OUT)
print("rho near/far:", rho_near, rho_far)
print("S2 distances:", d_near, d_far)
print("pixel points:", {"S1": xy(S1), "S2": xy(S2), "Gnear": xy(G_near), "Gfar": xy(G_far)})
