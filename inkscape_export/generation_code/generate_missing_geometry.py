"""Rebuild the metric diagrams that accompany the image-generated paper artwork."""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Polygon


OUT = Path(__file__).resolve().parent
NAVY = "#14365d"
TEAL = "#42b9bc"
BLUE = "#7db9e5"
AMBER = "#e59b35"
GRAY = "#8294a8"

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 10,
        "pdf.fonttype": 42,
        "savefig.facecolor": "white",
    }
)


def save(fig: plt.Figure, filename: str) -> None:
    fig.savefig(OUT / filename, bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)


def clean(ax: plt.Axes, xlim: tuple[float, float], ylim: tuple[float, float]) -> None:
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal", adjustable="box")
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRAY)
    ax.tick_params(colors=NAVY, labelsize=8)
    ax.grid(color="#e5edf2", lw=0.6)
    ax.set_axisbelow(True)


def clip_halfplane(poly: np.ndarray, origin: np.ndarray, direction: np.ndarray, keep_positive: bool) -> np.ndarray:
    def signed(p: np.ndarray) -> float:
        cross = direction[0] * (p[1] - origin[1]) - direction[1] * (p[0] - origin[0])
        return cross if keep_positive else -cross

    out: list[np.ndarray] = []
    for a, b in zip(poly, np.roll(poly, -1, axis=0)):
        fa, fb = signed(a), signed(b)
        ina, inb = fa >= -1e-12, fb >= -1e-12
        if ina:
            out.append(a)
        if ina != inb:
            out.append(a + fa / (fa - fb) * (b - a))
    return np.array(out).reshape(-1, 2)


def wedge(poly: np.ndarray, s: np.ndarray, bearing: float, half_angle: float) -> np.ndarray:
    a = math.radians(bearing - half_angle)
    b = math.radians(bearing + half_angle)
    poly = clip_halfplane(poly, s, np.array([math.cos(a), math.sin(a)]), True)
    return clip_halfplane(poly, s, np.array([math.cos(b), math.sin(b)]), False)


def p1_wedge() -> None:
    fig, (left, right) = plt.subplots(1, 2, figsize=(11.2, 4.1), gridspec_kw={"width_ratios": [1, 1.05]})
    # The one-degree aperture is drawn to scale, with a magnified y range.
    s = np.array([0.0, 0.0])
    x = np.linspace(0, 7, 150)
    low, high = np.tan(np.deg2rad(-1)) * x, np.tan(np.deg2rad(1)) * x
    left.fill_between(x, low, high, color=TEAL, alpha=0.4, label=r"$W_i$")
    left.plot(x, low, color=NAVY, lw=1.5)
    left.plot(x, high, color=NAVY, lw=1.5)
    left.plot(x, np.zeros_like(x), color=GRAY, ls="--", lw=1.1)
    left.scatter([0], [0], color=NAVY, zorder=5)
    left.text(0.05, -0.07, r"$S_i$", color=NAVY)
    left.text(4.25, 0.42, r"上边界 $\theta_i+1^\circ$", color=NAVY)
    left.text(4.25, -0.46, r"下边界 $\theta_i-1^\circ$", color=NAVY)
    left.text(5.7, 0.075, r"$\theta_i$", color=GRAY)
    left.text(1.1, 0.3, r"$\operatorname{cross}(u_-,x-S_i)\geq0$", color=NAVY, fontsize=8)
    left.text(1.1, -0.32, r"$\operatorname{cross}(u_+,x-S_i)\leq0$", color=NAVY, fontsize=8)
    left.text(4.1, 0.18, r"$W_i$", color=NAVY, fontsize=10)
    clean(left, (-0.25, 7.1), (-0.53, 0.53))
    # Keep the mathematical boundary slopes exact; expand only the display's y axis.
    left.set_aspect("auto")
    left.axis("off")
    left.set_title("单次示向：两个半平面的交集（纵向放大）", color=NAVY, fontsize=11)

    bounds = np.array([[-2.5, -2.5], [2.5, -2.5], [2.5, 2.5], [-2.5, 2.5]])
    stations = [np.array([-1.9, -1.3]), np.array([2.0, -1.1]), np.array([0.2, 2.2])]
    colors = [BLUE, TEAL, "#cbbce8"]
    feasible = bounds.copy()
    for i, (station, color) in enumerate(zip(stations, colors), start=1):
        theta = math.degrees(math.atan2(-station[1], -station[0]))
        wp = wedge(bounds.copy(), station, theta, 8.0)
        feasible = wedge(feasible, station, theta, 8.0)
        right.add_patch(Polygon(wp, facecolor=color, alpha=0.22, edgecolor="none"))
        for t in (theta - 8, theta + 8):
            v = np.array([math.cos(math.radians(t)), math.sin(math.radians(t))])
            right.plot([station[0], station[0] + 4.5 * v[0]], [station[1], station[1] + 4.5 * v[1]], color=color, lw=1)
        right.scatter(*station, c=NAVY, s=25, zorder=6)
        right.annotate(rf"$S_{i}$", station, xytext=(4, 4), textcoords="offset points", color=NAVY)
    right.add_patch(Polygon(feasible, closed=True, facecolor=TEAL, alpha=0.68, edgecolor=NAVY, lw=1.8, zorder=4))
    right.scatter(feasible[:, 0], feasible[:, 1], s=16, c=NAVY, zorder=5)
    right.text(0.08, -0.02, r"$\Omega$", fontsize=17, color=NAVY, zorder=7)
    right.scatter([1.6], [1.7], marker="x", c=AMBER, s=65, lw=2)
    right.text(1.58, 1.9, "不可行交点", fontsize=8, color=AMBER)
    clean(right, (-2.35, 2.35), (-2.2, 2.35))
    right.set_xticks([])
    right.set_yticks([])
    right.set_title("多次示向：保留公共凸区域", color=NAVY, fontsize=11)
    save(fig, "problem1_wedge_intersection.pdf")


def p2_forward_lateral() -> None:
    fig = plt.figure(figsize=(11.4, 5.2))
    ax = fig.add_axes([0.07, 0.36, 0.67, 0.51])
    ax.set_xlim(-80, 1530)
    ax.set_ylim(-190, 190)
    ax.set_aspect("equal", adjustable="box")
    ax.axhline(0, color=NAVY, lw=1)
    x = np.linspace(0, 1500, 200)
    edge = x * math.tan(math.radians(1.0051))
    ax.fill_between(x, -edge, edge, color=TEAL, alpha=0.3, label="首次示向可行角域")
    ax.plot(x, edge, color=TEAL, ls="--", lw=1.2)
    ax.plot(x, -edge, color=TEAL, ls="--", lw=1.2)
    ax.axvline(1500, color=GRAY, ls=":")
    ax.fill_between([390, 525], [60, 60], [83, 83], color=AMBER, alpha=0.45)
    ax.fill_between([390, 525], [-83, -83], [-60, -60], color=AMBER, alpha=0.45)
    for px, py, marker in [(525, 60, "o"), (525, -60, "o"), (392.69, 82.76, "s"), (392.69, -82.76, "s")]:
        ax.scatter(px, py, c=AMBER, edgecolor=NAVY, marker=marker, s=35, zorder=6)
    ax.scatter(0, 0, c=NAVY, s=28, zorder=6)
    ax.text(10, -20, r"$S_1=(0,0)$", color=NAVY, fontsize=8)
    ax.text(1140, 60, r"$\pm1.0051^\circ$", color=TEAL, fontsize=9)
    ax.text(1450, 90, r"$d_+=1500$ m", fontsize=8, color=NAVY)
    ax.set_xlabel("沿首次示向距离 x / m")
    ax.set_ylabel("侧向偏移 y / m")
    ax.set_xticks([0, 400, 525, 1000, 1500])
    ax.set_yticks([-100, -60, 0, 60, 100])
    ax.grid(color="#e5edf2", lw=0.6)
    ax.set_title("双侧候选带（局部等比例视图）", color=NAVY, fontsize=11)

    inset = fig.add_axes([0.76, 0.4, 0.22, 0.43])
    inset.set_aspect("auto")
    inset.plot([0, 1000], [0, 0], color=NAVY)
    inset.plot([525, 1000], [60, 0], color=AMBER)
    inset.scatter([0, 525, 1000], [0, 60, 0], c=[NAVY, AMBER, NAVY], s=26)
    inset.text(-20, -28, r"$S_1$", fontsize=9)
    inset.text(505, 81, r"$S_2$", fontsize=9)
    inset.text(975, -27, r"$G$", fontsize=9)
    inset.text(650, 30, r"$\gamma>0$", fontsize=9, color=AMBER)
    inset.set_xlim(-70, 1060)
    inset.set_ylim(-100, 160)
    inset.axis("off")
    inset.set_title("事后交会示意（纵向放大）", fontsize=9, color=NAVY)
    overview = fig.add_axes([0.81, 0.06, 0.13, 0.22])
    overview.add_patch(Circle((0, 0), 1800, edgecolor=GRAY, facecolor="none", lw=1))
    overview.plot([0, 1500], [0, 0], color=TEAL, lw=2)
    overview.scatter([450], [0], c=AMBER, s=18, zorder=5)
    overview.set_xlim(-2000, 2000)
    overview.set_ylim(-2000, 2000)
    overview.set_aspect("equal", adjustable="box")
    overview.axis("off")
    overview.set_title("目标圆概览", fontsize=8, color=NAVY)
    fig.text(0.08, 0.24, r"候选参数：$\lambda\in[0.26,0.35],\ h\in[60,83]$ m", color=NAVY)
    fig.text(0.08, 0.18, r"问题三：$(525,\pm60)$ m    问题四：$(392.69,\pm82.76)$ m", color=NAVY)
    fig.text(0.08, 0.11, "目标圆半径 1800 m；本图为候选区局部放大，目标圆边界位于画幅外。", fontsize=9, color=GRAY)
    fig.text(0.75, 0.3, "G 仅用于事后说明交会角。", fontsize=8, color=GRAY)
    save(fig, "problem2_forward_lateral_region.pdf")


def p2_reception() -> None:
    fig, ax = plt.subplots(figsize=(10.3, 5.1))
    near, far, first, second = (500, 0), (1400, 0), (0, 0), (525, 60)
    ax.add_patch(Circle(near, 1000, edgecolor="#376cb1", facecolor=BLUE, alpha=0.12, lw=1.7, ls="--"))
    ax.add_patch(Circle(far, 1400, edgecolor="#108a82", facecolor=TEAL, alpha=0.10, lw=1.7))
    ax.axhline(0, color=GRAY, lw=0.9)
    for p, label, color, dy in [(first, r"$S_1=(0,0)$", NAVY, -210), (near, r"$G_{\rm near}=(500,0)$", "#376cb1", -340), (far, r"$G_{\rm far}=(1400,0)$", "#108a82", -210), (second, r"$S_2=(525,60)$", AMBER, 220)]:
        ax.scatter(*p, c=color, s=30, zorder=5)
        ax.text(p[0], p[1] + dy, label, color=color, ha="center", fontsize=9)
    ax.text(-430, 1110, r"$\rho(G_{\rm near})=1000$ m", color="#376cb1")
    ax.text(1600, 1320, r"$\rho(G_{\rm far})=1400$ m", color="#108a82")
    ax.text(1730, -950, "两个可能源位置的示意，\n不等于对连续可行域的保证。\n定向源还受发射朝向限制。", color=NAVY, fontsize=9,
            bbox={"facecolor": "white", "edgecolor": "#d8e4eb", "boxstyle": "round,pad=0.5"})
    clean(ax, (-650, 3000), (-1530, 1530))
    ax.set_xlabel("x / m")
    ax.set_ylabel("y / m")
    ax.set_title("首次阳性观测给出的最小相容接收半径", color=NAVY, fontsize=11)
    save(fig, "problem2_reception_condition.pdf")


def p3_coverage() -> None:
    fig, ax = plt.subplots(figsize=(7.7, 6.3))
    ring = np.array([(1200 * math.cos(math.radians(t)), 1200 * math.sin(math.radians(t))) for t in range(30, 390, 60)])
    anchors = np.vstack([[[0, 0]], ring])
    for i, p in enumerate(anchors):
        ax.add_patch(Circle(p, 1000, edgecolor=TEAL, facecolor=TEAL, alpha=0.09, lw=1.1, ls="--"))
        ax.add_patch(Circle(p, 1000, edgecolor=TEAL, facecolor="none", lw=0.9, ls="--", alpha=0.7))
        ax.scatter(*p, c=NAVY, s=25, zorder=6)
    ax.add_patch(Circle((0, 0), 1800, edgecolor=NAVY, facecolor="none", lw=1.8))
    ax.scatter(1800, 0, marker="*", c=AMBER, s=95, zorder=7)
    ax.annotate(r"$\max_{G\in\mathcal{T}}\min_{s\in\mathcal{S}_7}\|G-s\|\approx968.91\,{\rm m}$",
                xy=(1800, 0), xytext=(100, 1970), arrowprops={"arrowstyle": "->", "color": AMBER}, color=NAVY, fontsize=9)
    clean(ax, (-2150, 2150), (-2150, 2150))
    ax.set_xlabel("x / m")
    ax.set_ylabel("y / m")
    fig.text(0.08, 0.015, "实线：源分布圆 r=1800 m   虚线：最小接收圆 r=1000 m   圆点：计划扫描航点", fontsize=8, color=NAVY)
    ax.set_title("原点与半径 1200 m 六点环的发现覆盖", color=NAVY, fontsize=11)
    save(fig, "problem3_discovery_coverage.pdf")


if __name__ == "__main__":
    p1_wedge()
    p2_forward_lateral()
    p2_reception()
    p3_coverage()
