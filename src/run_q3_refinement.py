#!/usr/bin/env python3
"""Q3 source-count experiment and log-derived explanatory figures."""
from __future__ import annotations

import argparse
import csv
import json
import math
import multiprocessing as mp
from pathlib import Path
import time
from types import SimpleNamespace

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LogNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrowPatch, Patch, Rectangle
import numpy as np
from shapely import minimum_bounding_circle
from shapely.geometry import Point, Polygon

from run_q34_validation import (
    ROOT, OfflineClient, controller_module, generate_sources,
)


SOURCE_COUNTS = tuple(range(10, 17))
EXAMPLE_COUNT = 10


class LoggingClient(OfflineClient):
    def __init__(self, sources, seed):
        super().__init__(sources, seed)
        self.log = []

    def call(self, path, point=None, channel=None):
        before_position = self.position.copy()
        before_time = self.time
        source = None if channel is None else self._source(channel)
        source_position = None if source is None else source.position.copy()
        result = super().call(path, point, channel)
        self.log.append({
            "index": len(self.log),
            "path": path,
            "channel": None if channel is None else int(channel),
            "position": self.position.copy(),
            "previous_position": before_position,
            "time_start_s": before_time,
            "time_end_s": self.time,
            "result": result.get("measure_result", result.get("clear_result", "")),
            "bearing_deg": result.get("svd_deg"),
            "source_position": source_position,
        })
        return result


def run_one(task):
    source_count, run_index, seed = task
    sources = generate_sources("q3_uniform", seed, source_count)
    client = OfflineClient(sources, seed)
    started = time.perf_counter()
    try:
        module = controller_module(3)
        policy = module.PortfolioTour(
            client, module.BEST_TOUR_CONFIG, module.BEST_PORTFOLIO_CONFIG)
        result = policy.run()
        error = ""
    except Exception as exc:
        result = {}
        error = f"{type(exc).__name__}: {exc}"
    cleared = sum(source.cleared for source in sources)
    return {
        "source_count": source_count,
        "run_index": run_index,
        "seed": seed,
        "cleared": cleared,
        "complete": int(cleared == source_count and not error),
        "virtual_time_s": client.time,
        "time_per_source_s": client.time / source_count,
        "actions": client.calls,
        "survey_stops": result.get("survey_stops", ""),
        "optical_fallbacks": result.get("optical_fallbacks", ""),
        "runtime_s": time.perf_counter() - started,
        "error": error,
    }


def summarize(rows):
    result = []
    for count in SOURCE_COUNTS:
        group = [row for row in rows if row["source_count"] == count]
        total_time = np.array([row["virtual_time_s"] for row in group])
        per_source = np.array([row["time_per_source_s"] for row in group])
        result.append({
            "source_count": count,
            "samples": len(group),
            "complete_samples": sum(row["complete"] for row in group),
            "mean_time_s": float(total_time.mean()),
            "sd_time_s": float(total_time.std(ddof=1)),
            "mean_time_per_source_s": float(per_source.mean()),
            "p95_time_s": float(np.quantile(total_time, 0.95)),
            "mean_actions": float(np.mean([row["actions"] for row in group])),
        })
    all_time = np.array([row["virtual_time_s"] for row in rows])
    all_per_source = np.array([row["time_per_source_s"] for row in rows])
    result.append({
        "source_count": "overall",
        "samples": len(rows),
        "complete_samples": sum(row["complete"] for row in rows),
        "mean_time_s": float(all_time.mean()),
        "sd_time_s": float(all_time.std(ddof=1)),
        "mean_time_per_source_s": float(all_per_source.mean()),
        "p95_time_s": float(np.quantile(all_time, 0.95)),
        "mean_actions": float(np.mean([row["actions"] for row in rows])),
    })
    return result


def run_logged_example(seed, source_count):
    sources = generate_sources("q3_uniform", seed, source_count)
    client = LoggingClient(sources, seed)
    module = controller_module(3)
    policy = module.PortfolioTour(
        client, module.BEST_TOUR_CONFIG, module.BEST_PORTFOLIO_CONFIG)
    policy.run()
    serializable = {
        "seed": seed,
        "source_count": source_count,
        "sources": [{
            "channel": source.channel,
            "position": source.position.tolist(),
            "reception_radius": source.reception_radius,
        } for source in sources],
        "survey": [point.tolist() for point in policy.survey],
        "actions": [{
            **{key: value for key, value in item.items()
               if key not in ("position", "previous_position", "source_position")},
            "position": item["position"].tolist(),
            "previous_position": item["previous_position"].tolist(),
            "source_position": (
                None if item["source_position"] is None
                else item["source_position"].tolist()),
        } for item in client.log],
        "virtual_time_s": client.time,
    }
    return sources, client, policy, serializable


def setup_style():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [
            "Arial Unicode MS", "Hiragino Sans GB", "Microsoft YaHei",
            "SimHei", "Songti SC", "SimSun",
        ],
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "font.size": 10,
    })


def plot_polygon(ax, shape, **kwargs):
    parts = list(shape.geoms) if hasattr(shape, "geoms") else [shape]
    for part in parts:
        if part.is_empty or part.geom_type != "Polygon":
            continue
        x, y = part.exterior.xy
        ax.fill(x, y, **kwargs)


def method_figure(output_dir):
    """Text-free method schematic; all semantics are carried by the legend."""
    blue = "#0072B2"
    sky = "#56B4E9"
    green = "#009E73"
    orange = "#E69F00"
    purple = "#CC79A7"
    dark = "#222222"
    grey = "#8A8A8A"

    fig, axes = plt.subplots(1, 3, figsize=(10.0, 3.55))
    fig.subplots_adjust(left=0.025, right=0.985, top=0.93,
                        bottom=0.31, wspace=0.12)

    # (a) Seven-point full-channel coverage.
    ax = axes[0]
    angles = np.arange(6) * np.pi / 3
    ring = 1.2 * np.column_stack([np.cos(angles), np.sin(angles)])
    scan = np.vstack([np.zeros(2), ring])
    route = np.vstack([scan[0], ring[[3, 2, 1, 0, 5, 4]]])
    ax.add_patch(Circle((0, 0), 1.8, facecolor="#FAFBFC",
                        edgecolor=dark, linewidth=1.0, zorder=0))
    for point in scan:
        ax.add_patch(Circle(point, 1.0, facecolor=sky, edgecolor=sky,
                            linewidth=0.5, alpha=0.16, zorder=1))
    for start, end in zip(route[:-1], route[1:]):
        ax.add_patch(FancyArrowPatch(
            start, end, arrowstyle="-|>", mutation_scale=7,
            color=blue, linewidth=1.0, shrinkA=5, shrinkB=5, zorder=3))
    ax.scatter(scan[:, 0], scan[:, 1], marker="s", s=30,
               facecolor=blue, edgecolor="white", linewidth=0.5, zorder=4)
    ax.set_xlim(-1.92, 1.92)
    ax.set_ylim(-1.92, 1.92)

    # (b) A metric-scale instance: target radius 1800 m and the guaranteed
    # reception/exclusion radius 1000 m.  Axes are intentionally hidden in
    # the final figure, but the geometry itself is kept in metres.
    ax = axes[1]
    arena = Point(0, 0).buffer(1800, quad_segs=96)
    ax.add_patch(Circle((0, 0), 1800, facecolor="#F3F5F7",
                        edgecolor=grey, linewidth=0.9, zorder=0))
    p1 = np.array([-600.0, 0.0])
    p2 = np.array([0.0, -600.0])
    negative = np.array([-1000.0, -600.0])
    # The common compatible location used only to construct this deterministic
    # illustration is within 1000 m of p1 and p2, and farther than 1000 m
    # from the no-signal point.
    reference = np.array([300.0, 300.0])
    half_angle = math.radians(1.0051)

    def bearing_sector(point, target):
        direction = math.atan2(target[1] - point[1], target[0] - point[0])
        rays = [
            point + 6000 * np.array([
                math.cos(direction - half_angle),
                math.sin(direction - half_angle)]),
            point + 6000 * np.array([
                math.cos(direction + half_angle),
                math.sin(direction + half_angle)]),
        ]
        return Polygon([point, *rays]).intersection(arena)

    wedge1 = bearing_sector(p1, reference)
    wedge2 = bearing_sector(p2, reference)
    # Use sufficiently distinct fills and outlines so that the three spatial
    # constraints remain legible after the figure is reduced in the paper.
    negative_disc = Point(negative).buffer(1000, quad_segs=96)
    plot_polygon(ax, negative_disc.intersection(arena), facecolor="#FDF1D4",
                 edgecolor="none", zorder=1)
    ax.add_patch(Circle(negative, 1000, facecolor="none", edgecolor=orange,
                        linewidth=1.25, linestyle="--", zorder=2))
    # Positive bearing constraints are kept above the exclusion fill so that
    # neither observation wedge is visually obscured where the regions meet.
    plot_polygon(ax, wedge1, facecolor="#9CCCE7", edgecolor=blue,
                 linewidth=1.15, zorder=3)
    plot_polygon(ax, wedge2, facecolor="#9CCCE7", edgecolor=blue,
                 linewidth=1.15, zorder=3)
    # The feasible set must be derived from the displayed constraints.  The
    # former hand-drawn polygon was not wholly inside both bearing wedges.
    # Intersect the two positive-observation wedges and remove the negative
    # observation disc, exactly mirroring the set-update logic in the text.
    feasible_shape = (
        wedge1.intersection(wedge2).difference(negative_disc))
    plot_polygon(ax, feasible_shape, facecolor=purple, alpha=0.92,
                 edgecolor=purple, linewidth=1.15, zorder=4)
    feasible = np.asarray(feasible_shape.exterior.coords[:-1])
    # Use the actual minimum covering circle of the constructed feasible set.
    cover = minimum_bounding_circle(feasible_shape)
    center = np.array([cover.centroid.x, cover.centroid.y])
    cover_radius = np.max(np.linalg.norm(feasible - center, axis=1))
    ax.add_patch(Circle(center, cover_radius, facecolor="none", edgecolor=green,
                        linewidth=1.0, linestyle="--", zorder=5))
    ax.scatter(*p1, marker="o", s=28, color=blue, zorder=6)
    ax.scatter(*p2, marker="o", s=28, color=blue, zorder=6)
    ax.scatter(*negative, marker="x", s=35, color=orange,
               linewidth=1.4, zorder=6)
    # Compact local enlargement preserves the physical construction above
    # while keeping the approximately 1-degree bearing intersection visible.
    zoom = ax.inset_axes([0.60, 0.12, 0.31, 0.31])
    plot_polygon(zoom, wedge1, facecolor="#9CCCE7", edgecolor=blue,
                 linewidth=0.9, zorder=1)
    plot_polygon(zoom, wedge2, facecolor="#9CCCE7", edgecolor=blue,
                 linewidth=0.9, zorder=1)
    plot_polygon(zoom, feasible_shape, facecolor=purple, alpha=0.92,
                 edgecolor=purple, linewidth=1.0, zorder=4)
    zoom.add_patch(Circle(center, cover_radius, facecolor="none",
                          edgecolor=green, linewidth=0.9,
                          linestyle="--", zorder=5))
    zoom.set_xlim(center[0] - 105, center[0] + 105)
    zoom.set_ylim(center[1] - 105, center[1] + 105)
    zoom.set_aspect("equal")
    zoom.set_xticks([])
    zoom.set_yticks([])
    for spine in zoom.spines.values():
        spine.set_color(grey)
        spine.set_linewidth(0.7)
    zoom.set_title("局部放大", fontsize=6.2, pad=1.5)
    ax.set_xlim(-1950, 1950)
    ax.set_ylim(-1950, 1950)

    # (c) Execute the first action, then replace the remaining open route.
    ax = axes[2]
    ax.add_patch(Circle((0, 0), 1.78, facecolor="#FAFBFC",
                        edgecolor=grey, linewidth=0.9, zorder=0))
    current = np.array([-1.48, -0.55])
    survey = np.array([[-0.35, 1.28], [1.18, -0.78]])
    local = np.array([[-0.92, 0.28], [0.20, -0.44], [0.88, 0.64]])
    clear = np.array([0.58, 1.16])
    first = local[0]
    old_route = np.vstack([current, first, survey[0], local[2], survey[1]])
    new_route = np.vstack([first, local[1], survey[1], local[2], survey[0]])
    for start, end in zip(old_route[:-1], old_route[1:]):
        ax.add_patch(FancyArrowPatch(
            start, end, arrowstyle="-|>", mutation_scale=7,
            color="#B6B6B6", linewidth=1.0, shrinkA=5, shrinkB=5, zorder=1))
    ax.plot(new_route[:, 0], new_route[:, 1], color=dark,
            linewidth=1.0, linestyle=(0, (3, 2)), zorder=2)
    ax.scatter(*current, marker=">", s=62, color=dark, zorder=5)
    ax.scatter(survey[:, 0], survey[:, 1], marker="s", s=32,
               facecolor=blue, edgecolor="white", linewidth=0.5, zorder=5)
    ax.scatter(local[:, 0], local[:, 1], marker="o", s=34,
               facecolor=green, edgecolor="white", linewidth=0.5, zorder=5)
    ax.scatter(*clear, marker="D", s=34, facecolor=purple,
               edgecolor="white", linewidth=0.5, zorder=5)
    ax.add_patch(Circle(first, 0.18, facecolor="none", edgecolor=orange,
                        linewidth=1.6, zorder=6))
    ax.set_xlim(-1.92, 1.92)
    ax.set_ylim(-1.92, 1.92)

    for label, ax in zip("abc", axes):
        ax.set_aspect("equal")
        ax.axis("off")
        ax.text(0.01, 0.99, label, transform=ax.transAxes,
                fontsize=11.0, fontweight="bold", va="top", color=dark)

    # Place only the symbols used in each panel underneath that panel.  A
    # figure-wide legend makes the correspondence with (a)--(c) ambiguous.
    panel_legends = [
        [
            Line2D([0], [0], marker="s", color=blue, markerfacecolor=blue,
                   markersize=5.5, linewidth=1.0, label="巡检节点"),
            Line2D([0], [0], marker="o", color=sky, markerfacecolor=sky,
                   alpha=0.35, markersize=7, linewidth=0, label="接收覆盖"),
        ],
        [
            Patch(facecolor="#9CCCE7", edgecolor=blue,
                  label="示向约束域"),
            Line2D([0], [0], color=orange, linewidth=1.25,
                   linestyle="--", marker="o", markerfacecolor="#FDF1D4",
                   markeredgecolor=orange, markersize=6,
                   label="无信号排除域"),
            Patch(facecolor=purple, edgecolor=purple, label="位置可行集"),
            Line2D([0], [0], color=green, linewidth=1.2,
                   linestyle="--", label="最小覆盖圆"),
        ],
        [
            Line2D([0], [0], marker=">", color=dark,
                   markerfacecolor=dark, markersize=6, linewidth=0,
                   label="当前位置"),
            Line2D([0], [0], marker="s", color=blue, markerfacecolor=blue,
                   markersize=5.5, linewidth=0, label="巡检节点"),
            Line2D([0], [0], marker="o", color=green,
                   markerfacecolor=green, markersize=5.5, linewidth=0,
                   label="局部测向"),
            Line2D([0], [0], marker="D", color=purple,
                   markerfacecolor=purple, markersize=5.5, linewidth=0,
                   label="清除"),
            Line2D([0], [0], marker="o", color=orange,
                   markerfacecolor="none", markersize=8, linewidth=0,
                   label="本轮执行"),
            Line2D([0], [0], color=dark, linewidth=1.0,
                   linestyle=(0, (3, 2)), label="重规划"),
        ],
    ]
    for axis, handles in zip(axes, panel_legends):
        axis.legend(handles=handles, loc="upper center",
                    bbox_to_anchor=(0.5, -0.055), frameon=False,
                    fontsize=7.4, ncol=2, columnspacing=0.9,
                    handletextpad=0.35)
    fig.savefig(output_dir / "q3_method_overview.pdf", bbox_inches="tight")
    fig.savefig(output_dir / "q3_method_overview.png", dpi=300,
                bbox_inches="tight")
    plt.close(fig)


def load_http_action_log(path):
    """Normalize the standalone controller's JSONL log for figure replay."""
    events = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record["path"] not in ("/measure", "/clear"):
                continue
            request = record["request"]
            response = record["response"]
            point = request["position"]
            result = response.get(
                "measure_result", response.get("clear_result", ""))
            events.append({
                "path": record["path"],
                "channel": int(request["channel"]),
                "position": np.array([point["x"], point["y"]], dtype=float),
                "time_end_s": float(response["virtual_time_s"]),
                "result": result,
                "bearing_deg": response.get("svd_deg"),
            })
    return SimpleNamespace(
        log=events,
        time=events[-1]["time_end_s"] if events else 0.0,
    )


def trajectory_figure(sources, client, policy, output_dir):
    """Reconstruct every macro decision and the associated feasible-set state."""
    module = controller_module(3)
    blue = "#3C5488"
    green = "#009E73"
    orange = "#D55E00"
    dark = "#2B2B2B"
    grid = "#DCE2E9"
    mode_colors = {
        "survey": blue,
        "measure": orange,
        "clear": green,
        "clear_fail": "#CC3311",
    }
    mode_labels = {
        "survey": "全频道巡检",
        "measure": "局部补充测向",
        "clear": "光学定位与清除",
        "clear_fail": "试探清除未命中",
    }
    event_actions = [item for item in client.log
                     if item["path"] in ("/measure", "/clear")]
    groups = []
    for item in event_actions:
        position = np.asarray(item["position"], dtype=float)
        if (not groups
                or np.linalg.norm(position - groups[-1]["position"]) > 1e-5):
            groups.append({"position": position.copy(), "actions": []})
        groups[-1]["actions"].append(item)

    survey_points = (
        [] if policy is None
        else [np.asarray(point, dtype=float) for point in policy.survey]
    )
    previous_end = 0.0
    for group in groups:
        paths = [item["path"] for item in group["actions"]]
        if any(path == "/clear" for path in paths):
            clear_results = [
                item["result"] for item in group["actions"]
                if item["path"] == "/clear"
            ]
            mode = "clear" if "success" in clear_results else "clear_fail"
        elif (any(np.linalg.norm(group["position"] - point) < 1e-5
                  for point in survey_points)
              or (policy is None
                  and sum(path == "/measure" for path in paths) == 20)):
            mode = "survey"
        else:
            mode = "measure"
        group["mode"] = mode
        group["time_end_s"] = group["actions"][-1]["time_end_s"]
        group["duration_s"] = group["time_end_s"] - previous_end
        previous_end = group["time_end_s"]
        if mode == "survey":
            group["short_label"] = "巡"
        else:
            preferred = [item for item in group["actions"]
                         if item["path"] == ("/clear" if mode.startswith("clear")
                                             else "/measure")]
            group["short_label"] = (
                ("失" if mode == "clear_fail"
                 else "清" if mode == "clear" else "测")
                + str(preferred[0]["channel"]))

    tracks = {channel: module.Track(channel) for channel in range(1, 21)}
    states = []
    clear_marks = []
    failed_clear_marks = []
    first_seen = {}
    for step, group in enumerate(groups, 1):
        for item in group["actions"]:
            track = tracks[item["channel"]]
            point = np.asarray(item["position"], dtype=float)
            result = item["result"]
            if item["path"] == "/measure":
                if result == "no_signal":
                    track.negatives.append(point.copy())
                    track.shape = track.shape.difference(
                        Point(point).buffer(1000, quad_segs=48))
                    for positive, _ in track.positives:
                        track.shape = track.shape.intersection(
                            module.closer_to_positive_halfplane(
                                positive, point))
                else:
                    track.known = True
                    first_seen.setdefault(track.channel, step)
                    angle = item["bearing_deg"]
                    track.positives.append((point.copy(), angle))
                    if result == "near":
                        track.shape = track.shape.intersection(
                            module.outer_disc(point, 5))
                    else:
                        track.shape = module.update_direction(
                            track.shape, point, angle)
                    for negative in track.negatives:
                        track.shape = track.shape.intersection(
                            module.closer_to_positive_halfplane(
                                point, negative))
            elif result == "success":
                track.cleared = True
                clear_marks.append((step, track.channel))
            else:
                failed_clear_marks.append((step, track.channel))
                track.shape = track.shape.difference(
                    Point(point).buffer(20, quad_segs=32))
            if track.known and track.shape.is_empty:
                raise RuntimeError(
                    f"Empty reconstructed feasible set for channel {track.channel}")
        states.append({
            channel: module.enclosing_circle(track.shape)[1]
            for channel, track in tracks.items()
            if track.known and not track.cleared
        })

    channels = sorted(first_seen)
    channel_index = {channel: index for index, channel in enumerate(channels)}
    measurement_states = []
    for step, group in enumerate(groups, 1):
        updated_channels = {
            item["channel"] for item in group["actions"]
            if item["path"] == "/measure"
            and item["channel"] in channel_index
        }
        for channel in sorted(updated_channels):
            radius = states[step - 1].get(channel)
            if radius is not None:
                measurement_states.append((step, channel, radius))

    fig = plt.figure(figsize=(10.0, 4.3))
    outer = fig.add_gridspec(
        1, 2, width_ratios=[1.0, 1.42], left=0.06, right=0.975,
        top=0.93, bottom=0.15, wspace=0.22)
    ax = fig.add_subplot(outer[0, 0])
    bx = fig.add_subplot(outer[0, 1])

    # Spatial trajectory, with order encoded continuously rather than numbered.
    positions = np.asarray([group["position"] for group in groups])
    path = np.vstack([np.zeros(2), positions])
    segments = np.stack([path[:-1], path[1:]], axis=1)
    ax.add_patch(Circle((0, 0), 1800, facecolor="#FAFBFC",
                        edgecolor=dark, linewidth=0.9, zorder=0))
    collection = LineCollection(
        segments, cmap="cividis", linewidths=1.4, alpha=0.95)
    collection.set_array(np.arange(1, len(groups) + 1))
    collection.set_clim(1, len(groups))
    ax.add_collection(collection)
    for mode, marker in (
            ("survey", "s"), ("measure", "o"),
            ("clear", "D"), ("clear_fail", "X")):
        ids = [index for index, group in enumerate(groups)
               if group["mode"] == mode]
        if not ids:
            continue
        points = positions[ids]
        ax.scatter(points[:, 0], points[:, 1], marker=marker, s=34,
                   facecolor=mode_colors[mode], edgecolor="white",
                   linewidth=0.55, label=mode_labels[mode], zorder=4)
    ax.set_aspect("equal")
    ax.set_xlim(-1950, 1950)
    ax.set_ylim(-1950, 1950)
    ax.set_xlabel("$x$（m）")
    ax.set_ylabel("$y$（m）")
    ax.legend(loc="lower left", frameon=False, fontsize=7.4,
              handletextpad=0.35)
    ax.grid(color=grid, linewidth=0.55, alpha=0.75)
    route_bar = fig.colorbar(
        collection, ax=ax, orientation="horizontal",
        pad=0.075, fraction=0.045, aspect=24)
    route_bar.set_label("停驻步 $k$", fontsize=8.0)
    route_bar.ax.tick_params(labelsize=8.0)
    route_bar.set_ticks([1, len(groups)])

    # Sparse event timeline: circles shrink as the feasible set contracts.
    clear_by_channel = {channel: step for step, channel in clear_marks}
    for channel in channels:
        row = channel_index[channel]
        start = first_seen[channel]
        end = clear_by_channel.get(channel, len(groups))
        bx.hlines(row, start, end, color="#C7CDD4", linewidth=1.0, zorder=0)
    norm = LogNorm(vmin=20, vmax=2000)
    cmap = plt.get_cmap("cividis_r")
    if measurement_states:
        event_steps = np.array([item[0] for item in measurement_states])
        event_rows = np.array([channel_index[item[1]]
                               for item in measurement_states])
        event_radii = np.array([item[2] for item in measurement_states])
        size_scale = np.clip(
            18 + 34 * np.log10(np.maximum(event_radii, 20) / 20) / 2,
            18, 52)
        image = bx.scatter(
            event_steps, event_rows, c=event_radii, s=size_scale,
            cmap=cmap, norm=norm, marker="o", edgecolor="white",
            linewidth=0.45, zorder=3)
    else:
        image = None
    for step, channel in clear_marks:
        if channel not in channel_index:
            continue
        row = channel_index[channel]
        bx.scatter(step, row, marker="D", s=36, facecolor=green,
                   edgecolor="white", linewidth=0.5, zorder=5)
    for step, channel in failed_clear_marks:
        if channel in channel_index:
            bx.scatter(step, channel_index[channel], marker="X", s=38,
                       facecolor=mode_colors["clear_fail"], edgecolor="white",
                       linewidth=0.5, zorder=5)
    for step in range(1, len(groups) + 1):
        bx.axvline(step, color="#EEF1F4", linewidth=0.45, zorder=0)
    bx.set_yticks(np.arange(len(channels)), [str(channel) for channel in channels])
    bx.set_ylabel("频道")
    bx.set_xlabel("停驻步 $k$")
    bx.set_xlim(0.5, len(groups) + 0.5)
    bx.set_ylim(len(channels) - 0.5, -0.5)
    bx.set_xticks(np.arange(1, len(groups) + 1))
    bx.tick_params(axis="x", labelsize=8.0)
    bx.tick_params(axis="y", labelsize=8.0)
    bx.spines["top"].set_visible(False)
    bx.spines["right"].set_visible(False)
    bx.grid(axis="y", color="#EEF1F4", linewidth=0.45)
    state_handles = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="#5577AA", markeredgecolor="white",
               markersize=6, label="测向更新"),
        Line2D([0], [0], marker="D", color="none",
               markerfacecolor=green, markeredgecolor="white",
               markersize=6, label="清除成功"),
    ]
    if failed_clear_marks:
        state_handles.append(Line2D(
            [0], [0], marker="X", color="none",
            markerfacecolor=mode_colors["clear_fail"],
            markeredgecolor="white", markersize=6, label="清除未命中"))
    bx.legend(handles=state_handles, loc="upper right", frameon=False,
              fontsize=8.0, ncol=len(state_handles),
       handletextpad=0.3, columnspacing=0.9)
    if image is not None:
        colorbar = fig.colorbar(image, ax=bx, pad=0.015, fraction=0.035)
        colorbar.set_label("$r_c$（m）", fontsize=8.2)
        colorbar.set_ticks([20, 50, 100, 200, 500, 1000, 2000])
        colorbar.set_ticklabels(
            ["20", "50", "100", "200", "500", "1000", "2000"])
        colorbar.ax.tick_params(labelsize=8.0)
    for label, axis in zip("ab", (ax, bx)):
        axis.text(0.01, 0.99, label, transform=axis.transAxes,
                  fontsize=11.0, fontweight="bold", va="top", color=dark)
    fig.savefig(output_dir / "q3_example_trajectory.pdf", bbox_inches="tight")
    fig.savefig(output_dir / "q3_example_trajectory.png", dpi=300,
                bbox_inches="tight")
    plt.close(fig)


def log_spectrum_figure(client, policy, output_dir):
    """Show channel-wise observations and belief contraction by decision step."""
    blue = "#3C5488"
    green = "#00A087"
    orange = "#E64B35"
    grey = "#8C8C8C"
    pale = "#EDF2F7"

    event_actions = [item for item in client.log
                     if item["path"] in ("/measure", "/clear")]
    groups = []
    for item in event_actions:
        position = np.asarray(item["position"], dtype=float)
        if (not groups
                or np.linalg.norm(position - groups[-1]["position"]) > 1e-5):
            groups.append({"position": position.copy(), "actions": []})
        groups[-1]["actions"].append(item)

    survey_steps = []
    for step, group in enumerate(groups, 1):
        if any(np.linalg.norm(group["position"] - point) < 1e-5
               for point in policy.survey):
            survey_steps.append(step)

    fig, (ax, bx) = plt.subplots(
        2, 1, figsize=(8.2, 6.0), sharex=True,
        gridspec_kw={"height_ratios": [1.0, 1.18]})
    for step in survey_steps:
        ax.axvspan(step - 0.48, step + 0.48, color=pale, zorder=0)

    marker_style = {
        "no_signal": ("x", grey, 14),
        "bearing": ("o", blue, 18),
        "near": ("^", orange, 22),
        "clear_success": ("s", green, 22),
        "clear_failed": ("s", orange, 24),
    }
    observed_keys = set()
    for step, group in enumerate(groups, 1):
        for item in group["actions"]:
            channel = item["channel"]
            if item["path"] == "/measure":
                key = item["result"]
                offset = -0.11
            else:
                key = "clear_success" if item["result"] == "success" else "clear_failed"
                offset = 0.11
            observed_keys.add(key)
            marker, color, size = marker_style[key]
            if key == "clear_failed":
                ax.scatter(step + offset, channel, marker=marker, s=size,
                           facecolor="none", edgecolor=color, linewidth=0.9,
                           zorder=4)
            else:
                ax.scatter(step + offset, channel, marker=marker, s=size,
                           color=color, linewidth=0.7, zorder=4)

    legend_catalog = {
        "no_signal": Line2D([0], [0], marker="x", linestyle="none",
                            color=grey, markersize=5, label="无信号"),
        "bearing": Line2D([0], [0], marker="o", linestyle="none",
                          color=blue, markersize=5, label="示向"),
        "near": Line2D([0], [0], marker="^", linestyle="none",
                       color=orange, markersize=5, label="近距"),
        "clear_success": Line2D([0], [0], marker="s", linestyle="none",
                                color=green, markersize=5, label="清除"),
        "clear_failed": Line2D(
            [0], [0], marker="s", linestyle="none", markerfacecolor="none",
            markeredgecolor=orange, markersize=5, label="清除失败"),
    }
    legend_order = ("no_signal", "bearing", "near", "clear_success",
                    "clear_failed")
    legend = [legend_catalog[key] for key in legend_order
              if key in observed_keys]
    ax.legend(handles=legend, frameon=False, ncol=len(legend), fontsize=7.4,
              loc="lower left", bbox_to_anchor=(0.0, 1.01),
              columnspacing=1.1, handletextpad=0.3, borderaxespad=0)
    ax.set_ylabel("频道")
    ax.set_ylim(0.5, 20.5)
    ax.set_yticks(np.arange(1, 21))
    ax.grid(axis="y", color="#E1E5EA", linewidth=0.45)

    module = controller_module(3)
    tracks = {channel: module.Track(channel) for channel in range(1, 21)}
    radii = np.full((20, len(groups)), np.nan)
    clear_marks = []
    for step_index, group in enumerate(groups):
        for item in group["actions"]:
            track = tracks[item["channel"]]
            point = np.asarray(item["position"], dtype=float)
            if item["path"] == "/measure":
                if item["result"] == "no_signal":
                    track.negatives.append(point.copy())
                    track.shape = track.shape.difference(
                        Point(point).buffer(1000, quad_segs=48))
                    for positive, _ in track.positives:
                        track.shape = track.shape.intersection(
                            module.closer_to_positive_halfplane(
                                positive, point))
                else:
                    track.known = True
                    angle = item["bearing_deg"]
                    track.positives.append((point.copy(), angle))
                    if item["result"] == "near":
                        track.shape = track.shape.intersection(
                            module.outer_disc(point, 5))
                    else:
                        track.shape = module.update_direction(
                            track.shape, point, angle)
                    for negative in track.negatives:
                        track.shape = track.shape.intersection(
                            module.closer_to_positive_halfplane(
                                point, negative))
            elif item["result"] == "success":
                track.cleared = True
                clear_marks.append((step_index + 1, track.channel))
            else:
                track.shape = track.shape.difference(
                    Point(point).buffer(20, quad_segs=32))
            if track.known and track.shape.is_empty:
                raise RuntimeError(
                    f"Empty reconstructed belief for channel {track.channel}")
        for channel, track in tracks.items():
            if track.known and not track.cleared:
                radii[channel - 1, step_index] = module.enclosing_circle(
                    track.shape)[1]

    coverage_step = max(survey_steps) if survey_steps else None
    excluded_channels = [channel for channel, track in tracks.items()
                         if not track.known]
    if coverage_step is not None:
        for channel in excluded_channels:
            bx.add_patch(Rectangle(
                (coverage_step - 0.5, channel - 0.5),
                len(groups) - coverage_step + 1, 1,
                facecolor="#E3E6E9", edgecolor="none", zorder=0))

    cmap = plt.get_cmap("viridis_r").copy()
    cmap.set_bad((1, 1, 1, 0))
    image = bx.imshow(
        np.ma.masked_invalid(radii), origin="lower", aspect="auto",
        interpolation="nearest", extent=(0.5, len(groups) + 0.5, 0.5, 20.5),
        cmap=cmap, norm=LogNorm(vmin=20, vmax=2000))
    for step in survey_steps:
        bx.axvline(step, color="#AAB4C0", linewidth=0.55, alpha=0.8)
    if clear_marks:
        xy = np.asarray(clear_marks)
        bx.scatter(xy[:, 0], xy[:, 1], marker="s", s=15,
                   facecolor=green, edgecolor="white", linewidth=0.35,
                   zorder=5)
    colorbar = fig.colorbar(image, ax=bx, pad=0.015, fraction=0.025)
    colorbar.set_label("可行域覆盖半径 $r_c$（m）")
    colorbar.set_ticks([20, 50, 100, 200, 500, 1000, 2000])
    colorbar.set_ticklabels(["20", "50", "100", "200", "500", "1000", "2000"])
    bx.set_xlabel("决策步")
    bx.set_ylabel("频道")
    bx.set_ylim(0.5, 20.5)
    bx.set_yticks(np.arange(1, 21))
    tick_step = max(1, math.ceil(len(groups) / 12))
    bx.set_xticks(np.arange(1, len(groups) + 1, tick_step))

    for label, axis in zip("ab", (ax, bx)):
        axis.text(-0.08, 1.03, label, transform=axis.transAxes,
                  fontsize=11, fontweight="bold", va="top", color="#2F2F2F")
        axis.tick_params(labelsize=7.5, width=0.7, length=3)
        for spine in axis.spines.values():
            spine.set_linewidth(0.7)
    fig.tight_layout(pad=0.8, h_pad=1.0)
    fig.savefig(output_dir / "q3_log_spectrum.pdf", bbox_inches="tight")
    fig.savefig(output_dir / "q3_log_spectrum.png", dpi=300,
                bbox_inches="tight")
    plt.close(fig)


def belief_history(module, client, channel):
    shape = module.ARENA
    positives = []
    history = []
    true_position = None
    for item in client.log:
        if item["path"] != "/measure" or item["channel"] != channel:
            continue
        point = item["position"]
        true_position = item["source_position"]
        if item["result"] == "no_signal":
            shape = shape.difference(Point(point).buffer(1000, quad_segs=48))
            for positive, _ in positives:
                shape = shape.intersection(
                    module.closer_to_positive_halfplane(positive, point))
        else:
            angle = item["bearing_deg"]
            positives.append((point.copy(), angle))
            if item["result"] == "near":
                shape = shape.intersection(module.outer_disc(point, 5))
            else:
                shape = module.update_direction(shape, point, angle)
            for negative_item in [
                    old for old in client.log[:item["index"]]
                    if old["path"] == "/measure"
                    and old["channel"] == channel
                    and old["result"] == "no_signal"]:
                shape = shape.intersection(
                    module.closer_to_positive_halfplane(
                        point, negative_item["position"]))
        history.append({
            "shape": shape,
            "point": point.copy(),
            "result": item["result"],
            "bearing": item["bearing_deg"],
            "true_position": true_position,
        })
    return history


def belief_figure(sources, client, output_dir):
    module = controller_module(3)
    candidates = []
    for source in sources:
        history = belief_history(module, client, source.channel)
        bearing_count = sum(item["result"] == "bearing" for item in history)
        if bearing_count >= 2:
            candidates.append((len(history), source.channel, history))
    if not candidates:
        return None
    _, channel, history = max(candidates)
    indices = sorted(set(np.linspace(
        0, len(history) - 1, min(4, len(history)), dtype=int)))
    fig, axes = plt.subplots(2, 2, figsize=(7.6, 6.8), squeeze=False)
    axes_flat = axes.ravel()
    for panel, history_index in enumerate(indices):
        ax = axes_flat[panel]
        state = history[history_index]
        arena = plt.Circle((0, 0), 1800, facecolor="#F5F7FA",
                           edgecolor="#59636E", linewidth=0.9)
        ax.add_patch(arena)
        plot_polygon(ax, state["shape"], color="#5B8DB8", alpha=0.55)
        used = history[:history_index + 1]
        positive = np.array([item["point"] for item in used
                             if item["result"] != "no_signal"])
        negative = np.array([item["point"] for item in used
                             if item["result"] == "no_signal"])
        if len(positive):
            ax.scatter(positive[:, 0], positive[:, 1], s=25, marker="o",
                       color="#1B7F5C", zorder=5)
        if len(negative):
            ax.scatter(negative[:, 0], negative[:, 1], s=25, marker="x",
                       color="#B23A48", zorder=5)
        true_position = np.asarray(state["true_position"])
        ax.scatter(true_position[0], true_position[1], marker="*", s=75,
                   color="#202733", zorder=6)
        vertices = module.vertices(state["shape"])
        if len(vertices):
            _, radius = module.enclosing_circle(state["shape"])
            area_m2 = state["shape"].area
            if area_m2 >= 1e4:
                area_text = f"{area_m2 / 1e6:.3f}\\,\\mathrm{{km}}^2"
            else:
                area_text = f"{area_m2:.0f}\\,\\mathrm{{m}}^2"
            annotation = f"$A={area_text}$\n$r={radius:.1f}\\,\\mathrm{{m}}$"
        else:
            annotation = "空集"
        ax.text(0.04, 0.96, annotation, transform=ax.transAxes,
                ha="left", va="top", fontsize=8)
        ax.set_title(f"({chr(97 + panel)}) 第 {history_index + 1} 次观测")
        ax.set_aspect("equal")
        ax.set_xlim(-1900, 1900)
        ax.set_ylim(-1900, 1900)
        ax.set_xticks([-1500, 0, 1500])
        ax.set_yticks([-1500, 0, 1500])
        ax.grid(color="#D9DEE7", linewidth=0.5)
    for ax in axes_flat[len(indices):]:
        ax.axis("off")
    fig.suptitle(f"频道 {channel} 的观测驱动可行域收缩", y=0.995)
    fig.tight_layout()
    fig.savefig(output_dir / "q3_belief_contraction.pdf", bbox_inches="tight")
    fig.savefig(output_dir / "q3_belief_contraction.png", dpi=240,
                bbox_inches="tight")
    plt.close(fig)
    return channel


def count_figure(rows, output_dir):
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10.2, 4.2))
    groups = [[row["virtual_time_s"] for row in rows
               if row["source_count"] == count] for count in SOURCE_COUNTS]
    parts = ax.violinplot(groups, positions=SOURCE_COUNTS, widths=0.72,
                          showmeans=False, showmedians=False, showextrema=False)
    for body in parts["bodies"]:
        body.set_facecolor("#5B8DB8")
        body.set_edgecolor("none")
        body.set_alpha(0.68)
    ax.boxplot(groups, positions=SOURCE_COUNTS, widths=0.20, showfliers=False,
               patch_artist=True,
               boxprops={"facecolor": "white", "edgecolor": "#202733"},
               medianprops={"color": "#202733", "linewidth": 1.3},
               whiskerprops={"color": "#202733"},
               capprops={"color": "#202733"})
    ax.set_xticks(SOURCE_COUNTS)
    ax.set_xlabel("干扰源数量")
    ax.set_ylabel("总虚拟时间（s）")
    ax.set_title("(a) 总时间分布")
    ax.grid(axis="y", color="#D9DEE7", linewidth=0.65)

    means = [np.mean([row["time_per_source_s"] for row in rows
                      if row["source_count"] == count])
             for count in SOURCE_COUNTS]
    sds = [np.std([row["time_per_source_s"] for row in rows
                   if row["source_count"] == count], ddof=1)
           for count in SOURCE_COUNTS]
    bx.errorbar(SOURCE_COUNTS, means, yerr=sds, marker="o", markersize=5,
                linewidth=1.8, capsize=4, color="#B23A48")
    bx.set_xticks(SOURCE_COUNTS)
    bx.set_xlabel("干扰源数量")
    bx.set_ylabel("平均单源时间（s）")
    bx.set_title("(b) 单源平均代价")
    bx.grid(color="#D9DEE7", linewidth=0.65)
    for axis in (ax, bx):
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(output_dir / "q3_source_count_performance.pdf",
                bbox_inches="tight")
    fig.savefig(output_dir / "q3_source_count_performance.png", dpi=240,
                bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples-per-count", type=int, default=500)
    parser.add_argument("--seed-base", type=int, default=20260913)
    parser.add_argument("--workers", type=int,
                        default=max(1, min(8, mp.cpu_count())))
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "26GuoSai" / "q3_refinement")
    parser.add_argument(
        "--action-log", type=Path,
        default=ROOT / "26GuoSai" / "q3_refinement"
        / "q3_best_http_10_seed20261233.jsonl")
    args = parser.parse_args()
    setup_style()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    tasks = []
    for group_index, source_count in enumerate(SOURCE_COUNTS):
        for run_index in range(args.samples_per_count):
            seed = args.seed_base + group_index * 1_000_000 + run_index
            tasks.append((source_count, run_index, seed))
    started = time.perf_counter()
    if args.workers == 1:
        rows = [run_one(task) for task in tasks]
    else:
        context = mp.get_context("spawn")
        with context.Pool(args.workers) as pool:
            rows = list(pool.imap_unordered(run_one, tasks, chunksize=4))
    rows.sort(key=lambda row: (row["source_count"], row["seed"]))
    with (args.output_dir / "q3_source_count_runs.csv").open(
            "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = summarize(rows)
    (args.output_dir / "q3_source_count_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    count_figure(rows, args.output_dir)
    method_figure(args.output_dir)

    example_rows = [row for row in rows
                    if row["source_count"] == EXAMPLE_COUNT]
    target = float(np.median([row["virtual_time_s"] for row in example_rows]))
    example = min(example_rows,
                  key=lambda row: abs(row["virtual_time_s"] - target))
    sources, client, policy, log = run_logged_example(
        example["seed"], EXAMPLE_COUNT)
    (args.output_dir / "q3_example_log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.action_log.is_file():
        http_client = load_http_action_log(args.action_log)
        trajectory_figure(None, http_client, None, args.output_dir)
    else:
        trajectory_figure(sources, client, policy, args.output_dir)
    log_spectrum_figure(client, policy, args.output_dir)
    channel = belief_figure(sources, client, args.output_dir)
    failures = [row for row in rows if not row["complete"]]
    print(json.dumps({
        "runs": len(rows),
        "complete_runs": len(rows) - len(failures),
        "failed_runs": len(failures),
        "example_seed": example["seed"],
        "belief_channel": channel,
        "wall_time_s": time.perf_counter() - started,
        "summary": summary,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    mp.freeze_support()
    main()
