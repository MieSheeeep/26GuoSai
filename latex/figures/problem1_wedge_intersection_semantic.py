"""Generate the structure-first, monochrome bearing-wedge illustration.

Geometry is constructed from angular half-plane constraints.  The left panel
uses an explicitly labelled vertical magnification to make ±1 degree legible.
"""

from __future__ import annotations

import math
from pathlib import Path
from xml.etree import ElementTree as ET


HERE = Path(__file__).resolve().parent
OUT = HERE / "problem1_wedge_intersection_semantic.svg"
SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)


def el(parent, tag, **attrs):
    return ET.SubElement(parent, f"{{{SVG}}}{tag}", {k.replace("_", "-"): str(v) for k, v in attrs.items()})


def polygon(parent, points, **attrs):
    return el(parent, "polygon", points=" ".join(f"{x:.3f},{y:.3f}" for x, y in points), **attrs)


def line(parent, a, b, **attrs):
    return el(parent, "line", x1=f"{a[0]:.3f}", y1=f"{a[1]:.3f}", x2=f"{b[0]:.3f}", y2=f"{b[1]:.3f}", **attrs)


def text(parent, id_, x, y, pieces, size=27, anchor=None, italic=True, **attrs):
    kw = dict(id=id_, x=x, y=y, font_size=size, font_family="Times New Roman, Cambria Math, serif", fill="#111")
    if anchor:
        kw["text_anchor"] = anchor
    if italic:
        kw["font_style"] = "italic"
    kw.update(attrs)
    t = el(parent, "text", **kw)
    for value, role in pieces:
        if role == "sub":
            s = el(t, "tspan", font_size="70%", baseline_shift="sub")
        elif role == "sup":
            s = el(t, "tspan", font_size="70%", baseline_shift="super")
        else:
            s = el(t, "tspan")
        s.text = value
    return t


def clip_halfplane(poly, origin, direction, keep_positive=True):
    sign = 1 if keep_positive else -1

    def value(p):
        return sign * (direction[0] * (p[1] - origin[1]) - direction[1] * (p[0] - origin[0]))

    out = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        fa, fb = value(a), value(b)
        ia, ib = fa >= -1e-9, fb >= -1e-9
        if ia:
            out.append(a)
        if ia != ib:
            q = fa / (fa - fb)
            out.append((a[0] + q * (b[0] - a[0]), a[1] + q * (b[1] - a[1])))
    return out


def wedge(poly, station, aim, half_deg):
    theta = math.atan2(aim[1] - station[1], aim[0] - station[0])
    half = math.radians(half_deg)
    lower = (math.cos(theta - half), math.sin(theta - half))
    upper = (math.cos(theta + half), math.sin(theta + half))
    return clip_halfplane(clip_halfplane(poly, station, lower), station, upper, False)


def ray_endpoint(station, direction, box):
    xmin, ymin, xmax, ymax = box
    candidates = []
    for value, start, delta in ((xmin, station[0], direction[0]), (xmax, station[0], direction[0]),
                                (ymin, station[1], direction[1]), (ymax, station[1], direction[1])):
        if abs(delta) < 1e-12:
            continue
        t = (value - start) / delta
        if t > 1e-9:
            p = (station[0] + t * direction[0], station[1] + t * direction[1])
            if xmin - 1e-7 <= p[0] <= xmax + 1e-7 and ymin - 1e-7 <= p[1] <= ymax + 1e-7:
                candidates.append((t, p))
    return min(candidates)[1]


def close(a, b, eps=0.02):
    return abs(a[0] - b[0]) < eps and abs(a[1] - b[1]) < eps


def inside_wedge(point, station, aim, half_deg, eps=1e-7):
    theta = math.atan2(aim[1] - station[1], aim[0] - station[0])
    half = math.radians(half_deg)
    minus = (math.cos(theta - half), math.sin(theta - half))
    plus = (math.cos(theta + half), math.sin(theta + half))
    delta = (point[0] - station[0], point[1] - station[1])
    cross_minus = minus[0] * delta[1] - minus[1] * delta[0]
    cross_plus = plus[0] * delta[1] - plus[1] * delta[0]
    return cross_minus >= -eps and cross_plus <= eps


root = ET.Element(f"{{{SVG}}}svg", {
    "width": "1672", "height": "941", "viewBox": "0 0 1672 941", "role": "img",
    "aria-label": "Single bearing wedge and intersection of three bearing wedges",
})
el(root, "title").text = "有界示向角域与三次示向的公共定位区域"
el(root, "desc").text = "左幅为纵向放大十倍的正负一度扇形；右幅由三个扇形的半平面交计算定位多边形。"
defs = el(root, "defs")
pattern1 = el(defs, "pattern", id="hatch-W1", patternUnits="userSpaceOnUse", width="10", height="10", patternTransform="rotate(45)")
line(pattern1, (0, 0), (0, 10), stroke="#d5d5d5", stroke_width="2")
pattern3 = el(defs, "pattern", id="hatch-W3", patternUnits="userSpaceOnUse", width="12", height="12", patternTransform="rotate(-45)")
line(pattern3, (0, 0), (0, 12), stroke="#dedede", stroke_width="2")
el(defs, "marker", id="arrow", markerWidth="8", markerHeight="8", refX="7", refY="4", orient="auto", markerUnits="strokeWidth")
arrow = defs[-1]
el(arrow, "path", d="M0,0 L8,4 L0,8 Z", fill="#111")

frame = el(root, "g", id="panels", fill="white", stroke="#111", stroke_width="1.5")
el(frame, "rect", id="panel-single", x="16", y="68", width="805", height="806")
el(frame, "rect", id="panel-intersection", x="851", y="68", width="805", height="806")

# Left: real angular slopes are computed before applying the stated y scale.
left = el(root, "g", id="single-bearing-construction")
S = (106.0, 475.0)
end_x = 680.0
mag = 10.0
rise = mag * (end_x - S[0]) * math.tan(math.radians(1.0))
upper_end = (end_x, S[1] - rise)
lower_end = (end_x, S[1] + rise)
region = el(left, "g", id="region-Wi")
polygon(region, [S, upper_end, lower_end], fill="#f2f2f2")
polygon(region, [S, upper_end, lower_end], fill="url(#hatch-W1)")
boundaries = el(left, "g", id="bearing-rays", fill="none", stroke="#111", stroke_width="2.2")
line(boundaries, S, upper_end, id="ray-theta-upper", marker_end="url(#arrow)")
line(boundaries, S, (703, S[1]), id="ray-theta-center", stroke_dasharray="6 5", stroke_width="1.6", marker_end="url(#arrow)")
line(boundaries, S, lower_end, id="ray-theta-lower", marker_end="url(#arrow)")
el(left, "circle", id="node-Si", cx=S[0], cy=S[1], r="5.6", fill="#111")

# Arc positions use the magnified displayed slope, while their labels state
# the unscaled physical half-angle and the note explains the display transform.
shown = math.atan(mag * math.tan(math.radians(1)))
for name, radius, sign in (("upper", 153, -1), ("lower", 153, 1)):
    x0, y0 = S[0] + radius, S[1]
    x1, y1 = S[0] + radius * math.cos(shown), S[1] + sign * radius * math.sin(shown)
    el(left, "path", id=f"angle-arc-{name}", d=f"M{x0:.3f},{y0:.3f} A{radius},{radius} 0 0,{1 if sign > 0 else 0} {x1:.3f},{y1:.3f}", fill="none", stroke="#111", stroke_width="1.5")

labels = el(left, "g", id="native-editable-labels-single")
text(labels, "label-Si", 59, 451, [("S", "normal"), ("i", "sub")], 31)
text(labels, "label-theta-upper", 688, 374, [("θ", "normal"), ("i", "sub"), (" + 1°", "normal")], 27)
text(labels, "label-theta-center", 710, 484, [("θ", "normal"), ("i", "sub")], 27)
text(labels, "label-theta-lower", 688, 589, [("θ", "normal"), ("i", "sub"), (" − 1°", "normal")], 27)
text(labels, "label-Wi", 481, 476, [("W", "normal"), ("i", "sub")], 35)
text(labels, "label-angle-upper", 274, 457, [("1°", "normal")], 22, italic=False)
text(labels, "label-angle-lower", 274, 506, [("1°", "normal")], 22, italic=False)

text(labels, "label-upper-halfplane", 254, 273,
     [("cross(u(θ", "normal"), ("i", "sub"), ("+1°), x−S", "normal"), ("i", "sub"), (") ≤ 0", "normal")],
     24, italic=False)
text(labels, "label-lower-halfplane", 253, 704,
     [("cross(u(θ", "normal"), ("i", "sub"), ("−1°), x−S", "normal"), ("i", "sub"), (") ≥ 0", "normal")],
     24, italic=False)
leaders = el(left, "g", id="constraint-leaders", fill="none", stroke="#111", stroke_width="1.3")
line(leaders, (425, 284), (432, S[1] - mag * (432 - S[0]) * math.tan(math.radians(1)) - 8), marker_end="url(#arrow)")
line(leaders, (421, 672), (432, S[1] + mag * (432 - S[0]) * math.tan(math.radians(1)) + 8), marker_end="url(#arrow)")
el(labels, "text", id="label-vertical-magnification", x="416", y="824", text_anchor="middle",
   font_family="Microsoft YaHei, SimHei, sans-serif", font_size="19", fill="#333").text = "纵向放大 10 倍；实际半角各 1°"

# Right: all wedge polygons and intersection vertices come from clipping.
right = el(root, "g", id="three-bearing-intersection", transform="translate(851 68)")
box = [(1.5, 1.5), (803.5, 1.5), (803.5, 804.5), (1.5, 804.5)]
rect = (1.5, 1.5, 803.5, 804.5)
stations = {1: (65.0, 735.0), 2: (725.0, 680.0), 3: (360.0, 80.0)}
aim = (360.0, 480.0)
# The right panel is an aperture-enlarged construction diagram, as in the
# paper's original generator; its explicit note prevents a false 1° reading.
half_angle = 8.0
styles = {1: ("#f8f8f8", "url(#hatch-W1)"), 2: ("#ebebeb", None), 3: ("#f6f6f6", "url(#hatch-W3)")}
overlap = box[:]
for i in (1, 2, 3):
    s = stations[i]
    w = wedge(box[:], s, aim, half_angle)
    overlap = wedge(overlap, s, aim, half_angle)
    g = el(right, "g", id=f"region-W{i}")
    polygon(g, w, fill=styles[i][0])
    if styles[i][1]:
        polygon(g, w, fill=styles[i][1])

ray_groups = el(right, "g", id="wedge-boundaries", stroke="#111", stroke_width="1.35", fill="none")
for i in (1, 2, 3):
    s = stations[i]
    theta = math.atan2(aim[1] - s[1], aim[0] - s[0])
    g = el(ray_groups, "g", id=f"rays-S{i}")
    for side, name in ((-1, "minus"), (1, "plus")):
        angle = theta + side * math.radians(half_angle)
        d = (math.cos(angle), math.sin(angle))
        end = ray_endpoint(s, d, rect)
        line(g, s, end, id=f"ray-S{i}-{name}")

region_omega = el(right, "g", id="region-Omega")
polygon(region_omega, overlap, fill="#d5d5d5", stroke="#111", stroke_width="2.2")
assert len(overlap) == 6, overlap
top = min(overlap, key=lambda p: p[1])
left_lower = min((p for p in overlap if p[1] > 500), key=lambda p: p[0])
right_lower = max((p for p in overlap if p[1] > 500), key=lambda p: p[0])
for name, point in (("A", top), ("B", left_lower), ("C", right_lower)):
    el(right, "circle", id=f"node-{name}", cx=f"{point[0]:.3f}", cy=f"{point[1]:.3f}", r="5.3", fill="#111")
for p in overlap:
    assert all(inside_wedge(p, station, aim, half_angle) for station in stations.values())
    if p not in (top, left_lower, right_lower):
        el(right, "circle", cx=f"{p[0]:.3f}", cy=f"{p[1]:.3f}", r="2.5", fill="#111")

nodes = el(right, "g", id="stations")
for i, s in stations.items():
    el(nodes, "circle", id=f"node-S{i}", cx=s[0], cy=s[1], r="5.6", fill="#111")

rl = el(right, "g", id="native-editable-labels-intersection")
text(rl, "label-S1", 34, 771, [("S", "normal"), ("1", "sub")], 31)
text(rl, "label-S2", 742, 713, [("S", "normal"), ("2", "sub")], 31)
text(rl, "label-S3", 342, 58, [("S", "normal"), ("3", "sub")], 31)
text(rl, "label-W1", 168, 658, [("W", "normal"), ("1", "sub")], 31)
text(rl, "label-W2", 614, 638, [("W", "normal"), ("2", "sub")], 31)
text(rl, "label-W3", 365, 272, [("W", "normal"), ("3", "sub")], 31)
text(rl, "label-Omega", 360, 485, [("Ω", "normal")], 39, anchor="middle")
text(rl, "label-A", top[0] - 19, top[1] - 13, [("A", "normal")], 26)
text(rl, "label-B", left_lower[0] - 23, left_lower[1] + 31, [("B", "normal")], 26)
text(rl, "label-C", right_lower[0] + 8, right_lower[1] + 29, [("C", "normal")], 26)
el(rl, "rect", id="note-background", x="270", y="758", width="270", height="37", fill="white")
el(rl, "text", id="label-right-schematic-scale", x="405", y="786", text_anchor="middle",
   font_family="Microsoft YaHei, SimHei, sans-serif", font_size="18", fill="#333").text = "右幅角度示意；模型半角仍为 1°"

# The marked crossing of two extended boundary rays is outside W2.
def crossing(s, d, t, e):
    q = (t[0] - s[0], t[1] - s[1])
    det = d[0] * e[1] - d[1] * e[0]
    lam = (q[0] * e[1] - q[1] * e[0]) / det
    return (s[0] + lam * d[0], s[1] + lam * d[1])


th1 = math.atan2(aim[1] - stations[1][1], aim[0] - stations[1][0]) - math.radians(half_angle)
th3 = math.atan2(aim[1] - stations[3][1], aim[0] - stations[3][0]) - math.radians(half_angle)
excluded = crossing(stations[1], (math.cos(th1), math.sin(th1)),
                    stations[3], (math.cos(th3), math.sin(th3)))
assert 1.5 < excluded[0] < 803.5 and 1.5 < excluded[1] < 804.5
assert inside_wedge(excluded, stations[1], aim, half_angle)
assert inside_wedge(excluded, stations[3], aim, half_angle)
assert not inside_wedge(excluded, stations[2], aim, half_angle)
eg = el(right, "g", id="excluded-boundary-crossing")
line(eg, (excluded[0] - 7, excluded[1] - 7), (excluded[0] + 7, excluded[1] + 7), stroke="#111", stroke_width="2")
line(eg, (excluded[0] - 7, excluded[1] + 7), (excluded[0] + 7, excluded[1] - 7), stroke="#111", stroke_width="2")
el(eg, "text", id="label-excluded", x=f"{excluded[0] + 15:.3f}", y=f"{excluded[1] - 11:.3f}",
   font_family="Microsoft YaHei, SimHei, sans-serif", font_size="20", fill="#111").text = "排除"

ET.indent(root, space="  ")
ET.ElementTree(root).write(OUT, encoding="utf-8", xml_declaration=True)
print(OUT)
print("Omega vertices:", [(round(x, 2), round(y, 2)) for x, y in overlap])
print("A, B, C:", top, left_lower, right_lower)
print("Excluded crossing:", excluded)
