import math
import random

import pytest

from src.problem1 import (
    bearing_halfplanes,
    brute_force_polygon_diameter,
    diameter_circle_covers,
    localization_polygon,
    polygon_diameter,
    solve,
)


def rounded_points(points, digits=8):
    return {(round(x, digits), round(y, digits)) for x, y in points}


def test_east_bearing_contains_forward_axis_only():
    planes = bearing_halfplanes((0.0, 0.0), 0.0, 1.0)

    assert all(plane.contains((10.0, 0.0)) for plane in planes)
    assert not all(plane.contains((-10.0, 0.0)) for plane in planes)


def test_bearing_wraps_across_zero_degrees():
    planes = bearing_halfplanes((2.0, -3.0), 359.5, 1.0)
    point_on_true_direction = (
        2.0 + 100.0 * math.cos(math.radians(0.2)),
        -3.0 + 100.0 * math.sin(math.radians(0.2)),
    )

    assert all(plane.contains(point_on_true_direction) for plane in planes)


def test_rejects_nonpositive_error_bound():
    with pytest.raises(ValueError, match="error_deg"):
        bearing_halfplanes((0.0, 0.0), 90.0, 0.0)


def test_four_bearings_recover_diamond():
    observations = [
        ((-2.0, 0.0), 0.0, 45.0),
        ((2.0, 0.0), 180.0, 45.0),
        ((0.0, -2.0), 90.0, 45.0),
        ((0.0, 2.0), 270.0, 45.0),
    ]

    polygon = localization_polygon(observations)

    assert rounded_points(polygon) == {
        (-2.0, 0.0),
        (0.0, -2.0),
        (2.0, 0.0),
        (0.0, 2.0),
    }


def test_true_source_lies_in_polygon_for_consistent_one_degree_readings():
    source = (300.0, 400.0)
    stations = [(-500.0, -200.0), (900.0, -100.0), (0.0, 1000.0)]
    reading_offsets = [0.6, -0.8, 0.4]
    observations = []
    for station, offset in zip(stations, reading_offsets, strict=True):
        true_bearing = math.degrees(
            math.atan2(source[1] - station[1], source[0] - station[0])
        )
        observations.append((station, true_bearing + offset, 1.0))

    polygon = localization_polygon(observations)
    planes = [
        plane
        for station, bearing, error in observations
        for plane in bearing_halfplanes(station, bearing, error)
    ]

    assert len(polygon) >= 3
    assert all(plane.contains(source) for plane in planes)


def test_single_bearing_is_reported_as_unbounded():
    with pytest.raises(ValueError, match="unbounded"):
        localization_polygon([((0.0, 0.0), 45.0, 1.0)])


def test_rectangle_diameter_matches_diagonal():
    polygon = [(0.0, 0.0), (3.0, 0.0), (3.0, 4.0), (0.0, 4.0)]

    diameter, first, second = polygon_diameter(polygon)

    assert diameter == pytest.approx(5.0)
    assert {first, second} in (
        {(0.0, 0.0), (3.0, 4.0)},
        {(3.0, 0.0), (0.0, 4.0)},
    )


def test_diameter_circle_does_not_always_cover_polygon():
    triangle = [(0.0, 0.0), (2.0, 0.0), (1.0, math.sqrt(3.0))]

    covered, center, radius = diameter_circle_covers(triangle)

    assert covered is False
    assert radius == pytest.approx(1.0)
    assert isinstance(center, tuple) and len(center) == 2


def test_diameter_circle_covers_rectangle():
    rectangle = [(0.0, 0.0), (3.0, 0.0), (3.0, 4.0), (0.0, 4.0)]

    covered, center, radius = diameter_circle_covers(rectangle)

    assert covered is True
    assert center == pytest.approx((1.5, 2.0))
    assert radius == pytest.approx(2.5)


def test_rotating_calipers_matches_brute_force_on_random_cyclic_polygons():
    rng = random.Random(20260911)
    for vertex_count in range(3, 25):
        angles = sorted(rng.uniform(0.0, 2.0 * math.pi) for _ in range(vertex_count))
        polygon = [(100.0 * math.cos(a), 100.0 * math.sin(a)) for a in angles]

        fast_distance, _, _ = polygon_diameter(polygon)
        reference_distance, _, _ = brute_force_polygon_diameter(polygon)

        assert fast_distance == pytest.approx(reference_distance, rel=1e-12)


def test_diameter_rejects_fewer_than_two_vertices():
    with pytest.raises(ValueError, match="two vertices"):
        polygon_diameter([(0.0, 0.0)])


def test_solve_returns_complete_result():
    observations = [
        ((-2.0, 0.0), 0.0, 45.0),
        ((2.0, 0.0), 180.0, 45.0),
        ((0.0, -2.0), 90.0, 45.0),
        ((0.0, 2.0), 270.0, 45.0),
    ]

    result = solve(observations)

    assert set(result) == {
        "polygon",
        "diameter",
        "diameter_endpoints",
        "circle",
    }
    assert result["diameter"] == pytest.approx(4.0)
    assert result["circle"]["covers"] is True
