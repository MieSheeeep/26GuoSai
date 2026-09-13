"""Render the Problem 1 geometry as a compact journal-style two-panel figure.

The geometry is recomputed from the same deterministic example as the paper,
so coordinates, vertex order, diameter and circle remain reproducible.
"""

from __future__ import annotations

from pathlib import Path
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle

from src.generate_paper_figures import _problem1_example


INK = "#263746"
BLUE = "#346C89"
PALE_BLUE = "#D8E9EE"
BOUND = "#83B5C4"
TEAL = "#198A78"
CORAL = "#C65F42"
AMBER = "#C49337"
GRID = "#E7ECEF"


def render(destination: Path) -> None:
    observations, source, result = _problem1_example()
    polygon = result["polygon"]
    xs, ys = zip(*polygon)
    diameter_start, diameter_end = result["diameter_endpoints"]
    circle_data = result["circle"]

    style = {
        "font.family": "sans-serif",
        "font.sans-serif": ["Noto Sans SC", "Microsoft YaHei", "DejaVu Sans"],
        "font.size": 8.4,
        "axes.labelsize": 8.5,
        "axes.titlesize": 9.2,
        "xtick.labelsize": 7.6,
        "ytick.labelsize": 7.6,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "axes.linewidth": 0.75,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 3.0,
        "ytick.major.size": 3.0,
        "svg.fonttype": "none",
        "savefig.facecolor": "white",
    }
    with plt.rc_context(style):
        fig, axes = plt.subplots(
            1, 2, figsize=(8.5, 3.75),
            gridspec_kw={"width_ratios": [1.13, 0.87], "wspace": 0.23},
        )
        fig.subplots_adjust(left=0.075, right=0.985, top=0.865, bottom=0.19)

        ax = axes[0]
        for index, (station, bearing, error) in enumerate(observations, start=1):
            distance = math.dist(station, source)
            for offset, linestyle, color, width, alpha in (
                (-error, (0, (1.6, 2.5)), BOUND, 0.85, 0.90),
                (error, (0, (1.6, 2.5)), BOUND, 0.85, 0.90),
                (0.0, (0, (5, 2.5)), BLUE, 1.25, 1.0),
            ):
                angle = math.radians(bearing + offset)
                endpoint = (
                    station[0] + 1.18 * distance * math.cos(angle),
                    station[1] + 1.18 * distance * math.sin(angle),
                )
                ax.plot(
                    [station[0], endpoint[0]], [station[1], endpoint[1]],
                    linestyle=linestyle, color=color, lw=width,
                    alpha=alpha, solid_capstyle="round", zorder=1,
                )
            ax.scatter(*station, marker="s", s=28, facecolor=AMBER,
                       edgecolor="white", linewidth=0.6, zorder=4)
            offsets = {1: (5, 7), 2: (5, 5), 3: (5, 5)}
            ax.annotate(rf"$S_{{{index}}}$", station, xytext=offsets[index],
                        textcoords="offset points", fontsize=8.5)

        ax.add_patch(Rectangle((267, 375), 68, 77, fill=False,
                               edgecolor=TEAL, linewidth=0.85,
                               linestyle=(0, (3, 2)), zorder=2))
        ax.scatter(*source, marker="*", s=85, facecolor=CORAL,
                   edgecolor="white", linewidth=0.65, zorder=5)
        ax.annotate("$G$", source, xytext=(6, -15),
                    textcoords="offset points", fontsize=8.5)
        ax.set_xlim(-570, 980)
        ax.set_ylim(-265, 1060)
        ax.set_xticks([-400, 0, 400, 800])
        ax.set_yticks([-200, 200, 600, 1000])
        ax.set_aspect("equal", adjustable="box")
        ax.set_title("三站有界测向交会", loc="left", pad=14, fontweight="medium")

        ax = axes[1]
        ax.add_patch(Polygon(polygon, closed=True, facecolor=PALE_BLUE,
                             edgecolor=BLUE, linewidth=1.35, zorder=2))
        ax.add_patch(Circle(circle_data["center"], circle_data["radius"],
                            fill=False, edgecolor=TEAL, linewidth=1.4,
                            linestyle=(0, (5, 2.6)), zorder=1))
        ax.plot([diameter_start[0], diameter_end[0]],
                [diameter_start[1], diameter_end[1]],
                color=CORAL, lw=2.0, solid_capstyle="round", zorder=3)
        ax.scatter(xs, ys, s=19, color=BLUE, edgecolor="white",
                   linewidth=0.5, zorder=4)
        label_offsets = [(4, 4), (4, 2), (4, 2), (4, 4), (4, 3), (-12, 6)]
        for index, (point, offset) in enumerate(zip(polygon, label_offsets), 1):
            ax.annotate(rf"$V_{{{index}}}$", point, xytext=offset,
                        textcoords="offset points", fontsize=7.8)
        ax.scatter(*source, marker="*", s=70, facecolor=CORAL,
                   edgecolor="white", linewidth=0.6, zorder=5)
        ax.scatter(*circle_data["center"], marker="+", s=43,
                   linewidth=1.25, color=TEAL, zorder=5)
        ax.set_xlim(min(xs) - 7, max(xs) + 7)
        ax.set_ylim(min(ys) - 7, max(ys) + 7)
        ax.set_xticks([280, 290, 300, 310, 320])
        ax.set_yticks([390, 400, 410, 420, 430, 440])
        ax.set_aspect("equal", adjustable="box")
        ax.set_title("定位区域与直径圆", loc="left", pad=14, fontweight="medium")
        ax.grid(color=GRID, lw=0.55, zorder=0)

        for letter, panel in zip("ab", axes):
            panel.text(-0.04, 1.20, letter, transform=panel.transAxes,
                       ha="left", va="bottom", fontsize=11, fontweight="bold")
            panel.set_xlabel("x (m)", labelpad=5)
            panel.set_ylabel("y (m)", labelpad=5)

        axes[1].text(0.01, -0.27, rf"直径 $D = {result['diameter']:.4f}$ m",
                     transform=axes[1].transAxes, color=CORAL,
                     fontsize=8.3, ha="left", va="top")
        axes[1].text(0.99, -0.27, "虚线：直径圆", transform=axes[1].transAxes,
                     color=TEAL, fontsize=8.3, ha="right", va="top")

        destination.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(destination, dpi=600)
        fig.savefig(destination.with_suffix(".svg"))
        plt.close(fig)


if __name__ == "__main__":
    render(Path(__file__).resolve().parents[1] / "latex" / "figures" /
           "problem1_region_nature.png")
