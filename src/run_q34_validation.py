#!/usr/bin/env python3
"""Reproducible offline validation for the submitted Q3 and Q4 controllers.

The harness reuses the standalone controllers without accessing latent source
coordinates from the policy.  It is an independent simulator, not the official
competition server; all assumptions are stated in the generated metadata.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import multiprocessing as mp
from dataclasses import dataclass
from pathlib import Path
import sys
import time

import matplotlib.pyplot as plt
import numpy as np


plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "SimSun"],
    "axes.unicode_minus": False,
    "pdf.fonttype": 42,
})


ROOT = Path(__file__).resolve().parents[2]
Q3_PATH = ROOT / "code" / "q3_best_standalone.py"
Q4_PATH = ROOT / "code" / "q4_standalone_副本.py"

SCENARIOS = (
    ("q3_uniform", 3, "全圆均匀"),
    ("q3_boundary", 3, "边界富集"),
    ("q3_clustered", 3, "空间聚集"),
    ("q4_mixed", 4, "混合源随机朝向"),
    ("q4_directional", 4, "全定向随机朝向"),
    ("q4_outward", 4, "全定向径向外射"),
)


@dataclass
class Source:
    channel: int
    position: np.ndarray
    reception_radius: float
    directional: bool
    heading: float
    cleared: bool = False


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_Q3 = None
_Q4 = None


def controller_module(problem: int):
    global _Q3, _Q4
    if problem == 3:
        if _Q3 is None:
            _Q3 = _load_module(Q3_PATH, "_validation_q3_controller")
        return _Q3
    if _Q4 is None:
        _Q4 = _load_module(Q4_PATH, "_validation_q4_controller")
    return _Q4


def uniform_disk(rng: np.random.Generator, count: int, r0=0.0, r1=1800.0):
    radius = np.sqrt(rng.uniform(r0 * r0, r1 * r1, count))
    angle = rng.uniform(0.0, 2 * np.pi, count)
    return radius[:, None] * np.column_stack((np.cos(angle), np.sin(angle)))


def clustered_points(rng: np.random.Generator, count: int):
    center = uniform_disk(rng, 1, 0.0, 1050.0)[0]
    points = []
    while len(points) < count:
        batch = center + rng.normal(0.0, 260.0, (count * 2, 2))
        points.extend(p for p in batch if np.linalg.norm(p) <= 1800.0)
    return np.asarray(points[:count])


def generate_sources(scenario: str, seed: int, source_count: int = 16):
    if not 1 <= source_count <= 16:
        raise ValueError("source_count must be in 1..16")
    rng = np.random.default_rng(seed)
    channels = rng.choice(np.arange(1, 21), source_count, replace=False)
    if scenario == "q3_uniform":
        points = uniform_disk(rng, source_count)
    elif scenario == "q3_boundary":
        points = uniform_disk(rng, source_count, 1350.0, 1800.0)
    elif scenario == "q3_clustered":
        points = clustered_points(rng, source_count)
    elif scenario in ("q4_mixed", "q4_directional"):
        points = uniform_disk(rng, source_count)
    elif scenario == "q4_outward":
        points = uniform_disk(rng, source_count, 1150.0, 1800.0)
    else:
        raise ValueError(f"Unknown scenario {scenario}")

    radii = rng.uniform(1000.0, 1500.0, source_count)
    random_headings = rng.uniform(0.0, 2 * np.pi, source_count)
    sources = []
    for i, (channel, point) in enumerate(zip(channels, points)):
        if scenario.startswith("q3_"):
            directional = False
            heading = 0.0
        elif scenario == "q4_mixed":
            directional = i >= source_count // 2
            heading = random_headings[i]
        elif scenario == "q4_directional":
            directional = True
            heading = random_headings[i]
        else:
            directional = True
            heading = math.atan2(point[1], point[0])
        sources.append(Source(
            int(channel), np.asarray(point, dtype=float), float(radii[i]),
            directional, float(heading)))
    return sources


class OfflineClient:
    """Minimal deterministic implementation of the competition action API."""

    def __init__(self, sources, seed):
        self.sources = sources
        self.rng = np.random.default_rng(seed ^ 0xA5A5A5A5)
        self.position = np.zeros(2)
        self.channel = 1
        self.time = 0.0
        self.deadline = math.inf
        self.calls = 0

    def _move(self, point):
        point = np.asarray(point, dtype=float)
        self.time += float(np.linalg.norm(point - self.position)) / 5.0
        self.position = point

    def _source(self, channel):
        return next(
            (s for s in self.sources if s.channel == int(channel) and not s.cleared),
            None)

    @staticmethod
    def _visible(source, receiver):
        if not source.directional:
            return True
        ray = np.array([math.cos(source.heading), math.sin(source.heading)])
        return float((receiver - source.position) @ ray) >= -1e-10

    def call(self, path, point=None, channel=None):
        self.calls += 1
        if path == "/enter":
            return {"accepted": True, "remaining_real_duration_s": 1e9,
                    "virtual_time_s": self.time}
        if path == "/exit":
            return {"accepted": True, "virtual_time_s": self.time}
        self._move(point)
        source = self._source(channel)
        distance = (math.inf if source is None else
                    float(np.linalg.norm(self.position - source.position)))
        if path == "/measure":
            if int(channel) != self.channel:
                self.time += 1.0
                self.channel = int(channel)
            self.time += 5.0
            if (source is None or distance > source.reception_radius
                    or not self._visible(source, self.position)):
                result = {"measure_result": "no_signal"}
            elif distance <= 5.0:
                result = {"measure_result": "near"}
            else:
                bearing = math.degrees(math.atan2(
                    source.position[1] - self.position[1],
                    source.position[0] - self.position[0]))
                bearing += self.rng.uniform(-1.0, 1.0)
                result = {"measure_result": "bearing",
                          "svd_deg": round(bearing, 2)}
            return dict(result, accepted=True, virtual_time_s=self.time)
        if path == "/clear":
            success = source is not None and distance <= 20.0
            self.time += 5.0 if success else 3.0
            if success:
                source.cleared = True
            return {"accepted": True,
                    "clear_result": (
                        "success" if success else "no_target_in_range"),
                    "virtual_time_s": self.time}
        raise ValueError(f"Unsupported path {path}")


def run_one(task):
    scenario, problem, seed = task
    sources = generate_sources(scenario, seed)
    client = OfflineClient(sources, seed)
    started = time.perf_counter()
    try:
        module = controller_module(problem)
        if problem == 3:
            policy = module.PortfolioTour(
                client, module.BEST_TOUR_CONFIG, module.BEST_PORTFOLIO_CONFIG)
        else:
            policy = module.PlannedNegativeTour(client, module.Q4_CONFIG)
        result = policy.run()
        error = ""
    except Exception as exc:
        result = {}
        error = f"{type(exc).__name__}: {exc}"
    cleared = sum(source.cleared for source in sources)
    return {
        "scenario": scenario,
        "problem": problem,
        "seed": seed,
        "cleared": cleared,
        "total": len(sources),
        "success": int(cleared == len(sources) and not error),
        "virtual_time_s": client.time,
        "actions": client.calls,
        "survey_stops": result.get("survey_stops", ""),
        "optical_fallbacks": result.get("optical_fallbacks", ""),
        "runtime_s": time.perf_counter() - started,
        "error": error,
    }


def wilson_interval(successes, total, z=1.959963984540054):
    if total == 0:
        return math.nan, math.nan
    p = successes / total
    den = 1 + z * z / total
    center = (p + z * z / (2 * total)) / den
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / den
    return center - radius, center + radius


def write_results(rows, output_dir: Path):
    csv_path = output_dir / "q34_validation_runs.csv"
    fields = list(rows[0])
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    summary = []
    labels = dict((key, label) for key, _, label in SCENARIOS)
    for key, problem, _ in SCENARIOS:
        group = [row for row in rows if row["scenario"] == key]
        successes = sum(int(row["success"]) for row in group)
        low, high = wilson_interval(successes, len(group))
        times = np.array([float(row["virtual_time_s"]) for row in group])
        actions = np.array([float(row["actions"]) for row in group])
        summary.append({
            "scenario": key,
            "label_zh": labels[key],
            "problem": problem,
            "runs": len(group),
            "successes": successes,
            "success_rate": successes / len(group),
            "wilson_95_low": low,
            "wilson_95_high": high,
            "virtual_time_mean_s": float(times.mean()),
            "virtual_time_sd_s": float(times.std(ddof=1)) if len(times) > 1 else 0.0,
            "virtual_time_p95_s": float(np.quantile(times, 0.95)),
            "virtual_time_max_s": float(times.max()),
            "actions_mean": float(actions.mean()),
            "actions_max": int(actions.max()),
        })
    summary_path = output_dir / "q34_validation_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    metadata = {
        "design": "stratified fixed-seed offline validation",
        "runs_total": len(rows),
        "scenario_definitions": {
            "q3_uniform": "16 omnidirectional sources uniformly distributed by area in the target disk",
            "q3_boundary": "16 omnidirectional sources uniformly distributed by area in the 1350--1800 m annulus",
            "q3_clustered": "16 omnidirectional sources sampled around one random cluster centre",
            "q4_mixed": "8 omnidirectional and 8 directional sources; positions and directional headings are random",
            "q4_directional": "16 directional sources with random positions and headings",
            "q4_outward": "16 directional sources in the 1150--1800 m annulus, each pointing radially outward",
        },
        "common_assumptions": {
            "sources_per_run": 16,
            "channels": "16 distinct channels sampled without replacement from 1--20",
            "reception_radius_m": "independent uniform[1000,1500]",
            "bearing_error_deg": "independent uniform[-1,1], then rounded to 0.01 degree",
            "directional_visibility": "closed forward half-plane (plus/minus 90 degrees)",
            "near_threshold_m": 5,
            "clear_threshold_m": 20,
            "movement_speed_m_per_s": 5,
            "measure_cost_s": 5,
            "channel_switch_cost_s": 1,
            "clear_cost_s": {"success": 5, "no_target_in_range": 3},
            "clear_changes_measurement_channel": False,
        },
        "controller_sha256": {
            str(Q3_PATH.name): hashlib.sha256(Q3_PATH.read_bytes()).hexdigest(),
            str(Q4_PATH.name): hashlib.sha256(Q4_PATH.read_bytes()).hexdigest(),
        },
        "scope_note": "This harness is independent of the official simulator and supports empirical, not universal, claims.",
    }
    (output_dir / "q34_validation_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#D9DEE7", linewidth=0.7, alpha=0.8)


def performance_figure(summary, output_dir):
    labels = [item["label_zh"] for item in summary]
    rates = np.array([item["success_rate"] for item in summary])
    lows = np.array([item["wilson_95_low"] for item in summary])
    colors = ["#2A6F97"] * 3 + ["#C8553D"] * 3
    x = np.arange(len(summary))
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    ax.bar(x, rates * 100, color=colors, width=0.68)
    ax.errorbar(x, rates * 100, yerr=(rates - lows) * 100, fmt="none",
                ecolor="#202124", capsize=4, linewidth=1.1)
    ax.set_ylabel("样本内完整清除率（%）")
    ax.set_ylim(max(0, lows.min() * 100 - 2), 100.5)
    ax.set_xticks(x, labels, rotation=18, ha="right")
    ax.set_title("六类预注册场景下的完整清除率与 Wilson 95% 置信下界")
    for i, item in enumerate(summary):
        ax.text(i, rates[i] * 100 - 0.25,
                f'{item["successes"]}/{item["runs"]}',
                ha="center", va="top", color="white", fontsize=9)
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(output_dir / "q34_validation_success.pdf", bbox_inches="tight")
    fig.savefig(output_dir / "q34_validation_success.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def stability_figure(rows, output_dir):
    keys = [item[0] for item in SCENARIOS]
    labels = [item[2] for item in SCENARIOS]
    data = [[float(row["virtual_time_s"]) for row in rows
             if row["scenario"] == key] for key in keys]
    fig, ax = plt.subplots(figsize=(9.2, 4.9))
    parts = ax.violinplot(data, showmeans=False, showmedians=False,
                          showextrema=False)
    for i, body in enumerate(parts["bodies"]):
        body.set_facecolor("#2A6F97" if i < 3 else "#C8553D")
        body.set_edgecolor("none")
        body.set_alpha(0.62)
    ax.boxplot(data, widths=0.15, showfliers=False, patch_artist=True,
               boxprops={"facecolor": "white", "edgecolor": "#202124"},
               medianprops={"color": "#202124", "linewidth": 1.4},
               whiskerprops={"color": "#202124"},
               capprops={"color": "#202124"})
    ax.set_xticks(np.arange(1, 7), labels, rotation=18, ha="right")
    ax.set_ylabel("总虚拟时间（s）")
    ax.set_title("六类固定样例的虚拟时间分布")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(output_dir / "q34_validation_stability.pdf", bbox_inches="tight")
    fig.savefig(output_dir / "q34_validation_stability.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def outward_figure(output_dir, seed):
    sources = generate_sources("q4_outward", seed)
    outer_angles = np.arange(18) * 2 * np.pi / 18
    inner_angles = np.deg2rad(10) + np.arange(12) * 2 * np.pi / 12
    stations = np.vstack([
        np.zeros((1, 2)),
        1850 * np.column_stack((np.cos(outer_angles), np.sin(outer_angles))),
        925 * np.column_stack((np.cos(inner_angles), np.sin(inner_angles))),
    ])
    fig, ax = plt.subplots(figsize=(7.0, 7.0))
    arena = plt.Circle((0, 0), 1800, facecolor="#F4F7FA",
                       edgecolor="#1F2933", linewidth=1.4)
    ax.add_patch(arena)
    ax.scatter(stations[1:19, 0], stations[1:19, 1], s=38,
               color="#2A6F97", marker="o", label="外环扫描点", zorder=4)
    ax.scatter(stations[19:, 0], stations[19:, 1], s=36,
               color="#E09F3E", marker="s", label="内环扫描点", zorder=4)
    ax.scatter(0, 0, s=50, color="#202124", marker="D",
               label="中心扫描点", zorder=5)
    detected = 0
    for source in sources:
        direction = np.array([math.cos(source.heading), math.sin(source.heading)])
        ax.arrow(source.position[0], source.position[1],
                 190 * direction[0], 190 * direction[1],
                 width=9, head_width=55, head_length=70,
                 length_includes_head=True, color="#B23A48", zorder=5)
        valid = []
        for station in stations:
            distance = np.linalg.norm(station - source.position)
            if (distance <= source.reception_radius
                    and float((station - source.position) @ direction) >= -1e-10):
                valid.append((distance, station))
        if valid:
            detected += 1
            _, station = min(valid, key=lambda item: item[0])
            ax.plot([source.position[0], station[0]],
                    [source.position[1], station[1]],
                    color="#5B6770", linewidth=0.65, alpha=0.6, zorder=2)
    ax.scatter([s.position[0] for s in sources],
               [s.position[1] for s in sources],
               s=28, color="#B23A48", zorder=6, label="径向外射定向源")
    ax.set_aspect("equal")
    ax.set_xlim(-2070, 2070)
    ax.set_ylim(-2070, 2070)
    ax.set_xlabel("$x$（m）")
    ax.set_ylabel("$y$（m）")
    ax.set_title(f"径向外射压力场景的多方位发现结果（{detected}/16）")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08),
              ncol=2, frameon=False)
    ax.grid(color="#D9DEE7", linewidth=0.6, alpha=0.65)
    fig.tight_layout()
    fig.savefig(output_dir / "q4_outward_adversarial.pdf", bbox_inches="tight")
    fig.savefig(output_dir / "q4_outward_adversarial.png", dpi=240,
                bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-per-scenario", type=int, default=500)
    parser.add_argument("--seed-base", type=int, default=20260913)
    parser.add_argument("--workers", type=int, default=max(1, min(8, mp.cpu_count())))
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "26GuoSai" / "validation")
    args = parser.parse_args()
    if args.runs_per_scenario < 1:
        raise ValueError("runs-per-scenario must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    tasks = []
    for scenario_index, (scenario, problem, _) in enumerate(SCENARIOS):
        for run_index in range(args.runs_per_scenario):
            seed = args.seed_base + scenario_index * 1_000_000 + run_index
            tasks.append((scenario, problem, seed))
    started = time.perf_counter()
    if args.workers == 1:
        rows = [run_one(task) for task in tasks]
    else:
        context = mp.get_context("spawn")
        with context.Pool(args.workers) as pool:
            rows = list(pool.imap_unordered(run_one, tasks, chunksize=4))
    rows.sort(key=lambda row: (row["scenario"], row["seed"]))
    summary = write_results(rows, args.output_dir)
    performance_figure(summary, args.output_dir)
    stability_figure(rows, args.output_dir)
    outward_figure(args.output_dir, args.seed_base + 5_000_000)
    failed = [row for row in rows if not row["success"]]
    report = {
        "runs": len(rows),
        "successful_runs": len(rows) - len(failed),
        "failed_runs": len(failed),
        "wall_time_s": time.perf_counter() - started,
        "output_dir": str(args.output_dir),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failed:
        print("First failures:")
        print(json.dumps(failed[:5], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    mp.freeze_support()
    main()
