#!/usr/bin/env python3
"""Q4 source-count validation with random source types and headings."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import multiprocessing as mp
from pathlib import Path
import time

import numpy as np

from run_q34_validation import (
    Q4_PATH, ROOT, OfflineClient, controller_module, generate_sources,
)

SOURCE_COUNTS = tuple(range(10, 17))
TYPE_SEED_XOR = 0x5A17C0DE


def generate_random_mixed_sources(seed: int, source_count: int):
    """Each source type is an independent fair draw; headings are uniform."""
    sources = generate_sources("q4_mixed", seed, source_count)
    rng = np.random.default_rng(seed ^ TYPE_SEED_XOR)
    for source in sources:
        source.directional = bool(rng.integers(0, 2))
        source.heading = float(rng.uniform(0.0, 2.0 * math.pi))
    return sources


def run_one(task):
    source_count, run_index, seed = task
    sources = generate_random_mixed_sources(seed, source_count)
    client = OfflineClient(sources, seed)
    started = time.perf_counter()
    try:
        module = controller_module(4)
        result = module.PlannedNegativeTour(client, module.Q4_CONFIG).run()
        error = ""
    except Exception as exc:
        result = {}
        error = f"{type(exc).__name__}: {exc}"
    cleared = sum(source.cleared for source in sources)
    directional_count = sum(source.directional for source in sources)
    return {
        "source_count": source_count, "run_index": run_index, "seed": seed,
        "directional_count": directional_count,
        "omnidirectional_count": source_count - directional_count,
        "cleared": cleared,
        "complete": int(cleared == source_count and not error),
        "virtual_time_s": client.time,
        "time_per_source_s": client.time / source_count,
        "actions": client.calls,
        "survey_stops": result.get("survey_stops", ""),
        "optical_fallbacks": result.get("optical_fallbacks", ""),
        "runtime_s": time.perf_counter() - started, "error": error,
    }


def summarize(rows):
    result = []
    for count in SOURCE_COUNTS:
        group = [row for row in rows if row["source_count"] == count]
        complete = [row for row in group if row["complete"]]
        total_time = np.asarray([row["virtual_time_s"] for row in complete])
        per_source = np.asarray([row["time_per_source_s"] for row in complete])
        result.append({
            "source_count": count, "samples": len(group),
            "complete_samples": len(complete),
            "complete_rate": len(complete) / len(group),
            "mean_time_s": float(total_time.mean()),
            "sd_time_s": float(total_time.std(ddof=1)),
            "mean_time_per_source_s": float(per_source.mean()),
            "p95_time_s": float(np.quantile(total_time, 0.95)),
            "mean_directional_sources": float(np.mean(
                [row["directional_count"] for row in group])),
        })
    completed_rows = [row for row in rows if row["complete"]]
    all_time = np.asarray([row["virtual_time_s"] for row in completed_rows])
    all_per_source = np.asarray(
        [row["time_per_source_s"] for row in completed_rows])
    result.append({
        "source_count": "overall", "samples": len(rows),
        "complete_samples": len(completed_rows),
        "complete_rate": len(completed_rows) / len(rows),
        "mean_time_s": float(all_time.mean()),
        "sd_time_s": float(all_time.std(ddof=1)),
        "mean_time_per_source_s": float(all_per_source.mean()),
        "p95_time_s": float(np.quantile(all_time, 0.95)),
        "mean_directional_sources": float(np.mean(
            [row["directional_count"] for row in rows])),
    })
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples-per-count", type=int, default=300)
    parser.add_argument("--seed-base", type=int, default=20260913)
    parser.add_argument("--workers", type=int, default=max(1, min(8, mp.cpu_count())))
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "26GuoSai" / "q4_source_count_refinement")
    args = parser.parse_args()
    if args.samples_per_count < 1:
        raise ValueError("samples-per-count must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    tasks = [
        (count, run, args.seed_base + group * 1_000_000 + run)
        for group, count in enumerate(SOURCE_COUNTS)
        for run in range(args.samples_per_count)
    ]
    started = time.perf_counter()
    total = len(tasks)
    def show_progress(done):
        width = 30
        filled = int(width * done / total)
        bar = "#" * filled + "-" * (width - filled)
        print(f"\r[{bar}] {done}/{total} ({100 * done / total:5.1f}%)",
              end="", flush=True)
    if args.workers == 1:
        rows = []
        for done, task in enumerate(tasks, start=1):
            rows.append(run_one(task))
            show_progress(done)
    else:
        context = mp.get_context("spawn")
        with context.Pool(args.workers) as pool:
            rows = []
            for done, row in enumerate(
                    pool.imap_unordered(run_one, tasks, chunksize=4), start=1):
                rows.append(row)
                show_progress(done)
    print()
    rows.sort(key=lambda row: (row["source_count"], row["seed"]))
    with (args.output_dir / "q4_source_count_runs.csv").open(
            "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = summarize(rows)
    (args.output_dir / "q4_source_count_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    metadata = {
        "design": "fixed-seed Q4 source-count stratified offline validation",
        "source_counts": list(SOURCE_COUNTS),
        "samples_per_source_count": args.samples_per_count,
        "seed_scheme": "seed_base + source_count_group_index * 1000000 + run_index",
        "source_type_design": "Each source is independently omnidirectional or directional with probability 0.5; directional headings are independent uniform[0, 2pi).",
        "positions": "independent area-uniform samples in the radius-1800 m disk",
        "channels": "sampled without replacement from 1..20",
        "reception_radius_m": "independent uniform[1000,1500]",
        "bearing_error_deg": "independent uniform[-1,1], rounded to 0.01 degree",
        "time_statistics_population": "complete runs only",
        "controller_sha256": hashlib.sha256(Q4_PATH.read_bytes()).hexdigest(),
    }
    (args.output_dir / "q4_source_count_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "runs": len(rows), "complete_runs": sum(row["complete"] for row in rows),
        "wall_time_s": time.perf_counter() - started,
        "output_dir": str(args.output_dir), "summary": summary,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    mp.freeze_support()
    main()
