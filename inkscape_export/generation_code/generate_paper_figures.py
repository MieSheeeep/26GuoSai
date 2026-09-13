"""Generate reproducible vector figures for Problems 1 and 2.

The figures are derived from the same deterministic examples used in
problem1.py and problem2.py. Run this module from the repository root to
refresh the PDF assets under latex/figures.
"""

from __future__ import annotations

from pathlib import Path
import math
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon

from src.problem1 import solve
from src.problem2 import (
    reception_margin,
    sample_source_region,
    select_second_detection_points,
)

Point = tuple[float, float]

BLUE = "#0072B2"
SKY = "#56B4E9"
ORANGE = "#E69F00"
GREEN = "#009E73"
VERMILION = "#D55E00"
GRAY = "#666666"


def _configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Noto Sans SC", "Microsoft YaHei", "SimHei"],
            "axes.unicode_minus": False,
            "font.size": 9,
            "axes.labelsize": 9,
            "axes.titlesize": 10,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "figure.dpi": 140,
            "savefig.dpi": 600,
            "pdf.fonttype": 42,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def _problem1_example() -> tuple[list[tuple[Point, float, float]], Point, dict[str, Any]]:
    source = (300.0, 400.0)
    stations = [(-500.0, -200.0), (900.0, -100.0), (0.0, 1000.0)]
    offsets = [0.6, -0.8, 0.4]
    observations: list[tuple[Point, float, float]] = []
    for station, offset in zip(stations, offsets, strict=True):
        bearing = math.degrees(
            math.atan2(source[1] - station[1], source[0] - station[0])
        ) % 360.0
        observations.append((station, bearing + offset, 1.0))
    return observations, source, solve(observations)


def _p2_safe_candidates(step: float = 100.0) -> tuple[list[Point], list[Point]]:
    first = (0.0, 0.0)
    sources, _ = sample_source_region(
        first,
        0.0,
        error_deg=1.0,
        angle_samples=9,
        radial_samples=31,
    )
    candidates: list[Point] = []
    limit = math.floor(1800.0 / step)
    for ix in range(-limit, limit + 1):
        for iy in range(-limit, limit + 1):
            point = (ix * step, iy * step)
            if math.hypot(*point) > 1800.0 + 1e-9:
                continue
            if math.hypot(point[0] - first[0], point[1] - first[1]) < 100.0:
                continue
            if reception_margin(first, point, sources, 1000.0) >= -1e-9:
                candidates.append(point)
    return sources, candidates


def _save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(
        path,
        format="pdf",
        bbox_inches="tight",
        facecolor="white",
        metadata={
            "Title": path.stem,
            "Author": "26GuoSai reproducible figure generator",
        },
    )
    plt.close(fig)


def _draw_workflow(
    path: Path,
    stages: list[tuple[str, str, str]],
    colors: list[str],
) -> None:
    """Draw a compact left-to-right workflow shared by both problem chapters."""

    fig, ax = plt.subplots(figsize=(9.2, 2.15), constrained_layout=True)
    box_width = 1.62
    box_height = 1.26
    gap = 0.36
    y0 = 0.18

    for index, ((title, subtitle, symbol), color) in enumerate(
        zip(stages, colors, strict=True)
    ):
        x0 = index * (box_width + gap)
        box = FancyBboxPatch(
            (x0, y0),
            box_width,
            box_height,
            boxstyle="round,pad=0.04,rounding_size=0.08",
            facecolor=color,
            edgecolor=color,
            alpha=0.16,
            linewidth=1.4,
        )
        ax.add_patch(box)
        ax.text(
            x0 + 0.13,
            y0 + box_height - 0.18,
            f"步骤 {index + 1}",
            color=color,
            fontsize=7.5,
            fontweight="bold",
            va="top",
        )
        ax.text(
            x0 + box_width / 2,
            y0 + 0.78,
            title,
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
        )
        ax.text(
            x0 + box_width / 2,
            y0 + 0.48,
            symbol,
            ha="center",
            va="center",
            fontsize=10,
            color=color,
        )
        ax.text(
            x0 + box_width / 2,
            y0 + 0.18,
            subtitle,
            ha="center",
            va="bottom",
            fontsize=7.6,
            color=GRAY,
        )
        if index < len(stages) - 1:
            arrow = FancyArrowPatch(
                (x0 + box_width + 0.04, y0 + box_height / 2),
                (x0 + box_width + gap - 0.04, y0 + box_height / 2),
                arrowstyle="-|>",
                mutation_scale=12,
                linewidth=1.25,
                color=GRAY,
            )
            ax.add_patch(arrow)

    total_width = len(stages) * box_width + (len(stages) - 1) * gap
    ax.set_xlim(-0.08, total_width + 0.08)
    ax.set_ylim(0.05, 1.58)
    ax.axis("off")
    _save(fig, path)


def _draw_overview(path: Path) -> None:
    stages = [
        ("有界测向", "示向度 ±1°", r"$\theta_i\pm\varepsilon$"),
        ("线性化约束", "一次观测对应两个半平面", r"$H_{2i-1}\cap H_{2i}$"),
        ("定位区域", "半平面交形成凸多边形", r"$\Omega=\cap_i W_i$"),
        ("区域直径", "旋转卡壳确定最远点对", r"$D(\Omega)$"),
        ("覆盖判定", "逐顶点检验直径圆", r"$\|v_i-C\|\leq r$"),
    ]
    _draw_workflow(path, stages, [BLUE, SKY, GREEN, ORANGE, VERMILION])


def _draw_problem2_workflow(path: Path) -> None:
    """Draw the five-stage robust second-point selection workflow."""

    stages = [
        ("首次不确定域", "角度与距离联合采样", r"$\Omega_1$"),
        ("保证接收区", "先用硬约束筛选候选点", r"$\mathcal{C}_{\mathrm{safe}}$"),
        ("交会质量", "评价最坏定位几何", r"$\gamma_{\min},\ E_{\max}$"),
        ("代价折中", "综合接收裕量与移动距离", r"$M,\ L,\ J$"),
        ("双侧推荐", "保留示向线两侧最优点", r"$S_2^{(+)},\ S_2^{(-)}$"),
    ]
    _draw_workflow(path, stages, [SKY, GREEN, BLUE, ORANGE, VERMILION])


def _draw_problem1(
    path: Path,
    observations: list[tuple[Point, float, float]],
    source: Point,
    result: dict[str, Any],
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.15), constrained_layout=True)
    polygon = result["polygon"]
    endpoints = result["diameter_endpoints"]
    circle_data = result["circle"]

    ax = axes[0]
    for index, (station, bearing, error) in enumerate(observations, start=1):
        distance = math.hypot(source[0] - station[0], source[1] - station[1])
        for offset, style, alpha in (
            (0.0, "--", 0.95),
            (-error, ":", 0.55),
            (error, ":", 0.55),
        ):
            angle = math.radians(bearing + offset)
            end = (
                station[0] + 1.18 * distance * math.cos(angle),
                station[1] + 1.18 * distance * math.sin(angle),
            )
            ax.plot(
                [station[0], end[0]],
                [station[1], end[1]],
                ls=style,
                lw=1.15 if offset == 0.0 else 0.8,
                color=BLUE,
                alpha=alpha,
            )
        ax.scatter(*station, marker="s", s=45, color=ORANGE, zorder=4)
        ax.annotate(
            rf"$S_{index}$",
            station,
            xytext=(5, 6),
            textcoords="offset points",
        )
    ax.add_patch(
        Polygon(polygon, closed=True, facecolor=SKY, edgecolor=BLUE, alpha=0.7)
    )
    ax.scatter(
        *source,
        marker="*",
        s=100,
        color=VERMILION,
        edgecolor="black",
        lw=0.5,
        zorder=5,
    )
    ax.annotate(r"$G$", source, xytext=(5, -13), textcoords="offset points")
    ax.set_title("(a) 三站有界测向交会")
    ax.set_xlabel("$x$/m")
    ax.set_ylabel("$y$/m")
    ax.grid(alpha=0.18, lw=0.5)
    ax.set_aspect("equal")

    ax = axes[1]
    ax.add_patch(
        Polygon(
            polygon,
            closed=True,
            facecolor=SKY,
            edgecolor=BLUE,
            alpha=0.65,
            lw=1.4,
        )
    )
    xs = [point[0] for point in polygon]
    ys = [point[1] for point in polygon]
    ax.scatter(xs, ys, s=24, color=BLUE, zorder=4)
    for index, point in enumerate(polygon, start=1):
        ax.annotate(
            rf"$V_{index}$",
            point,
            xytext=(3, 4),
            textcoords="offset points",
            fontsize=7,
        )
    first, second = endpoints
    ax.plot(
        [first[0], second[0]],
        [first[1], second[1]],
        color=VERMILION,
        lw=2.2,
        label=f"直径 = {result['diameter']:.4f} m",
    )
    ax.add_patch(
        Circle(
            circle_data["center"],
            circle_data["radius"],
            fill=False,
            edgecolor=GREEN,
            ls="--",
            lw=1.6,
            label="直径圆",
        )
    )
    ax.scatter(
        *source,
        marker="*",
        s=100,
        color=VERMILION,
        edgecolor="black",
        lw=0.5,
        zorder=5,
    )
    ax.scatter(*circle_data["center"], marker="+", s=55, color=GREEN, zorder=5)
    ax.set_title("(b) 定位区域、直径端点与直径圆")
    ax.set_xlabel("$x$/m")
    ax.set_ylabel("$y$/m")
    ax.grid(alpha=0.18, lw=0.5)
    ax.set_aspect("equal")
    ax.legend(frameon=False, loc="lower right")
    pad = 7.0
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    _save(fig, path)


def _draw_problem2(
    path: Path,
    sources: list[Point],
    candidates: list[Point],
    result: dict[str, Any],
    sensitivity: list[dict[str, float]],
) -> None:
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(9.2, 4.15),
        gridspec_kw={"width_ratios": [1.18, 0.82]},
        constrained_layout=True,
    )
    ax = axes[0]
    ax.add_patch(Circle((0.0, 0.0), 1800.0, fill=False, color="#BBBBBB", lw=1.0))
    ax.scatter(
        [p[0] for p in sources],
        [p[1] for p in sources],
        s=8,
        color=ORANGE,
        alpha=0.60,
        label=r"首次可行域样本 $\Omega_1$",
        rasterized=True,
    )
    ax.scatter(
        [p[0] for p in candidates],
        [p[1] for p in candidates],
        s=17,
        facecolor=SKY,
        edgecolor=BLUE,
        lw=0.45,
        alpha=0.86,
        label=r"保证接收候选 $\mathcal{C}_{\mathrm{safe}}$",
    )
    ax.scatter([0.0], [0.0], marker="s", s=48, color="#222222", label=r"$S_1$")
    ax.plot(
        [0.0, 1550.0],
        [0.0, 0.0],
        ls="--",
        lw=1.2,
        color=GRAY,
        label="中心示向线",
    )
    for item in result["recommended_points"]:
        x, y = item["point"]
        ax.scatter(
            x,
            y,
            marker="D",
            s=65,
            color=VERMILION,
            edgecolor="white",
            lw=0.6,
            zorder=5,
        )
        ax.annotate(
            rf"$S_2^\ast=({x:.0f},{y:.0f})$",
            (x, y),
            xytext=(6, 7 if y > 0 else -15),
            textcoords="offset points",
            color=VERMILION,
            fontsize=8,
        )
        ax.annotate(
            "",
            xy=(x, y),
            xytext=(0.0, 0.0),
            arrowprops={
                "arrowstyle": "->",
                "lw": 1.0,
                "color": VERMILION,
                "alpha": 0.7,
            },
        )
    ax.set_xlim(-150.0, 1650.0)
    ax.set_ylim(-1050.0, 1050.0)
    ax.set_aspect("equal")
    ax.set_xlabel("$x$/m")
    ax.set_ylabel("$y$/m")
    ax.set_title("(a) 保证接收候选区域与推荐点")
    ax.grid(alpha=0.18, lw=0.5)
    ax.legend(frameon=False, loc="upper right")

    ax = axes[1]
    labels = [f"{int(item['step'])}" for item in sensitivity]
    positions = list(range(len(labels)))
    errors = [item["error"] for item in sensitivity]
    scores = [item["score"] for item in sensitivity]
    line1 = ax.plot(
        positions,
        errors,
        marker="o",
        color=BLUE,
        lw=1.8,
        ms=5,
        label="最坏误差代理/m",
    )
    ax.set_xticks(positions, labels)
    ax.set_xlabel("候选网格步长/m")
    ax.set_ylabel("最坏定位误差代理/m", color=BLUE)
    ax.tick_params(axis="y", labelcolor=BLUE)
    ax.grid(axis="y", alpha=0.18, lw=0.5)
    ax2 = ax.twinx()
    line2 = ax2.plot(
        positions,
        scores,
        marker="s",
        color=ORANGE,
        lw=1.8,
        ms=5,
        label="综合评分",
    )
    ax2.set_ylabel("综合评分", color=ORANGE)
    ax2.tick_params(axis="y", labelcolor=ORANGE)
    ax2.spines["right"].set_visible(True)
    ax.set_title("(b) 网格细化敏感性")
    ax.legend(
        line1 + line2,
        [item.get_label() for item in line1 + line2],
        frameon=False,
        loc="best",
    )
    for x, error in zip(positions, errors, strict=True):
        ax.annotate(
            f"{error:.2f}",
            (x, error),
            xytext=(0, 6),
            textcoords="offset points",
            ha="center",
            color=BLUE,
            fontsize=7,
        )
    _save(fig, path)


def generate_all(output_dir: str | Path) -> dict[str, Any]:
    """Generate all paper figures and return the underlying example metrics."""

    _configure_style()
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    observations, source, p1_result = _problem1_example()
    p2_result = select_second_detection_points(
        first_point=(0.0, 0.0),
        bearing_deg=0.0,
        grid_step=100.0,
        angle_samples=9,
        radial_samples=31,
    )
    sources, candidates = _p2_safe_candidates(100.0)

    sensitivity: list[dict[str, float]] = []
    for step in (200.0, 100.0, 50.0):
        item = select_second_detection_points(
            first_point=(0.0, 0.0),
            bearing_deg=0.0,
            grid_step=step,
            angle_samples=9,
            radial_samples=31,
        )["recommended_points"][0]
        sensitivity.append(
            {
                "step": step,
                "error": float(item["worst_positioning_error"]),
                "score": float(item["score"]),
            }
        )

    _draw_overview(destination / "problem12_overview.pdf")
    _draw_problem2_workflow(destination / "problem2_workflow.pdf")
    _draw_problem1(
        destination / "problem1_region.pdf",
        observations,
        source,
        p1_result,
    )
    _draw_problem2(
        destination / "problem2_candidate_region.pdf",
        sources,
        candidates,
        p2_result,
        sensitivity,
    )
    return {
        "problem1": p1_result,
        "problem2": p2_result,
        "sensitivity": sensitivity,
    }


def main() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    generate_all(repository_root / "latex" / "figures")


if __name__ == "__main__":
    main()
