#!/usr/bin/env python3
"""Q4-only validation and publication figures.

The experiment reuses the submitted standalone controller and the independent
simulator in ``run_q34_validation.py``.  Policy code never receives latent
source coordinates.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import multiprocessing as mp
from pathlib import Path
import time

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrowPatch, Patch, Wedge
import numpy as np
from shapely.geometry import Point, Polygon

from run_q34_validation import (
    Q4_PATH,
    ROOT,
    OfflineClient,
    controller_module,
    generate_sources,
    wilson_interval,
)


SCENARIOS = (
    ("q4_mixed", "混合源随机朝向", "混合源"),
    ("q4_directional", "全定向源随机朝向", "全定向随机"),
    ("q4_outward", "全定向源径向外射", "全定向外射"),
)
Q4_SEED_GROUP_OFFSET = 3


def setup_style():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [
            "Arial Unicode MS", "Hiragino Sans GB", "Microsoft YaHei",
            "SimHei", "Songti SC", "SimSun",
        ],
        "font.size": 8.2,
        "axes.labelsize": 8.2,
        "xtick.labelsize": 7.4,
        "ytick.labelsize": 7.4,
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
    })


def survey_stations():
    outer_angles = np.arange(18) * 2 * np.pi / 18
    inner_angles = np.deg2rad(10) + np.arange(12) * 2 * np.pi / 12
    center = np.zeros((1, 2))
    outer = 1850 * np.column_stack((
        np.cos(outer_angles), np.sin(outer_angles)))
    inner = 925 * np.column_stack((
        np.cos(inner_angles), np.sin(inner_angles)))
    return center, outer, inner


def run_one(task):
    scenario, run_index, seed = task
    sources = generate_sources(scenario, seed, source_count=16)
    client = OfflineClient(sources, seed)
    started = time.perf_counter()
    try:
        module = controller_module(4)
        policy = module.PlannedNegativeTour(client, module.Q4_CONFIG)
        result = policy.run()
        error = ""
    except Exception as exc:
        result = {}
        error = f"{type(exc).__name__}: {exc}"
    cleared = sum(source.cleared for source in sources)
    return {
        "scenario": scenario,
        "run_index": run_index,
        "seed": seed,
        "cleared": cleared,
        "total": len(sources),
        "complete": int(cleared == len(sources) and not error),
        "virtual_time_s": client.time,
        "actions": client.calls,
        "survey_stops": result.get("survey_stops", ""),
        "optical_fallbacks": result.get("optical_fallbacks", ""),
        "runtime_s": time.perf_counter() - started,
        "error": error,
    }


def summarize(rows):
    labels = {key: label for key, label, _ in SCENARIOS}
    result = []
    for key, _, _ in SCENARIOS:
        group = [row for row in rows if row["scenario"] == key]
        complete = sum(int(row["complete"]) for row in group)
        completed_group = [row for row in group if int(row["complete"])]
        times = np.array([
            float(row["virtual_time_s"]) for row in completed_group])
        actions = np.array([
            float(row["actions"]) for row in completed_group])
        low, high = wilson_interval(complete, len(group))
        result.append({
            "scenario": key,
            "label_zh": labels[key],
            "samples": len(group),
            "complete_samples": complete,
            "complete_rate": complete / len(group),
            "wilson_95_low": low,
            "wilson_95_high": high,
            "mean_time_s": float(times.mean()),
            "sd_time_s": float(times.std(ddof=1)),
            "p95_time_s": float(np.quantile(times, 0.95)),
            "max_time_s": float(times.max()),
            "mean_actions": float(actions.mean()),
            "max_actions": int(actions.max()),
        })
    completed_rows = [row for row in rows if int(row["complete"])]
    all_times = np.array([
        float(row["virtual_time_s"]) for row in completed_rows])
    complete = sum(int(row["complete"]) for row in rows)
    low, high = wilson_interval(complete, len(rows))
    result.append({
        "scenario": "overall",
        "label_zh": "总体",
        "samples": len(rows),
        "complete_samples": complete,
        "complete_rate": complete / len(rows),
        "wilson_95_low": low,
        "wilson_95_high": high,
        "mean_time_s": float(all_times.mean()),
        "sd_time_s": float(all_times.std(ddof=1)),
        "p95_time_s": float(np.quantile(all_times, 0.95)),
        "max_time_s": float(all_times.max()),
        "mean_actions": float(np.mean([
            float(row["actions"]) for row in completed_rows])),
        "max_actions": int(max(
            float(row["actions"]) for row in completed_rows)),
    })
    return result


def plot_shape(ax, shape, scale=1.0, **kwargs):
    parts = list(shape.geoms) if hasattr(shape, "geoms") else [shape]
    for part in parts:
        if part.is_empty or part.geom_type != "Polygon":
            continue
        x, y = part.exterior.xy
        ax.fill(np.asarray(x) / scale, np.asarray(y) / scale, **kwargs)


def method_figure(output_dir):
    """Three geometric panels with all semantics carried by the legend."""
    blue = "#0072B2"
    sky = "#56B4E9"
    green = "#009E73"
    orange = "#E69F00"
    vermilion = "#D55E00"
    purple = "#CC79A7"
    dark = "#252525"
    grey = "#8B9299"

    fig, axes = plt.subplots(1, 3, figsize=(10.0, 3.55))
    fig.subplots_adjust(left=0.025, right=0.985, top=0.93,
                        bottom=0.31, wspace=0.12)

    # (a) A directional source is visible only in its forward half-disc.
    ax = axes[0]
    ax.add_patch(Wedge(
        (0, 0), 1.38, -90, 90, facecolor=sky,
        edgecolor="none", alpha=0.23, zorder=1))
    ax.add_patch(Circle(
        (0, 0), 1.38, facecolor="none", edgecolor=grey,
        linewidth=0.8, linestyle=(0, (3, 2)), zorder=2))
    ax.add_patch(FancyArrowPatch(
        (-0.08, 0), (0.82, 0), arrowstyle="-|>",
        mutation_scale=10, color=vermilion, linewidth=1.5, zorder=4))
    ax.scatter(0, 0, marker="D", s=34, facecolor=vermilion,
               edgecolor="white", linewidth=0.5, zorder=5)
    positive = np.array([[0.88, 0.58], [1.05, -0.42]])
    negative = np.array([[-0.76, 0.62], [-0.92, -0.38], [1.58, 0.26]])
    ax.scatter(positive[:, 0], positive[:, 1], marker="o", s=35,
               facecolor=blue, edgecolor="white", linewidth=0.55, zorder=5)
    ax.scatter(negative[:, 0], negative[:, 1], marker="x", s=38,
               color=orange, linewidth=1.4, zorder=5)
    ax.set_xlim(-1.82, 1.82)
    ax.set_ylim(-1.82, 1.82)

    # (b) The fixed center/inner/outer layout covers every source orientation.
    ax = axes[1]
    module = controller_module(4)
    center, outer, inner = survey_stations()
    stations = np.vstack((center, outer, inner))
    region = module.local_hull_region(tuple(map(tuple, stations)))
    ax.add_patch(Circle(
        (0, 0), 1.8, facecolor="#FAFBFC", edgecolor=dark,
        linewidth=0.95, zorder=0))
    plot_shape(
        ax, region.intersection(module.ARENA), scale=1000.0,
        color=green, alpha=0.16, edgecolor="none", zorder=1)
    ax.scatter(outer[:, 0] / 1000, outer[:, 1] / 1000, marker="o", s=20,
               facecolor=blue, edgecolor="white", linewidth=0.4, zorder=4)
    ax.scatter(inner[:, 0] / 1000, inner[:, 1] / 1000, marker="s", s=19,
               facecolor=orange, edgecolor="white", linewidth=0.4, zorder=4)
    ax.scatter(0, 0, marker="D", s=28, facecolor=dark,
               edgecolor="white", linewidth=0.45, zorder=5)
    ax.set_xlim(-2.02, 2.02)
    ax.set_ylim(-2.02, 2.02)

    # (c) Multiple negative observations remove only a common exclusion set.
    ax = axes[2]
    prior = Polygon([
        (-1.35, -0.52), (-0.62, -1.10), (0.72, -1.02),
        (1.36, -0.34), (1.12, 0.72), (0.16, 1.12),
        (-1.15, 0.72),
    ])
    negatives = np.array([
        [-0.88, -0.72], [-0.70, 0.78], [0.88, 0.62],
    ])
    excluded = Polygon(negatives).buffer(0.05)
    posterior = prior.difference(excluded)
    ax.add_patch(Circle(
        (0, 0), 1.72, facecolor="#FAFBFC", edgecolor=grey,
        linewidth=0.85, zorder=0))
    plot_shape(
        ax, prior, color=purple, alpha=0.10, edgecolor=purple,
        linewidth=0.9, linestyle=(0, (3, 2)), zorder=1)
    plot_shape(
        ax, posterior, color=purple, alpha=0.72,
        edgecolor=purple, linewidth=0.75, zorder=2)
    plot_shape(
        ax, excluded.intersection(prior), color=orange, alpha=0.30,
        edgecolor=orange, linewidth=0.8, zorder=3)
    ax.scatter(negatives[:, 0], negatives[:, 1], marker="x", s=38,
               color=orange, linewidth=1.4, zorder=5)
    candidates = np.array([[1.24, 0.93], [1.35, -0.82]])
    ax.scatter(candidates[:, 0], candidates[:, 1], marker="o", s=32,
               facecolor=green, edgecolor="white", linewidth=0.5, zorder=5)
    current = np.array([-1.48, 0.05])
    ax.scatter(*current, marker=">", s=54, facecolor=dark,
               edgecolor="white", linewidth=0.5, zorder=6)
    ax.add_patch(FancyArrowPatch(
        current, candidates[1], arrowstyle="-|>", mutation_scale=8,
        color=dark, linewidth=1.0, linestyle=(0, (3, 2)),
        shrinkA=6, shrinkB=6, zorder=4))
    ax.set_xlim(-1.82, 1.82)
    ax.set_ylim(-1.82, 1.82)

    for label, axis in zip("abc", axes):
        axis.set_aspect("equal")
        axis.axis("off")
        axis.text(
            0.01, 0.99, label, transform=axis.transAxes,
            fontsize=11.0, fontweight="bold", va="top", color=dark)

    legend_kw = dict(loc="upper center", frameon=False, fontsize=7.7,
                     columnspacing=1.0, handletextpad=0.35)
    axes[0].legend(handles=[
        Line2D([0], [0], marker="D", color=vermilion,
               markerfacecolor=vermilion, markersize=5.5,
               linewidth=1.2, label="定向源及发射方向"),
        Patch(facecolor=sky, edgecolor="none", alpha=0.35,
              label="有效辐射区域"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=blue,
               markersize=5.5, label="有信号观测"),
        Line2D([0], [0], marker="x", color=orange, markersize=5.5,
               linewidth=0, label="无信号观测"),
    ], bbox_to_anchor=(0.5, -0.08), ncol=2, **legend_kw)
    axes[1].legend(handles=[
        Line2D([0], [0], marker="o", color="none", markerfacecolor=blue,
               markersize=5.5, label="外环巡检"),
        Line2D([0], [0], marker="s", color="none",
               markerfacecolor=orange, markersize=5.5, label="内环巡检"),
        Line2D([0], [0], marker="D", color="none", markerfacecolor=dark,
               markersize=5.5, label="中心巡检"),
        Patch(facecolor=green, edgecolor=green, alpha=0.25,
              label="多方位覆盖区域"),
    ], bbox_to_anchor=(0.5, -0.08), ncol=2, **legend_kw)
    axes[2].legend(handles=[
        Patch(facecolor=orange, edgecolor=orange, alpha=0.30,
              label="多点排除区域"),
        Patch(facecolor=purple, edgecolor=purple, alpha=0.72,
              label="位置可行集"),
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor=green, markersize=5.5, label="异方位复测"),
    ], bbox_to_anchor=(0.5, -0.08), ncol=1, **legend_kw)
    fig.savefig(output_dir / "q4_method_overview.pdf", bbox_inches="tight")
    fig.savefig(
        output_dir / "q4_method_overview.png", dpi=300,
        bbox_inches="tight")
    plt.close(fig)


def validation_figure(rows, output_dir, seed):
    """Outward-radiation geometry and Q4-only time distributions."""
    blue = "#0072B2"
    green = "#009E73"
    orange = "#E69F00"
    vermilion = "#D55E00"
    dark = "#252525"
    grey = "#8B9299"
    colors = (blue, orange, green)

    # Single-panel geometry view with a real recorded HTTP trajectory.
    sources = generate_sources("q4_outward", seed, source_count=16)
    fig, ax = plt.subplots(figsize=(7.0, 6.0))
    ax.add_patch(Circle((0, 0), 1800, facecolor="#FAFBFC",
                        edgecolor=dark, linewidth=0.9, zorder=0))
    for source in sources:
        direction = np.array([math.cos(source.heading), math.sin(source.heading)])
        ax.add_patch(Wedge(tuple(source.position), source.reception_radius,
                           math.degrees(source.heading) - 90,
                           math.degrees(source.heading) + 90,
                           facecolor=vermilion, edgecolor="none", alpha=0.12, zorder=2))
        ax.add_patch(FancyArrowPatch(
            source.position, source.position + 145 * direction,
            arrowstyle="-|>", mutation_scale=6.5, color=vermilion,
            linewidth=0.8, zorder=4))
        ax.scatter(*source.position, marker="o", s=13,
                   facecolor=vermilion, edgecolor="white", linewidth=0.35, zorder=5)
    log_path = ROOT / "26GuoSai" / "q3_refinement" / "q3_example_log.json"
    if log_path.exists():
        log = json.loads(log_path.read_text(encoding="utf-8"))
        trajectory = np.array([a["position"] for a in log["actions"]], dtype=float)
        ax.plot(trajectory[:, 0], trajectory[:, 1], color="#3B4A5A",
                linewidth=1.2, alpha=0.88, zorder=6)
        ax.scatter(*trajectory[0], marker="o", s=30, color="#3B4A5A",
                    edgecolor="white", linewidth=0.5, zorder=7)
        ax.scatter(*trajectory[-1], marker="*", s=65, color="#3B4A5A",
                    edgecolor="white", linewidth=0.5, zorder=7)
    ax.set_aspect("equal")
    ax.set_xlim(-2030, 2030)
    ax.set_ylim(-2030, 2030)
    ax.set_xlabel("x/m")
    ax.set_ylabel("y/m")
    ax.text(0.01, 0.99, "a", transform=ax.transAxes, fontsize=11,
            fontweight="bold", va="top", color=dark)
    ax.legend(handles=[
        Patch(facecolor=vermilion, edgecolor="none", alpha=0.28,
              label="定向源前向可检测范围"),
        Line2D([0], [0], color="#3B4A5A", linewidth=1.2,
               label="真实HTTP日志轨迹"),
        Line2D([0], [0], marker="o", color=vermilion,
               markerfacecolor=vermilion, markersize=4.8,
               linewidth=1.0, label="径向外射源"),
    ], loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2,
       frameon=False, fontsize=8.0, columnspacing=1.1)
    fig.subplots_adjust(left=0.10, right=0.98, top=0.96, bottom=0.20)
    fig.savefig(output_dir / "q4_validation_overview.pdf", bbox_inches="tight")
    fig.savefig(output_dir / "q4_validation_overview.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    return

    sources = generate_sources("q4_outward", seed, source_count=16)
    center, outer, inner = survey_stations()
    stations = np.vstack((center, outer, inner))

    fig = plt.figure(figsize=(10.0, 4.15))
    grid = fig.add_gridspec(
        1, 2, width_ratios=(1.0, 1.24), left=0.035, right=0.98,
        top=0.94, bottom=0.28, wspace=0.19)
    ax = fig.add_subplot(grid[0, 0])
    bx = fig.add_subplot(grid[0, 1])

    ax.add_patch(Circle(
        (0, 0), 1800, facecolor="#FAFBFC", edgecolor=dark,
        linewidth=0.9, zorder=0))
    ax.scatter(outer[:, 0], outer[:, 1], marker="o", s=18,
               facecolor=blue, edgecolor="white", linewidth=0.4, zorder=5)
    ax.scatter(inner[:, 0], inner[:, 1], marker="s", s=17,
               facecolor=orange, edgecolor="white", linewidth=0.4, zorder=5)
    ax.scatter(0, 0, marker="D", s=24, facecolor=dark,
               edgecolor="white", linewidth=0.4, zorder=5)
    detected = 0
    for source in sources:
        direction = np.array([
            math.cos(source.heading), math.sin(source.heading)])
        # Only show the directional source's forward detectable range.
        heading_deg = math.degrees(source.heading)
        ax.add_patch(Wedge(
            tuple(source.position), source.reception_radius,
            heading_deg - 90.0, heading_deg + 90.0,
            facecolor=vermilion, edgecolor="none", alpha=0.12, zorder=2))
        valid = []
        for station in stations:
            distance = float(np.linalg.norm(station - source.position))
            if (distance <= source.reception_radius
                    and float((station - source.position) @ direction)
                    >= -1e-10):
                valid.append((distance, station))
        if valid:
            detected += 1
            _, station = min(valid, key=lambda item: item[0])
            ax.plot(
                [source.position[0], station[0]],
                [source.position[1], station[1]],
                color=grey, linewidth=0.5, alpha=0.6, zorder=1)
        start = source.position
        end = start + 145 * direction
        ax.add_patch(FancyArrowPatch(
            start, end, arrowstyle="-|>", mutation_scale=6.5,
            color=vermilion, linewidth=0.8, zorder=4))
        ax.scatter(*start, marker="o", s=13, facecolor=vermilion,
                   edgecolor="white", linewidth=0.35, zorder=5)
    if detected != len(sources):
        raise RuntimeError(
            f"Outward example is not fully detected: {detected}/16")
    ax.set_aspect("equal")
    ax.set_xlim(-2030, 2030)
    ax.set_ylim(-2030, 2030)
    ax.axis("off")

    data = [[float(row["virtual_time_s"]) for row in rows
             if row["scenario"] == key and int(row["complete"])]
            for key, _, _ in SCENARIOS]
    positions = np.arange(1, 4)
    parts = bx.violinplot(
        data, positions=positions, vert=False, widths=0.72,
        showmeans=False, showmedians=False, showextrema=False)
    for body, color in zip(parts["bodies"], colors):
        body.set_facecolor(color)
        body.set_edgecolor("none")
        body.set_alpha(0.60)
    boxes = bx.boxplot(
        data, positions=positions, vert=False, widths=0.18,
        showfliers=False, patch_artist=True,
        boxprops={"facecolor": "white", "edgecolor": dark,
                  "linewidth": 0.8},
        medianprops={"color": dark, "linewidth": 1.1},
        whiskerprops={"color": dark, "linewidth": 0.8},
        capprops={"color": dark, "linewidth": 0.8})
    for median in boxes["medians"]:
        median.set_zorder(5)
    bx.set_yticks(
        positions, [short for _, _, short in SCENARIOS])
    bx.set_xlabel("总虚拟时间/s")
    bx.set_ylim(0.45, 3.55)
    bx.grid(axis="x", color="#DCE2E9", linewidth=0.55, alpha=0.85)
    bx.spines["top"].set_visible(False)
    bx.spines["right"].set_visible(False)

    for label, axis in zip("ab", (ax, bx)):
        axis.text(
            0.01, 0.99, label, transform=axis.transAxes,
            fontsize=11.0, fontweight="bold", va="top", color=dark)
    ax.legend(
        handles=[
            Line2D([0], [0], marker="o", color="none", markerfacecolor=blue,
                   markersize=5.2, label="外环巡检"),
            Line2D([0], [0], marker="s", color="none",
                   markerfacecolor=orange, markersize=5.2, label="内环巡检"),
            Line2D([0], [0], marker="D", color="none", markerfacecolor=dark,
                   markersize=5.2, label="中心巡检"),
        Patch(facecolor=vermilion, edgecolor="none", alpha=0.28,
              label="定向源前向可检测范围"),
        ],
        loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3,
        frameon=False, fontsize=7.6, columnspacing=1.15,
        handletextpad=0.42)
    bx.legend(
        handles=[
            Line2D([0], [0], marker="o", color=vermilion,
                   markerfacecolor=vermilion, markersize=4.8,
                   linewidth=1.0, label="径向外射源"),
            Line2D([0], [0], color=grey, linewidth=0.8,
                   label="可接收巡检点"),
        ],
        loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2,
        frameon=False, fontsize=7.6, columnspacing=1.15,
        handletextpad=0.42)
    fig.savefig(
        output_dir / "q4_validation_overview.pdf", bbox_inches="tight")
    fig.savefig(
        output_dir / "q4_validation_overview.png", dpi=300,
        bbox_inches="tight")
    plt.close(fig)


def write_outputs(rows, output_dir):
    csv_path = output_dir / "q4_validation_runs.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = summarize(rows)
    (output_dir / "q4_validation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    metadata = {
        "design": "stratified fixed-seed Q4 offline validation",
        "time_statistics_population": "complete runs only",
        "seed_scheme": (
            "seed_base + (scenario_index + 3) * 1000000 + run_index; "
            "the +3 offset preserves the Q4 groups from the original "
            "joint Q3/Q4 validation"),
        "runs_total": len(rows),
        "scenarios": {
            "q4_mixed": (
                "8 omnidirectional and 8 directional sources; positions "
                "and directional headings are random"),
            "q4_directional": (
                "16 directional sources with random positions and headings"),
            "q4_outward": (
                "16 directional sources in the 1150--1800 m annulus, "
                "each pointing radially outward"),
        },
        "common_assumptions": {
            "sources_per_run": 16,
            "channels": "16 distinct channels sampled without replacement",
            "reception_radius_m": "independent uniform[1000,1500]",
            "bearing_error_deg": (
                "independent uniform[-1,1], rounded to 0.01 degree"),
            "directional_visibility": "closed forward half-plane",
            "movement_speed_m_per_s": 5,
            "measure_cost_s": 5,
            "channel_switch_cost_s": 1,
            "clear_cost_s": {
                "success": 5,
                "no_target_in_range": 3,
            },
            "clear_changes_measurement_channel": False,
        },
        "controller_sha256": hashlib.sha256(
            Q4_PATH.read_bytes()).hexdigest(),
        "scope_note": (
            "The harness is independent of the official simulator and "
            "supports empirical, not universal, claims."),
    }
    (output_dir / "q4_validation_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def load_rows(path):
    with path.open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for key in ("run_index", "seed", "cleared", "total", "complete",
                    "actions"):
            row[key] = int(row[key])
        for key in ("virtual_time_s", "runtime_s"):
            row[key] = float(row[key])
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples-per-scenario", type=int, default=500)
    parser.add_argument("--seed-base", type=int, default=20260913)
    parser.add_argument(
        "--workers", type=int, default=max(1, min(8, mp.cpu_count())))
    parser.add_argument(
        "--output-dir", type=Path,
        default=ROOT / "26GuoSai" / "q4_refinement")
    parser.add_argument(
        "--figures-only", action="store_true",
        help="Reuse q4_validation_runs.csv and redraw figures.")
    args = parser.parse_args()
    if args.samples_per_scenario < 1:
        raise ValueError("samples-per-scenario must be positive")

    setup_style()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    csv_path = args.output_dir / "q4_validation_runs.csv"
    if args.figures_only:
        rows = load_rows(csv_path)
        summary = write_outputs(rows, args.output_dir)
    else:
        tasks = []
        for scenario_index, (scenario, _, _) in enumerate(SCENARIOS):
            for run_index in range(args.samples_per_scenario):
                seed = (
                    args.seed_base
                    + (scenario_index + Q4_SEED_GROUP_OFFSET) * 1_000_000
                    + run_index
                )
                tasks.append((scenario, run_index, seed))
        if args.workers == 1:
            rows = [run_one(task) for task in tasks]
        else:
            context = mp.get_context("spawn")
            with context.Pool(args.workers) as pool:
                rows = list(pool.imap_unordered(
                    run_one, tasks, chunksize=4))
        rows.sort(key=lambda row: (row["scenario"], row["seed"]))
        summary = write_outputs(rows, args.output_dir)

    method_figure(args.output_dir)
    validation_figure(
        rows, args.output_dir, args.seed_base + 5_000_000)
    failures = [row for row in rows if not int(row["complete"])]
    print(json.dumps({
        "runs": len(rows),
        "complete_runs": len(rows) - len(failures),
        "failed_runs": len(failures),
        "wall_time_s": time.perf_counter() - started,
        "output_dir": str(args.output_dir),
        "summary": summary,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    mp.freeze_support()
    main()
