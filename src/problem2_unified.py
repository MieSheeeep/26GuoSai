"""Reproduce the single-bearing candidate family used by the trusted tours.

The two tours share a forward-and-lateral construction, with different
calibrated parameters. This module only evaluates a transparent geometric
example for Problem 2; it does not replace either tour's online decisions.
"""

from __future__ import annotations

import importlib
import json
import math
from typing import Sequence


def candidate_pair(
    first_point: Sequence[float],
    bearing_deg: float,
    projection_min: float,
    projection_max: float,
    forward_fraction: float,
    lateral_distance: float,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return the two sides of the first-bearing follow-up construction."""
    if len(first_point) != 2:
        raise ValueError("first_point must have two coordinates")
    values = (
        *first_point, bearing_deg, projection_min, projection_max,
        forward_fraction, lateral_distance,
    )
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("all inputs must be finite")
    if projection_min < 0 or projection_max < projection_min:
        raise ValueError("invalid source projection interval")
    if not 0 < forward_fraction < 1 or lateral_distance <= 0:
        raise ValueError("forward_fraction and lateral_distance must be positive")

    angle = math.radians(bearing_deg)
    along = (math.cos(angle), math.sin(angle))
    lateral = (-along[1], along[0])
    distance = projection_min + forward_fraction * (
        projection_max - projection_min
    )
    center = (
        float(first_point[0]) + distance * along[0],
        float(first_point[1]) + distance * along[1],
    )
    return (
        (center[0] + lateral_distance * lateral[0],
         center[1] + lateral_distance * lateral[1]),
        (center[0] - lateral_distance * lateral[0],
         center[1] - lateral_distance * lateral[1]),
    )


def example_metrics() -> list[dict[str, float | str | list[float]]]:
    """Evaluate the center/east example with each unchanged trusted policy."""
    import numpy as np

    source = np.array([1000.0, 0.0])  # retrospective check, never an input to selection
    policies = (
        ("Q3", "q3_best_standalone", "BEST_TOUR_CONFIG"),
        ("Q4", "q4_standalone_\u526f\u672c", "Q4_CONFIG"),
    )
    rows: list[dict[str, float | str | list[float]]] = []
    for name, module_name, config_name in policies:
        module = importlib.import_module(module_name)
        config = getattr(module, config_name)
        upper, lower = candidate_pair(
            (0.0, 0.0), 0.0, 0.0, 1500.0,
            config.first_fraction, config.lateral,
        )
        second = np.array(upper)
        second_bearing = math.degrees(math.atan2(
            source[1] - second[1], source[0] - second[0]
        )) % 360.0
        region = module.localization_region((
            (np.array([0.0, 0.0]), 0.0),
            (second, second_bearing),
        ))
        rows.append({
            "policy": name,
            "forward_fraction": config.first_fraction,
            "lateral_m": config.lateral,
            "upper_point_m": list(upper),
            "lower_point_m": list(lower),
            "travel_m": float(np.linalg.norm(second)),
            "travel_s": float(np.linalg.norm(second)) / 5.0,
            "crossing_deg": math.degrees(math.atan2(
                config.lateral, source[0] - second[0]
            )),
            "second_range_m": float(np.linalg.norm(source - second)),
            "two_bearing_diameter_m": module.polygon_diameter(region)[0],
        })
    return rows


if __name__ == "__main__":
    print(json.dumps(example_metrics(), ensure_ascii=False, indent=2))
