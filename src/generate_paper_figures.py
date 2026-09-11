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
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Wedge

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


def _draw_overview(path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(9.2, 3.15), constrained_layout=True)

    ax = axes[0]
    ax.add_patch(Wedge((0.0, 0.0), 2.3, -12, 12, color=SKY, alpha=0.35))
    ax.plot([0.0, 2.15], [0.0, 0.0], ls="--", lw=1.3, color=BLUE)
    ax.scatter([0.0], [0.0], marker="s", s=44, color=ORANGE, zorder=3)
    ax.scatter([1.65], [0.12], marker="*", s=90, color=VERMILION, zorder=4)
    ax.text(0.0, -0.28, r"$S_1$", ha="center")
    ax.text(1.65, 0.34, r"$G$", ha="center")
    ax.set_title("① 有界误差测向")
    ax.text(1.05, -0.78, r"$\theta_1\pm1^\circ$", ha="center", color=GRAY)

    ax = axes[1]
    ax.add_patch(Wedge((-1.6, -0.8), 3.2, 17, 35, color=SKY, alpha=0.28))
    ax.add_patch(Wedge((1.6, -0.9), 3.2, 137, 157, color=ORANGE, alpha=0.25))
    region = Polygon(
        [(0.02, -0.02), (0.26, 0.02), (0.34, 0.23), (0.11, 0.34), (-0.08, 0.17)],
        closed=True,
        facecolor=GREEN,
        edgecolor="#006B4F",
        alpha=0.75,
        lw=1.2,
    )
    ax.add_patch(region)
    ax.scatter([-1.6, 1.6], [-0.8, -0.9], marker="s", s=38, color=[BLUE, ORANGE])
    ax.plot([-0.08, 0.34], [0.17, 0.23], color=VERMILION, lw=2.0)
    ax.set_title("② 扇形交与区域直径")
    ax.text(0.13, 0.60, r"$D(\Omega)$", ha="center", color=VERMILION)

    ax = axes[2]
    safe = [
        (x, y)
        for x in (0.4, 0.8, 1.2, 1.6)
        for y in (-1.0, -0.5, 0.0, 0.5, 1.0)
        if (x - 0.7) ** 2 + (0.75 * y) ** 2 < 1.2
    ]
    ax.scatter(
        [p[0] for p in safe],
        [p[1] for p in safe],
        s=28,
        facecolor=SKY,
        edgecolor=BLUE,
        lw=0.6,
    )
    ax.scatter([0.0], [0.0], marker="s", s=44, color=ORANGE)
    ax.scatter([1.15], [0.78], marker="D", s=62, color=VERMILION, zorder=4)
    ax.annotate(
        "",
        xy=(1.10, 0.72),
        xytext=(0.08, 0.04),
        arrowprops={"arrowstyle": "->", "lw": 1.5, "color": GRAY},
    )
    ax.set_title("③ 鲁棒选择第二检测点")
    ax.text(1.15, 1.04, r"$S_2^\ast$", ha="center", color=VERMILION)

    for ax in axes:
        ax.set_aspect("equal")
        ax.set_xlim(-2.35, 2.35)
        ax.set_ylim(-1.35, 1.45)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

    _save(fig, path)


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
