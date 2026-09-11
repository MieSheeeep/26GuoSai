"""B 题问题二：第二检测点候选区域与鲁棒选址。

程序只使用 Python 标准库。连续可行域通过确定性网格与边界采样近似；
报告中的集合定义仍是连续形式。
"""

from __future__ import annotations

import json
import math
from typing import Iterable, Sequence

Point = tuple[float, float]


def _as_point(point: Sequence[float], name: str) -> Point:
    if len(point) != 2:
        raise ValueError(f"{name} must contain exactly two coordinates")
    result = (float(point[0]), float(point[1]))
    if not all(math.isfinite(value) for value in result):
        raise ValueError(f"{name} coordinates must be finite")
    return result


def _distance(first: Point, second: Point) -> float:
    return math.hypot(first[0] - second[0], first[1] - second[1])


def _unit_vector(angle_deg: float) -> Point:
    angle_rad = math.radians(angle_deg)
    return math.cos(angle_rad), math.sin(angle_rad)


def ray_circle_exit_distance(
    start: Sequence[float], bearing_deg: float, radius: float = 1800.0
) -> float:
    """Return the forward distance from an interior point to a centered circle."""

    point = _as_point(start, "start")
    radius = float(radius)
    bearing_deg = float(bearing_deg)
    if not math.isfinite(radius) or radius <= 0.0:
        raise ValueError("radius must be a positive finite number")
    if not math.isfinite(bearing_deg):
        raise ValueError("bearing_deg must be finite")
    squared_norm = point[0] ** 2 + point[1] ** 2
    if squared_norm > radius**2 + 1e-9:
        raise ValueError("start must lie inside the target circle")

    direction = _unit_vector(bearing_deg)
    projection = point[0] * direction[0] + point[1] * direction[1]
    discriminant = projection**2 + radius**2 - squared_norm
    return -projection + math.sqrt(max(0.0, discriminant))


def sample_source_region(
    first_point: Sequence[float],
    bearing_deg: float,
    *,
    error_deg: float = 1.0,
    target_radius: float = 1800.0,
    max_receive_radius: float = 1500.0,
    min_source_distance: float = 20.0,
    angle_samples: int = 9,
    radial_samples: int = 31,
) -> tuple[list[Point], tuple[float, float]]:
    """Sample the source region after the first bearing measurement.

    The lower distance is 20 m because a source no farther than 20 m can be
    optically located immediately and does not require a second bearing.
    """

    first = _as_point(first_point, "first_point")
    bearing_deg = float(bearing_deg)
    error_deg = float(error_deg)
    target_radius = float(target_radius)
    max_receive_radius = float(max_receive_radius)
    min_source_distance = float(min_source_distance)
    if not math.isfinite(bearing_deg):
        raise ValueError("bearing_deg must be finite")
    if not math.isfinite(error_deg) or not 0.0 <= error_deg < 90.0:
        raise ValueError("error_deg must lie in [0, 90)")
    if target_radius <= 0.0 or max_receive_radius <= 0.0:
        raise ValueError("radii must be positive")
    if min_source_distance < 0.0 or min_source_distance >= max_receive_radius:
        raise ValueError("min_source_distance must be below max_receive_radius")
    if angle_samples < 2 or radial_samples < 2:
        raise ValueError("angle_samples and radial_samples must be at least 2")
    if _distance(first, (0.0, 0.0)) > target_radius + 1e-9:
        raise ValueError("first_point must lie inside the target circle")

    samples: list[Point] = []
    maximum_distance = min_source_distance
    for angle_index in range(angle_samples):
        fraction = angle_index / (angle_samples - 1)
        angle = bearing_deg - error_deg + 2.0 * error_deg * fraction
        upper = min(
            max_receive_radius,
            ray_circle_exit_distance(first, angle, target_radius),
        )
        if upper < min_source_distance - 1e-9:
            continue
        maximum_distance = max(maximum_distance, upper)
        direction = _unit_vector(angle)
        for radial_index in range(radial_samples):
            radial_fraction = radial_index / (radial_samples - 1)
            distance = min_source_distance + (upper - min_source_distance) * radial_fraction
            samples.append(
                (
                    first[0] + distance * direction[0],
                    first[1] + distance * direction[1],
                )
            )

    if not samples:
        raise ValueError("the first bearing has no feasible source region")
    return samples, (min_source_distance, maximum_distance)


def crossing_angle_degrees(
    first_point: Sequence[float],
    second_point: Sequence[float],
    source_point: Sequence[float],
) -> float:
    """Return the acute crossing angle of two station-to-source bearings."""

    first = _as_point(first_point, "first_point")
    second = _as_point(second_point, "second_point")
    source = _as_point(source_point, "source_point")
    first_vector = (source[0] - first[0], source[1] - first[1])
    second_vector = (source[0] - second[0], source[1] - second[1])
    first_length = math.hypot(*first_vector)
    second_length = math.hypot(*second_vector)
    if first_length <= 1e-12 or second_length <= 1e-12:
        raise ValueError("a detection point must not coincide with the source")
    cosine = abs(
        (first_vector[0] * second_vector[0] + first_vector[1] * second_vector[1])
        / (first_length * second_length)
    )
    return math.degrees(math.acos(min(1.0, max(0.0, cosine))))


def positioning_error_proxy(
    first_point: Sequence[float],
    second_point: Sequence[float],
    source_point: Sequence[float],
    error_deg: float = 1.0,
) -> float:
    """Estimate the worst linearized position error of a two-bearing cross.

    The conservative proxy is ``(d1 + d2) * tan(error) / sin(angle)``.
    It penalizes long station-source ranges and nearly parallel bearings.
    """

    first = _as_point(first_point, "first_point")
    second = _as_point(second_point, "second_point")
    source = _as_point(source_point, "source_point")
    error_deg = float(error_deg)
    if not math.isfinite(error_deg) or not 0.0 <= error_deg < 90.0:
        raise ValueError("error_deg must lie in [0, 90)")
    angle = crossing_angle_degrees(first, second, source)
    sine = math.sin(math.radians(angle))
    if sine <= 1e-12:
        return math.inf
    return (
        (_distance(first, source) + _distance(second, source))
        * math.tan(math.radians(error_deg))
        / sine
    )


def reception_margin(
    first_point: Sequence[float],
    second_point: Sequence[float],
    source_points: Iterable[Sequence[float]],
    min_receive_radius: float = 1000.0,
) -> float:
    """Return the worst guaranteed reception margin at the second point.

    A first successful detection implies the unknown actual reception radius
    is at least both ``min_receive_radius`` and the first station-source range.
    Nonnegative output therefore guarantees reception for all supplied sources.
    """

    first = _as_point(first_point, "first_point")
    second = _as_point(second_point, "second_point")
    min_receive_radius = float(min_receive_radius)
    if not math.isfinite(min_receive_radius) or min_receive_radius <= 0.0:
        raise ValueError("min_receive_radius must be positive")
    sources = [_as_point(point, "source_point") for point in source_points]
    if not sources:
        raise ValueError("source_points must not be empty")
    return min(
        max(min_receive_radius, _distance(first, source))
        - _distance(second, source)
        for source in sources
    )


def _grid_axis(radius: float, step: float) -> list[float]:
    index_limit = math.floor(radius / step)
    return [index * step for index in range(-index_limit, index_limit + 1)]


def _evaluate_candidate(
    first: Point,
    second: Point,
    sources: list[Point],
    *,
    min_receive_radius: float,
    max_receive_radius: float,
    target_radius: float,
    optical_radius: float,
    error_deg: float,
) -> dict[str, float | Point | bool]:
    margin = reception_margin(first, second, sources, min_receive_radius)
    possible = any(_distance(second, source) <= max_receive_radius + 1e-9 for source in sources)
    angles = []
    error_proxies = []
    for source in sources:
        if _distance(second, source) <= optical_radius:
            angles.append(90.0)
            error_proxies.append(0.0)
        else:
            angles.append(crossing_angle_degrees(first, second, source))
            error_proxies.append(
                positioning_error_proxy(first, second, source, error_deg)
            )
    worst_angle = min(angles)
    worst_error = max(error_proxies)
    move_distance = _distance(first, second)
    margin_term = max(-1.0, min(1.0, margin / min_receive_radius))
    score = (
        0.65 / (1.0 + worst_error / 100.0)
        + 0.35 * math.sin(math.radians(worst_angle))
        + 0.15 * margin_term
        - 0.08 * move_distance / (2.0 * target_radius)
    )
    return {
        "point": second,
        "score": score,
        "worst_crossing_angle_deg": worst_angle,
        "worst_positioning_error": worst_error,
        "reception_margin": margin,
        "move_distance": move_distance,
        "guaranteed": margin >= -1e-9,
        "possible": possible,
    }


def _best_on_each_side(
    candidates: list[dict[str, float | Point | bool]],
    first: Point,
    bearing_deg: float,
) -> list[dict[str, float | Point | bool]]:
    direction = _unit_vector(bearing_deg)
    normal = (-direction[1], direction[0])

    def lateral(candidate: dict[str, float | Point | bool]) -> float:
        point = candidate["point"]
        assert isinstance(point, tuple)
        return (point[0] - first[0]) * normal[0] + (point[1] - first[1]) * normal[1]

    def rank(candidate: dict[str, float | Point | bool]) -> tuple[float, float, float]:
        return (
            round(float(candidate["score"]), 12),
            -float(candidate["move_distance"]),
            abs(lateral(candidate)),
        )

    positive = [candidate for candidate in candidates if lateral(candidate) > 1e-9]
    negative = [candidate for candidate in candidates if lateral(candidate) < -1e-9]
    recommendations: list[dict[str, float | Point | bool]] = []
    if positive:
        recommendations.append(max(positive, key=rank))
    if negative:
        recommendations.append(max(negative, key=rank))
    if len(recommendations) < 2:
        for candidate in sorted(candidates, key=rank, reverse=True):
            if candidate not in recommendations:
                recommendations.append(candidate)
            if len(recommendations) == 2:
                break
    return recommendations


def select_second_detection_points(
    first_point: Sequence[float],
    bearing_deg: float,
    *,
    error_deg: float = 1.0,
    target_radius: float = 1800.0,
    min_receive_radius: float = 1000.0,
    max_receive_radius: float = 1500.0,
    optical_radius: float = 20.0,
    min_baseline: float = 100.0,
    grid_step: float = 100.0,
    angle_samples: int = 9,
    radial_samples: int = 31,
) -> dict[str, object]:
    """Select robust second-detection candidates from both sides of the bearing."""

    first = _as_point(first_point, "first_point")
    numeric_values = {
        "bearing_deg": bearing_deg,
        "error_deg": error_deg,
        "target_radius": target_radius,
        "min_receive_radius": min_receive_radius,
        "max_receive_radius": max_receive_radius,
        "optical_radius": optical_radius,
        "min_baseline": min_baseline,
        "grid_step": grid_step,
    }
    numeric_values = {name: float(value) for name, value in numeric_values.items()}
    if not all(math.isfinite(value) for value in numeric_values.values()):
        raise ValueError("all numeric parameters must be finite")
    if numeric_values["target_radius"] <= 0.0:
        raise ValueError("target_radius must be positive")
    if _distance(first, (0.0, 0.0)) > numeric_values["target_radius"] + 1e-9:
        raise ValueError("first_point must lie inside the target circle")
    if not 0.0 <= numeric_values["error_deg"] < 90.0:
        raise ValueError("error_deg must lie in [0, 90)")
    if numeric_values["min_receive_radius"] <= 0.0:
        raise ValueError("min_receive_radius must be positive")
    if numeric_values["max_receive_radius"] < numeric_values["min_receive_radius"]:
        raise ValueError("max_receive_radius must be at least min_receive_radius")
    if numeric_values["optical_radius"] < 0.0:
        raise ValueError("optical_radius must be nonnegative")
    if numeric_values["min_baseline"] <= 0.0 or numeric_values["grid_step"] <= 0.0:
        raise ValueError("min_baseline and grid_step must be positive")

    sources, distance_interval = sample_source_region(
        first,
        numeric_values["bearing_deg"],
        error_deg=numeric_values["error_deg"],
        target_radius=numeric_values["target_radius"],
        max_receive_radius=numeric_values["max_receive_radius"],
        min_source_distance=max(numeric_values["optical_radius"], 1e-6),
        angle_samples=angle_samples,
        radial_samples=radial_samples,
    )

    all_candidates: list[dict[str, float | Point | bool]] = []
    axis = _grid_axis(numeric_values["target_radius"], numeric_values["grid_step"])
    for x in axis:
        for y in axis:
            second = (x, y)
            if _distance(second, (0.0, 0.0)) > numeric_values["target_radius"] + 1e-9:
                continue
            if _distance(second, first) < numeric_values["min_baseline"] - 1e-9:
                continue
            candidate = _evaluate_candidate(
                first,
                second,
                sources,
                min_receive_radius=numeric_values["min_receive_radius"],
                max_receive_radius=numeric_values["max_receive_radius"],
                target_radius=numeric_values["target_radius"],
                optical_radius=numeric_values["optical_radius"],
                error_deg=numeric_values["error_deg"],
            )
            if candidate["possible"]:
                all_candidates.append(candidate)

    guaranteed = [candidate for candidate in all_candidates if candidate["guaranteed"]]
    pool = guaranteed if guaranteed else all_candidates
    if not pool:
        raise ValueError("no feasible second-detection candidate was found")
    mode = "guaranteed" if guaranteed else "possible"
    recommendations = _best_on_each_side(pool, first, numeric_values["bearing_deg"])
    points = [candidate["point"] for candidate in pool]
    bounds = {
        "min_x": min(point[0] for point in points),
        "max_x": max(point[0] for point in points),
        "min_y": min(point[1] for point in points),
        "max_y": max(point[1] for point in points),
    }

    return {
        "source_distance_interval": distance_interval,
        "source_region_sample_count": len(sources),
        "candidate_mode": mode,
        "candidate_count": len(pool),
        "candidate_bounds": bounds,
        "recommended_points": recommendations,
        "parameters": {
            **numeric_values,
            "angle_samples": angle_samples,
            "radial_samples": radial_samples,
        },
    }


def main() -> None:
    """Run a deterministic example used by the Markdown report."""

    result = select_second_detection_points(
        first_point=(0.0, 0.0),
        bearing_deg=0.0,
        grid_step=100.0,
        angle_samples=9,
        radial_samples=31,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
