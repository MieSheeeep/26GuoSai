"""Geometry algorithms for Problem 1 of the radio-source task."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import json
from math import atan2, cos, degrees, hypot, radians, sin, sqrt
from typing import Iterable, Sequence, TypeAlias

Point: TypeAlias = tuple[float, float]
Observation: TypeAlias = tuple[Point, float] | tuple[Point, float, float]


@dataclass(frozen=True)
class HalfPlane:
    """Closed half-plane ``a*x + b*y <= c``."""

    a: float
    b: float
    c: float

    def contains(self, point: Point, tol: float = 1e-9) -> bool:
        return self.a * point[0] + self.b * point[1] <= self.c + tol


def bearing_halfplanes(
    station: Point, bearing_deg: float, error_deg: float = 1.0
) -> tuple[HalfPlane, HalfPlane]:
    """Return the two half-planes of one bearing-error wedge."""

    if not 0.0 < error_deg < 90.0:
        raise ValueError("error_deg must be between 0 and 90 degrees")

    sx, sy = station
    lower = radians(bearing_deg - error_deg)
    upper = radians(bearing_deg + error_deg)
    ux_lower, uy_lower = cos(lower), sin(lower)
    ux_upper, uy_upper = cos(upper), sin(upper)

    # cross(u_lower, X-S) >= 0
    lower_plane = HalfPlane(
        uy_lower, -ux_lower, uy_lower * sx - ux_lower * sy
    )
    # cross(u_upper, X-S) <= 0
    upper_plane = HalfPlane(
        -uy_upper, ux_upper, -uy_upper * sx + ux_upper * sy
    )
    return lower_plane, upper_plane


def _line_intersection(
    first: HalfPlane, second: HalfPlane, tol: float
) -> Point | None:
    determinant = first.a * second.b - second.a * first.b
    if abs(determinant) <= tol:
        return None
    x = (first.c * second.b - second.c * first.b) / determinant
    y = (first.a * second.c - second.a * first.c) / determinant
    return x, y


def _cross(origin: Point, first: Point, second: Point) -> float:
    return (first[0] - origin[0]) * (second[1] - origin[1]) - (
        first[1] - origin[1]
    ) * (second[0] - origin[0])


def _unique_points(points: Iterable[Point], tol: float) -> list[Point]:
    unique: list[Point] = []
    for point in points:
        if all(hypot(point[0] - q[0], point[1] - q[1]) > tol for q in unique):
            unique.append(point)
    return unique


def _convex_hull(points: Iterable[Point], tol: float) -> list[Point]:
    ordered = sorted(_unique_points(points, tol))
    if len(ordered) <= 1:
        return ordered

    lower: list[Point] = []
    for point in ordered:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], point) <= tol:
            lower.pop()
        lower.append(point)

    upper: list[Point] = []
    for point in reversed(ordered):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], point) <= tol:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def _has_recession_direction(planes: Sequence[HalfPlane], tol: float) -> bool:
    """Whether the common half-planes have a nonzero feasible direction."""

    if not planes:
        return True
    for plane in planes:
        tangent = (plane.b, -plane.a)
        for dx, dy in (tangent, (-tangent[0], -tangent[1])):
            if all(p.a * dx + p.b * dy <= tol for p in planes):
                return True
    return False


def localization_polygon(
    observations: Sequence[Observation], tol: float = 1e-9
) -> list[Point]:
    """Build the bounded convex feasible polygon from bearing observations.

    Each observation is ``(station, bearing_deg)`` or
    ``(station, bearing_deg, error_deg)``. The default error is one degree.
    Vertices are returned counter-clockwise without repeating the first vertex.
    """

    planes: list[HalfPlane] = []
    for observation in observations:
        planes.extend(bearing_halfplanes(*observation))

    if _has_recession_direction(planes, tol):
        raise ValueError("bearing constraints form an unbounded region")

    candidates: list[Point] = []
    for first, second in combinations(planes, 2):
        point = _line_intersection(first, second, tol)
        if point is not None and all(plane.contains(point, tol) for plane in planes):
            candidates.append(point)

    polygon = _convex_hull(candidates, tol)
    if len(polygon) < 3:
        raise ValueError("bearing constraints have an empty or degenerate intersection")
    return polygon


def _squared_distance(first: Point, second: Point) -> float:
    return (first[0] - second[0]) ** 2 + (first[1] - second[1]) ** 2


def brute_force_polygon_diameter(
    vertices: Sequence[Point],
) -> tuple[float, Point, Point]:
    """Reference O(n^2) diameter calculation used for verification."""

    if len(vertices) < 2:
        raise ValueError("a polygon diameter needs at least two vertices")
    best_squared = -1.0
    best_pair = (vertices[0], vertices[1])
    for first, second in combinations(vertices, 2):
        squared = _squared_distance(first, second)
        if squared > best_squared:
            best_squared = squared
            best_pair = first, second
    return sqrt(best_squared), best_pair[0], best_pair[1]


def polygon_diameter(vertices: Sequence[Point]) -> tuple[float, Point, Point]:
    """Return a convex polygon's diameter and endpoints in O(n) time.

    The vertices must follow the polygon boundary, clockwise or
    counter-clockwise, without repeating the first vertex.
    """

    if len(vertices) < 2:
        raise ValueError("a polygon diameter needs at least two vertices")
    if len(vertices) == 2:
        return hypot(
            vertices[0][0] - vertices[1][0], vertices[0][1] - vertices[1][1]
        ), vertices[0], vertices[1]

    polygon = list(vertices)
    signed_twice_area = sum(
        polygon[i][0] * polygon[(i + 1) % len(polygon)][1]
        - polygon[i][1] * polygon[(i + 1) % len(polygon)][0]
        for i in range(len(polygon))
    )
    if signed_twice_area < 0.0:
        polygon.reverse()

    vertex_count = len(polygon)
    opposite = 1
    best_squared = -1.0
    best_pair = (polygon[0], polygon[1])

    for index in range(vertex_count):
        next_index = (index + 1) % vertex_count
        while abs(
            _cross(
                polygon[index],
                polygon[next_index],
                polygon[(opposite + 1) % vertex_count],
            )
        ) > abs(
            _cross(polygon[index], polygon[next_index], polygon[opposite])
        ) + 1e-12:
            opposite = (opposite + 1) % vertex_count

        for first, second in (
            (polygon[index], polygon[opposite]),
            (polygon[next_index], polygon[opposite]),
        ):
            squared = _squared_distance(first, second)
            if squared > best_squared:
                best_squared = squared
                best_pair = first, second

    return sqrt(best_squared), best_pair[0], best_pair[1]


def diameter_circle_covers(
    vertices: Sequence[Point], tol: float = 1e-9
) -> tuple[bool, Point, float]:
    """Check the circle whose diameter is one farthest vertex pair."""

    diameter, first, second = polygon_diameter(vertices)
    center = ((first[0] + second[0]) / 2.0, (first[1] + second[1]) / 2.0)
    radius = diameter / 2.0
    covered = all(
        hypot(vertex[0] - center[0], vertex[1] - center[1]) <= radius + tol
        for vertex in vertices
    )
    return covered, center, radius


def solve(observations: Sequence[Observation]) -> dict[str, object]:
    """Solve Problem 1 for one set of bearing observations."""

    polygon = localization_polygon(observations)
    diameter, first, second = polygon_diameter(polygon)
    covered, center, radius = diameter_circle_covers(polygon)
    return {
        "polygon": polygon,
        "diameter": diameter,
        "diameter_endpoints": (first, second),
        "circle": {"covers": covered, "center": center, "radius": radius},
    }


def _demo_observations() -> list[Observation]:
    """A reproducible three-station example with the prescribed 1-degree error."""

    source = (300.0, 400.0)
    stations = [(-500.0, -200.0), (900.0, -100.0), (0.0, 1000.0)]
    reading_offsets = [0.6, -0.8, 0.4]
    observations: list[Observation] = []
    for station, offset in zip(stations, reading_offsets, strict=True):
        true_bearing = degrees(
            atan2(source[1] - station[1], source[0] - station[0])
        ) % 360.0
        observations.append((station, true_bearing + offset, 1.0))
    return observations


if __name__ == "__main__":
    print(json.dumps(solve(_demo_observations()), ensure_ascii=False, indent=2))
