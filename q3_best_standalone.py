#!/usr/bin/env python3
"""Standalone selected Q3 controller.

Official/practice run:
    python q3_best_standalone.py --robot-id <team-id>

Third-party requirements: numpy, scipy, shapely. No radio_search package or
external configuration file is used at runtime.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from functools import lru_cache
from numbers import Real
from pathlib import Path
import socket
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import numpy as np
from scipy.optimize import minimize
from scipy.spatial import Delaunay
from shapely.geometry import Point, Polygon, MultiPoint
from shapely.ops import unary_union



# ---- radio_search/geometry.py ----

ERROR_DEG = 1.0051  # Conservative allowance for two-decimal output rounding.


def outer_disc(point, radius: float, sides: int = 64):
    angles = np.arange(sides)*2*np.pi/sides
    r = radius/math.cos(np.pi/sides)
    return Polygon(np.array(point) + r*np.column_stack((np.cos(angles), np.sin(angles))))


ARENA = outer_disc((0, 0), 1800, 96)


def bearing_wedge(point, degrees: float):
    a = math.radians(degrees)
    e = math.radians(ERROR_DEG)
    p = np.array(point)
    return Polygon([p, p+6000*np.array([math.cos(a-e), math.sin(a-e)]),
                    p+6000*np.array([math.cos(a+e), math.sin(a+e)])])


def vertices(shape) -> np.ndarray:
    if shape.is_empty:
        return np.empty((0, 2))
    hull = shape.convex_hull
    if hull.geom_type == "Point":
        return np.asarray(hull.coords)
    if hull.geom_type == "LineString":
        return np.asarray(hull.coords)
    return np.asarray(hull.exterior.coords[:-1])


def localization_region(detections):
    """Return the conservative feasible region for positive bearing readings."""
    shape = ARENA
    for point, bearing_deg in detections:
        shape = update_direction(shape, point, bearing_deg)
        if shape.is_empty:
            raise ValueError("Bearing constraints have an empty intersection")
    return shape


def polygon_diameter(shape):
    """Return a convex region's diameter and an attaining vertex pair."""
    points = vertices(shape)
    count = len(points)
    if count == 0:
        raise ValueError("Cannot compute the diameter of an empty region")
    if count == 1:
        return 0., (points[0].copy(), points[0].copy())
    if count == 2:
        return float(np.linalg.norm(points[1]-points[0])), (
            points[0].copy(), points[1].copy())

    def doubled_area(a, b, c):
        ab = b-a
        ac = c-a
        return abs(float(ab[0]*ac[1]-ab[1]*ac[0]))

    best_distance_sq = -1.
    best_pair = None
    opposite = 1
    for index in range(count):
        next_index = (index+1) % count
        while doubled_area(
                points[index], points[next_index],
                points[(opposite+1) % count]) > doubled_area(
                    points[index], points[next_index],
                    points[opposite])+1e-10:
            opposite = (opposite+1) % count
        for left in (index, next_index):
            distance_sq = float(np.sum(
                (points[left]-points[opposite])**2))
            if distance_sq > best_distance_sq:
                best_distance_sq = distance_sq
                best_pair = (
                    points[left].copy(), points[opposite].copy())
    return math.sqrt(best_distance_sq), best_pair


def safe_second_measure_region(shape, resolution=64):
    """Points guaranteed within 1000 m of every source in a convex shape."""
    points = vertices(shape)
    if not len(points):
        raise ValueError("Cannot plan from an empty feasible region")
    candidate = Point(points[0]).buffer(1000, resolution=resolution)
    for point in points[1:]:
        candidate = candidate.intersection(
            Point(point).buffer(1000, resolution=resolution))
        if candidate.is_empty:
            break
    return candidate


def _three_circle(a, b, c):
    ab, ac = b-a, c-a
    det = 2*(ab[0]*ac[1]-ab[1]*ac[0])
    if abs(det) < 1e-10:
        return None
    aa, bb = float(ab@ab), float(ac@ac)
    center = a + np.array([(ac[1]*aa-ab[1]*bb)/det, (ab[0]*bb-ac[0]*aa)/det])
    return center, float(np.linalg.norm(center-a))


def enclosing_circle(shape):
    pts = vertices(shape)
    if not len(pts):
        raise ValueError("Empty feasible set; refusing a false localization certificate")
    pts = pts[np.random.default_rng(41).permutation(len(pts))]
    center, radius = pts[0].copy(), 0.0
    for i, p in enumerate(pts):
        if np.linalg.norm(p-center) <= radius + 1e-7:
            continue
        center, radius = p.copy(), 0.0
        for j in range(i):
            q = pts[j]
            if np.linalg.norm(q-center) <= radius + 1e-7:
                continue
            center, radius = (p+q)/2, float(np.linalg.norm(p-q)/2)
            for k in range(j):
                s = pts[k]
                if np.linalg.norm(s-center) <= radius + 1e-7:
                    continue
                circle = _three_circle(p, q, s)
                if circle is not None:
                    center, radius = circle
                else:
                    trio = [p, q, s]
                    aa, bb = max(((x, y) for x in trio for y in trio), key=lambda z: np.linalg.norm(z[0]-z[1]))
                    center, radius = (aa+bb)/2, float(np.linalg.norm(aa-bb)/2)
    # Independent containment check is important for guaranteed clearing.
    radius = float(np.linalg.norm(pts-center, axis=1).max())
    return center, radius


def nearest_clear_point(shape, current):
    center, radius = enclosing_circle(shape)
    if radius > 19.95:
        return None
    pts = vertices(shape)
    current = np.asarray(current)
    constraint = {"type": "ineq", "fun": lambda x: 19.99**2-np.sum((pts-x)**2, axis=1),
                  "jac": lambda x: 2*(pts-x)}
    res = minimize(lambda x: float(np.sum((x-current)**2)), center,
                   jac=lambda x: 2*(x-current), constraints=constraint, method="SLSQP",
                   options={"maxiter": 40, "ftol": 1e-7})
    if res.success and np.linalg.norm(pts-res.x, axis=1).max() <= 20-1e-5:
        return res.x
    return center


def update_direction(shape, point, degrees):
    return shape.intersection(bearing_wedge(point, degrees)).intersection(outer_disc(point, 1500))


def closer_to_positive_halfplane(positive, negative):
    """Region where a fixed-radius source can be seen at positive but not negative."""
    positive = np.asarray(positive, dtype=float)
    negative = np.asarray(negative, dtype=float)
    normal = negative-positive
    length = float(np.linalg.norm(normal))
    if length < 1e-9:
        return ARENA
    normal /= length
    tangent = np.array([-normal[1], normal[0]])
    midpoint = (positive+negative)/2
    extent = 10000.
    return Polygon([
        midpoint+extent*tangent,
        midpoint-extent*tangent,
        midpoint-extent*tangent-extent*normal,
        midpoint+extent*tangent-extent*normal,
    ])


def sample_shape(shape, count, rng):
    hull = vertices(shape)
    if not len(hull):
        return np.empty((0, 2))
    if len(hull) < 3:
        u = rng.random((count, 1))
        return hull[0]*(1-u)+hull[-1]*u
    # Area-weighted triangles of a convex hull; reject holes/nonconvex exclusions.
    root = hull[0]
    a, b = hull[1:-1]-root, hull[2:]-root
    areas = np.abs(a[:, 0]*b[:, 1]-a[:, 1]*b[:, 0])
    if areas.sum() < 1e-12:
        return np.repeat(np.asarray(shape.representative_point().coords), count, axis=0)
    result = []
    for _ in range(30):
        idx = rng.choice(len(a), max(2*(count-len(result)), 4), p=areas/areas.sum())
        uv = rng.random((len(idx), 2))
        uv[uv.sum(axis=1) > 1] = 1-uv[uv.sum(axis=1) > 1]
        points = root+a[idx]*uv[:, :1]+b[idx]*uv[:, 1:]
        result.extend(p for p in points if shape.covers(Point(p)))
        if len(result) >= count:
            break
    if not result:
        result = [np.array(shape.representative_point().coords[0])]
    while len(result) < count:
        result.append(result[len(result) % len(result)].copy())
    return np.array(result[:count])


def survey_anchors(problem):
    if problem == 3:
        # Nearest site is at most 700*sqrt(2) away. Removed corner Voronoi
        # cells have x,y >=1400 in absolute value, hence miss the 1800m disc.
        grid = [(x, y) for x in (-2100, -700, 700, 2100) for y in (-2100, -700, 700, 2100)
                if not (abs(x) == abs(y) == 2100)]
    else:
        grid = [(700*x, 700*y) for x in range(-3, 4) for y in range(-3, 4)]
    return [np.array(p, dtype=float) for p in [(0, 0)]+[p for p in grid if p != (0, 0)]]


@lru_cache(maxsize=2048)
def coverage_certificate(problem: int, points: tuple):
    if not points:
        return False, 0.0
    if problem == 3:
        # Inscribed discs make this a conservative, never optimistic certificate.
        covered = unary_union([Point(p).buffer(1000, resolution=32) for p in points])
    else:
        if len(points) < 3:
            return False, 0.0
        arr = np.array(points)
        try:
            tri = Delaunay(arr)
        except Exception:
            return False, 0.0
        pieces = []
        for ids in tri.simplices:
            p = arr[ids]
            if max(np.linalg.norm(p[0]-p[1]), np.linalg.norm(p[0]-p[2]), np.linalg.norm(p[1]-p[2])) <= 1000-1e-7:
                # Every point in this triangle is within 1000m of all three
                # vertices and in their convex hull: every closed half-plane
                # through the source contains at least one detecting vertex.
                pieces.append(Polygon(p))
        covered = unary_union(pieces)
    return covered.covers(ARENA), float(covered.intersection(ARENA).area/ARENA.area)


def clear_cover(shape, angle_deg=0):
    angle = math.radians(angle_deg)
    rot = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    pts = vertices(shape) @ rot
    lower, upper = pts.min(axis=0), pts.max(axis=0)
    # 25m square cells have covering radius 17.68m < 20m.
    lo = np.floor(lower/25).astype(int)
    hi = np.floor(upper/25).astype(int)
    result = []
    for i in range(lo[0], hi[0]+1):
        for j in range(lo[1], hi[1]+1):
            p = np.array([(i+.5)*25, (j+.5)*25]) @ rot.T
            if shape.distance(Point(p)) <= 18:
                result.append(p)
    return result


# ---- radio_search/routing.py ----

def open_path_length(start, points, order):
    if not order:
        return 0.
    sequence = np.vstack([start, np.asarray(points)[order]])
    return float(np.linalg.norm(np.diff(sequence, axis=0), axis=1).sum())


def open_route(start, points, optimize=True):
    points = np.asarray(points, dtype=float)
    if not len(points):
        return []
    if points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all():
        raise ValueError("Route sites must be finite 2D points")
    coordinates = np.vstack([np.asarray(start, dtype=float), points])
    distances = np.linalg.norm(coordinates[:, None, :]-coordinates[None, :, :], axis=2)
    remaining = list(range(1, len(points)+1))
    route, previous = [], 0
    while remaining:
        next_index = min(remaining, key=lambda i: (distances[previous, i], i))
        route.append(next_index)
        remaining.remove(next_index)
        previous = next_index
    if optimize:
        for _ in range(30):
            best_delta, best_pair = -1e-8, None
            for i in range(len(route)-1):
                before = route[i-1] if i else 0
                for j in range(i+1, len(route)):
                    delta = distances[before, route[j]]-distances[before, route[i]]
                    if j+1 < len(route):
                        after = route[j+1]
                        delta += distances[route[i], after]-distances[route[j], after]
                    if delta < best_delta:
                        best_delta, best_pair = delta, (i, j)
            if best_pair is None:
                break
            i, j = best_pair
            route[i:j+1] = reversed(route[i:j+1])
    return [i-1 for i in route]


# ---- radio_search/adaptive_tour.py ----

@dataclass
class TourConfig:
    scan_area: float = 180000.0
    optimistic_radius: float = 65.0
    first_fraction: float = 0.25
    lateral: float = 95.0
    share_sine: float = 0.35
    share_range: float = 1200.0
    share_baseline: float = 160.0
    cover_power: float = 1.0
    scan_price: float = 1.0
    retain_cover: bool = True
    relax_cover: bool = True
    ring_candidates: bool = True
    anneal_steps: int = 2000
    intermediate_scan: bool = False
    intermediate_share: bool = False
    q4_rings: bool = True
    q4_dynamic_prune: bool = False
    q4_outer_radius: float = 1880.
    q4_inner_radius: float = 940.
    q4_inner_phase: float = 0.
    q4_outer_count: int = 18
    q4_inner_count: int = 12
    q4_include_center: bool = True
    local_onward_weight: float = .15
    max_local_actions: int = 10
    max_actions: int = 5500

    def __post_init__(self):
        for name, value in vars(self).items():
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"Invalid {name}")
        if not 0 <= self.first_fraction <= 1 or not 0 <= self.share_sine <= 1:
            raise ValueError("Fractions must be in [0, 1]")
        if not isinstance(self.q4_dynamic_prune, bool):
            raise ValueError("q4_dynamic_prune must be boolean")
        if not isinstance(self.q4_include_center, bool):
            raise ValueError("q4_include_center must be boolean")
        for name in ("q4_outer_count", "q4_inner_count"):
            value = getattr(self, name)
            if (isinstance(value, bool) or not isinstance(value, int)
                    or value < 3):
                raise ValueError(f"{name} must be an integer >= 3")
        if self.lateral <= 0 or self.max_local_actions < 1 or self.max_actions < 1:
            raise ValueError("Positive action budgets and lateral distance required")


@dataclass
class Track:
    channel: int
    shape: object = field(default_factory=lambda: ARENA)
    positives: list = field(default_factory=list)
    negatives: list = field(default_factory=list)
    cleared: bool = False
    known: bool = False
    attempts: int = 0

    def estimate(self):
        if self.shape.is_empty:
            raise RuntimeError("Inconsistent observations: empty feasible region")
        if len(self.positives) >= 2:
            normals, offsets = [], []
            for p, angle in self.positives:
                if angle is None:
                    return p.copy()
                a = math.radians(angle)
                normal = np.array([-math.sin(a), math.cos(a)])
                normals.append(normal)
                offsets.append(float(normal @ p))
            center = np.linalg.lstsq(normals, offsets, rcond=None)[0]
            if self.shape.covers(Point(center)):
                return center
        return np.asarray(self.shape.centroid.coords[0])


def _components(shape):
    if shape.is_empty:
        return []
    return list(shape.geoms) if hasattr(shape, "geoms") else [shape]


def annealed_route(start, points, steps=2000):
    """Bounded, reproducible 2-opt annealing; never worse than the incumbent."""
    points = np.asarray(points, dtype=float)
    initial = open_route(start, points)
    if len(points) < 3 or not steps:
        return initial
    coords = np.vstack([start, points])
    distance = np.linalg.norm(coords[:, None]-coords[None, :], axis=2)
    route = [i+1 for i in initial]
    cost = sum(distance[a, b] for a, b in zip([0]+route[:-1], route))
    best, best_cost = route.copy(), cost
    rng = np.random.default_rng(314159)
    pairs = rng.integers(0, len(points), (steps, 2))
    thresholds = rng.random(steps)
    for k, (i, j) in enumerate(pairs):
        if i == j:
            continue
        if i > j:
            i, j = j, i
        before = route[i-1] if i else 0
        delta = distance[before, route[j]]-distance[before, route[i]]
        if j+1 < len(route):
            delta += distance[route[i], route[j+1]]-distance[route[j], route[j+1]]
        temperature = 150*(1-(k % max(1, steps//4))/max(1, steps//4))**3+1
        if delta <= 0 or thresholds[k] < math.exp(-delta/temperature):
            route[i:j+1] = reversed(route[i:j+1])
            cost += delta
            if cost < best_cost-1e-7:
                best, best_cost = route.copy(), cost
    return [i-1 for i in best]


class AdaptiveTour:
    def __init__(self, client, problem=3, config=None):
        if problem not in (3, 4):
            raise ValueError("problem must be 3 or 4")
        self.client, self.problem = client, problem
        self.config = config or TourConfig()
        self.tracks = [Track(c) for c in range(1, 21)]
        self.survey = []
        self.covered = Polygon()
        self.actions = 0
        self.planning_ms = []
        self.fallbacks = 0
        self.decisions = []
        self.cover_plan = []
        self._q4_prune_history = None
        self._q4_pruned_candidates = None
        angles = np.arange(36)*2*np.pi/36
        self.cover_candidates = np.vstack([
            np.zeros((1, 2)),
            *[r*np.column_stack([np.cos(angles), np.sin(angles)])
              for r in (850., 1200., 1450., 1750.)],
        ])
        if self.config.ring_candidates:
            self.cover_candidates = np.vstack([
                r*np.column_stack([np.cos(angles), np.sin(angles)])
                for r in (1200., 1450.)])
        if problem == 4:
            # Spacing 650 gives triangles with every edge < 1000. Retaining
            # a surrounding lattice ring provides a finite discovery fallback.
            self.cover_candidates = np.array([
                [650*(i+.5*(j % 2)), 650*math.sqrt(3)/2*j]
                for i in range(-4, 5) for j in range(-4, 5)
                if np.linalg.norm([650*(i+.5*(j % 2)),
                                   650*math.sqrt(3)/2*j]) <= 2600
            ])
            if self.config.q4_rings:
                outer = np.arange(self.config.q4_outer_count)*2*np.pi/self.config.q4_outer_count
                inner = (self.config.q4_inner_phase
                         + np.arange(self.config.q4_inner_count)*2*np.pi/self.config.q4_inner_count)
                parts = [
                    self.config.q4_outer_radius*np.column_stack([
                        np.cos(outer), np.sin(outer)]),
                    self.config.q4_inner_radius*np.column_stack([
                        np.cos(inner), np.sin(inner)]),
                ]
                if self.config.q4_include_center:
                    parts.insert(0, np.zeros((1, 2)))
                self.cover_candidates = np.vstack(parts)
                if not discovery_certificate(4, tuple(map(tuple, self.cover_candidates)),
                                             "local_hull")[0]:
                    raise RuntimeError("Q4 ring layout lacks a coverage proof")

    @property
    def known(self):
        return [t for t in self.tracks if t.known and not t.cleared]

    @property
    def unseen(self):
        return [t for t in self.tracks if not t.known]

    def _call(self, path, point, channel):
        if self.actions >= self.config.max_actions:
            raise RuntimeError("Action budget reached without a certificate")
        if time.monotonic() >= self.client.deadline:
            raise RuntimeError("Real deadline reached without a certificate")
        result = self.client.call(path, point, channel)
        self.actions += 1
        return result

    def measure(self, track, point):
        point = np.asarray(point, dtype=float)
        result = self._call("/measure", point, track.channel)
        kind = result["measure_result"]
        if kind == "no_signal":
            track.negatives.append(point.copy())
            if self.problem == 3:
                track.shape = track.shape.difference(Point(point).buffer(1000, quad_segs=48))
                for positive, _ in track.positives:
                    track.shape = track.shape.intersection(
                        closer_to_positive_halfplane(positive, point))
        else:
            track.known = True
            angle = result.get("svd_deg")
            track.positives.append((point.copy(), angle))
            if kind == "near":
                track.shape = track.shape.intersection(outer_disc(point, 5))
            else:
                track.shape = update_direction(track.shape, point, angle)
            if self.problem == 3:
                for negative in track.negatives:
                    track.shape = track.shape.intersection(
                        closer_to_positive_halfplane(point, negative))
        if track.known and track.shape.is_empty:
            raise RuntimeError(f"Empty belief for known channel {track.channel}")
        return kind

    def clear(self, track, point):
        result = self._call("/clear", point, track.channel)
        if result["clear_result"] == "success":
            track.cleared = True
            return True
        track.shape = track.shape.difference(Point(point).buffer(20, quad_segs=32))
        track.attempts += 1
        return False

    def _needs_discovery(self):
        return (bool(self.unseen)
                and sum(t.known for t in self.tracks) < 16
                and not self.covered.covers(ARENA))

    def scan(self, point, force=False):
        if not self._needs_discovery():
            return False
        point = np.asarray(point, dtype=float)
        if any(np.linalg.norm(point-p) < 1e-5 for p in self.survey):
            return False
        if self.problem == 4 and not force:
            if any(np.linalg.norm(point-p) < 450 for p in self.survey):
                return False
        disk = Point(point).buffer(1000, quad_segs=48)
        if not force and self.problem == 3:
            gain = ARENA.difference(self.covered).intersection(disk).area
            if gain < self.config.scan_area:
                return False
        for track in sorted(self.unseen, key=lambda t: (t.channel != self.client.channel, t.channel)):
            self.measure(track, point)
        self.survey.append(point.copy())
        if self.problem == 3:
            self.covered = self.covered.union(disk)
        else:
            history = tuple(tuple(p) for p in self.survey)
            self.covered = self.covered.union(local_hull_region(history))
            if not self.covered.covers(ARENA) and discovery_certificate(
                    4, history, "local_hull")[0]:
                self.covered = self.covered.union(ARENA)
        return True

    def share(self, point, skip=None):
        point = np.asarray(point, dtype=float)
        for track in self.known:
            if track is skip:
                continue
            center = track.estimate()
            delta = center-point
            distance = float(np.linalg.norm(delta))
            if not 25 < distance < self.config.share_range:
                continue
            old = [p for p, a in track.positives if a is not None]
            if not old or min(np.linalg.norm(point-p) for p in old) < self.config.share_baseline:
                continue
            sine = max(abs((center-p)[0]*delta[1]-(center-p)[1]*delta[0])
                       /max(np.linalg.norm(center-p)*distance, 1e-9) for p in old)
            if sine < self.config.share_sine:
                continue
            _, radius = enclosing_circle(track.shape)
            if radius > 20:
                self.measure(track, point)

    def _cover_plan_q3(self, source_points):
        remaining = ARENA.difference(self.covered)
        if not len(source_points):
            planned = []
        else:
            planned = [p.copy() for p in source_points]
            remaining = remaining.difference(unary_union([
                Point(p).buffer(990, quad_segs=24) for p in source_points]))
        extras = []
        if self.config.retain_cover:
            for point in self.cover_plan:
                if not any(np.linalg.norm(point-p) < 1e-5 for p in self.survey):
                    extras.append(point.copy())
                    remaining = remaining.difference(Point(point).buffer(990, quad_segs=24))
        candidates = list(self.cover_candidates)
        price = 30*len(self.unseen)*self.config.scan_price
        for _ in range(25):
            if remaining.is_empty:
                break
            # Exact residual components, including tiny boundary slivers, must
            # be covered; discretization is never a stopping certificate.
            for component in _components(remaining):
                center, radius = enclosing_circle(component)
                if radius <= 990:
                    candidates.append(center)
            route_points = np.array(planned+extras).reshape((-1, 2))
            route_order = open_route(self.client.position, route_points)
            route = np.vstack([self.client.position, route_points[route_order]])
            best = None
            for p in candidates:
                disk = Point(p).buffer(990, quad_segs=24)
                gain = float(remaining.intersection(disk).area)
                if gain <= 0:
                    continue
                if len(route) > 1:
                    detour = min(
                        float((np.linalg.norm(route[:-1]-p, axis=1)
                               + np.linalg.norm(route[1:]-p, axis=1)
                               - np.linalg.norm(np.diff(route, axis=0), axis=1)).min()),
                        float(np.linalg.norm(route[-1]-p)))
                else:
                    detour = float(np.linalg.norm(p-self.client.position))
                score = gain/max(1., price+detour)**self.config.cover_power
                if best is None or score > best[0]:
                    best = score, p, disk
            if best is None:
                raise RuntimeError("Unable to construct a covering continuation")
            _, point, disk = best
            extras.append(np.array(point))
            remaining = remaining.difference(disk)
        if not remaining.is_empty:
            raise RuntimeError("Cover planning iteration limit")
        base = ARENA.difference(self.covered)
        if planned:
            base = base.difference(unary_union([
                Point(p).buffer(990, quad_segs=24) for p in planned]))
        for i in range(len(extras)-1, -1, -1):
            others = [Point(p).buffer(990, quad_segs=24)
                      for j, p in enumerate(extras) if i != j]
            if base.difference(unary_union(others)).is_empty:
                extras.pop(i)
        if self.config.relax_cover and extras:
            extras = self._relax_cover(base, planned, extras)
        self.cover_plan = [p.copy() for p in extras]
        return extras

    def _relax_cover(self, region, planned, extras):
        """Convex visit-point optimization with fixed Voronoi responsibilities."""
        responsibility = []
        for i, point in enumerate(extras):
            cell = region
            for j, other in enumerate(extras):
                if i != j:
                    cell = cell.intersection(closer_to_positive_halfplane(point, other))
            responsibility.append(vertices(cell))
        all_points = np.array(planned+extras)
        order = open_route(self.client.position, all_points)
        n = len(planned)
        def objective(flat):
            points = all_points.copy()
            points[n:] = flat.reshape((-1, 2))
            route = np.vstack([self.client.position, points[order]])
            delta = np.diff(route, axis=0)
            lengths = np.linalg.norm(delta, axis=1)
            directions = delta/np.maximum(lengths[:, None], 1e-9)
            gradient = directions.copy()
            gradient[:-1] -= directions[1:]
            unsorted = np.zeros_like(points)
            unsorted[order] = gradient
            return float(lengths.sum()), unsorted[n:].ravel()
        constraints = []
        for i, pts in enumerate(responsibility):
            if not len(pts):
                continue
            def value(flat, i=i, pts=pts):
                return (995**2-np.sum((flat.reshape((-1, 2))[i]-pts)**2, axis=1))/1e6
            def jac(flat, i=i, pts=pts):
                result = np.zeros((len(pts), len(extras)*2))
                result[:, i*2:i*2+2] = 2*(pts-flat.reshape((-1, 2))[i])/1e6
                return result
            constraints.append({"type": "ineq", "fun": value, "jac": jac})
        initial = np.array(extras).ravel()
        result = minimize(objective, initial, jac=True, constraints=constraints,
                          method="SLSQP", options={"ftol": .01, "maxiter": 60})
        if (np.isfinite(result.x).all()
                and objective(result.x)[0] <= objective(initial)[0]
                and all(np.min(c["fun"](result.x)) >= -1e-9 for c in constraints)):
            return list(result.x.reshape((-1, 2)))
        return extras

    def _cover_plan_q4(self, source_points):
        # Missing sites remain mandatory until actual observations certify the
        # arena. Expected future source visits are never a stopping proof.
        history = [p.copy() for p in self.survey]
        candidates = [p for p in self.cover_candidates
                      if not any(np.linalg.norm(p-q) < 1e-5 for q in history)]
        if self.config.q4_dynamic_prune:
            key = tuple(sorted(tuple(map(float, p)) for p in history))
            if key != self._q4_prune_history:
                # A history point earns credit only because scan() measured
                # every still-unseen channel there. Remove a fixed stop only
                # when the combined, actually measured history and remaining
                # stops retain the continuous all-orientation certificate.
                kept = [p.copy() for p in candidates]
                changed = True
                while changed:
                    changed = False
                    for index in sorted(
                            range(len(kept)),
                            key=lambda i: -float(np.linalg.norm(
                                kept[i]-self.client.position))):
                        trial = kept[:index]+kept[index+1:]
                        sites = tuple(tuple(map(float, p)) for p in history+trial)
                        if discovery_certificate(4, sites, "local_hull")[0]:
                            kept = trial
                            changed = True
                            break
                self._q4_prune_history = key
                self._q4_pruned_candidates = kept
            candidates = [p.copy() for p in self._q4_pruned_candidates]
        if not candidates:
            if discovery_certificate(
                    4, tuple(tuple(map(float, p)) for p in history), "local_hull")[0]:
                return []
            raise RuntimeError("Q4 layout exhausted without discovery certificate")
        route = open_route(self.client.position, np.array(candidates))
        return [candidates[i] for i in route]

    def _local_point(self, track):
        center, radius = enclosing_circle(track.shape)
        estimate = track.estimate()
        current = self.client.position
        if len(track.positives) == 1 and track.positives[0][1] is not None:
            origin, angle = track.positives[0]
            a = math.radians(angle)
            along = np.array([math.cos(a), math.sin(a)])
            perpendicular = np.array([-along[1], along[0]])
            projections = (vertices(track.shape)-origin) @ along
            distance = float(projections.min()
                             + self.config.first_fraction*np.ptp(projections))
            candidates = [origin+distance*along+sign*self.config.lateral*perpendicular
                          for sign in (-1, 1)]
        else:
            vector = estimate-current
            distance = np.linalg.norm(vector)
            along = vector/max(distance, 1e-9)
            perpendicular = np.array([-along[1], along[0]])
            offset = min(self.config.lateral, max(25., radius*.7))
            candidates = [estimate+sign*offset*perpendicular for sign in (-1, 1)]
        others = [t.estimate() for t in self.known if t is not track]
        def cost(p):
            onward = min((np.linalg.norm(p-q) for q in others), default=0.)
            return np.linalg.norm(p-current)+self.config.local_onward_weight*onward
        return min(candidates, key=cost)

    def localize(self, track, action_limit=None, first_point=None):
        limit = self.config.max_local_actions if action_limit is None else min(
            self.config.max_local_actions, action_limit)
        for _ in range(limit):
            if track.cleared:
                return
            center, radius = enclosing_circle(track.shape)
            if radius <= 19.95:
                point = nearest_clear_point(track.shape, self.client.position)
                if self.clear(track, point):
                    self.scan(self.client.position)
                    self.share(self.client.position)
                    return
            elif radius <= self.config.optimistic_radius and track.attempts < 2:
                if self.clear(track, track.estimate()):
                    self.scan(self.client.position)
                    self.share(self.client.position)
                    return
                self.measure(track, self.client.position)
            else:
                if first_point is None:
                    point = self._local_point(track)
                else:
                    point = np.asarray(first_point, dtype=float)
                    first_point = None
                if self.problem == 4 and track.negatives and track.positives:
                    positive = track.positives[-1][0]
                    axis = track.estimate()-positive
                    axis /= max(np.linalg.norm(axis), 1e-9)
                    delta = point-positive
                    reflected = positive+2*(delta @ axis)*axis-delta
                    candidates = [point, reflected]
                    point = max(candidates, key=lambda p: min(
                        np.linalg.norm(p-q) for q in track.negatives))
                self.measure(track, point)
            if self.config.intermediate_scan:
                self.scan(self.client.position)
            if self.config.intermediate_share:
                self.share(self.client.position, skip=track)
        if action_limit is not None and not track.cleared:
            return
        self.fallbacks += 1
        angle = next((a for _, a in track.positives if a is not None), 0.)
        sites = clear_cover(track.shape, angle)
        while sites and not track.cleared:
            i = min(range(len(sites)), key=lambda j: np.linalg.norm(sites[j]-self.client.position))
            point = sites.pop(i)
            if track.shape.distance(Point(point)) <= 20:
                self.clear(track, point)
        if not track.cleared:
            raise RuntimeError("Finite optical cover failed")
        self.scan(self.client.position)
        self.share(self.client.position)

    def run(self):
        self.client.call("/enter")
        self.scan(self.client.position, force=True)
        while self.known or self._needs_discovery():
            start = time.perf_counter()
            known = self.known
            points = [t.estimate() for t in known]
            extras = []
            if self._needs_discovery():
                extras = (self._cover_plan_q3(points) if self.problem == 3
                          else self._cover_plan_q4(points))
            points += extras
            if not points:
                raise RuntimeError("No task without a completion certificate")
            order = annealed_route(self.client.position, np.asarray(points),
                                   self.config.anneal_steps)
            index = order[0]
            self.planning_ms.append((time.perf_counter()-start)*1000)
            if index < len(known):
                self.decisions.append({"task": "source", "channel": known[index].channel})
                self.localize(known[index])
            else:
                self.decisions.append({"task": "survey", "point": np.asarray(points[index]).tolist()})
                self.scan(points[index], force=True)
                self.share(self.client.position)
        certificate = (sum(t.cleared for t in self.tracks) == 16
                       or (not self.known and self.covered.covers(ARENA)))
        if not certificate:
            raise RuntimeError("Refusing exit without a completion certificate")
        self.client.call("/exit")
        return {
            "completion_certificate": certificate,
            "survey_stops": len(self.survey),
            "optical_fallbacks": self.fallbacks,
            "mean_planning_ms": float(np.mean(self.planning_ms)) if self.planning_ms else 0.,
            "max_planning_ms": max(self.planning_ms, default=0.),
        }


# ---- radio_search/q3_portfolio.py ----

@dataclass
class PortfolioConfig:
    layout: str = "ring"
    mode: str = "route"
    ring_radius: float = 1200.
    ring_count: int = 6
    angle: float = 0.
    rotate_initial: bool = False
    relax: bool = False
    scan_sources: bool = False
    replace_anchors: bool = False
    scan_intermediate: bool = False
    info_weight: float = 0.
    discovery_weight: float = 0.
    sweep_slack: float = .35
    rollout_samples: int = 0
    linear_weights: list | None = None
    commitment: int = 0
    source_task_point: str = "center"
    joint_share_weight: float = 0.
    relax_iterations: int = 1
    survey_share_bonus: float = 0.

    def __post_init__(self):
        if self.layout not in ("ring", "adaptive"):
            raise ValueError("Unsupported layout")
        if self.mode not in ("route", "nearest", "sweep", "lookahead", "linear", "neural"):
            raise ValueError("Unsupported mode")
        if self.ring_count < 6 or not 1100 <= self.ring_radius <= 1700:
            raise ValueError("Invalid ring")
        if (self.rollout_samples < 0 or not math.isfinite(self.info_weight)
                or not math.isfinite(self.discovery_weight)
                or not math.isfinite(self.joint_share_weight)
                or not math.isfinite(self.survey_share_bonus)
                or self.joint_share_weight < 0
                or self.survey_share_bonus < 0):
            raise ValueError("Invalid rollout settings")
        if self.commitment < 0:
            raise ValueError("Invalid commitment")
        if (isinstance(self.relax_iterations, bool)
                or not isinstance(self.relax_iterations, int)
                or not 1 <= self.relax_iterations <= 8):
            raise ValueError("Invalid relaxation iterations")
        if self.source_task_point not in ("center", "action"):
            raise ValueError("Invalid source task point")


FEATURES = (
    "source", "distance", "uncertainty", "neighbors", "coverage_gain",
    "bearing_information", "route_cost", "nearest_next", "cleared",
    "known", "unseen", "covered", "angular_forward", "ready",
    "local_cost", "first_on_route",
)


class PortfolioTour(AdaptiveTour):
    """The policy sees observable beliefs only, never the simulator or its seed."""

    def __init__(
            self, client, tour_config=None, portfolio=None, selector=None,
            replacement_selector=None, share_selector=None):
        super().__init__(client, 3, tour_config or TourConfig())
        self.portfolio = portfolio or PortfolioConfig()
        self.selector = selector
        self.replacement_selector = replacement_selector
        self.share_selector = share_selector
        self.anchors = None
        self.sweep_angle = self.portfolio.angle
        self.features_seen = []
        self.selected_indices = []
        self.replacement_features_seen = []
        self.replacement_actions = []
        self.share_features_seen = []
        self.share_actions = []
        self.rng = np.random.default_rng(601)

    def scan(self, point, force=False):
        replaced = False
        if not force:
            if not self._needs_discovery():
                return False
            if self.portfolio.replace_anchors and self.anchors is not None:
                point = np.asarray(point, dtype=float)
                if any(np.linalg.norm(point-p) < 1e-5 for p in self.survey):
                    return False
                kept = [p.copy() for p in self.anchors
                        if not any(np.linalg.norm(p-q) < 1e-5 for q in self.survey)]
                disks = [Point(p).buffer(999, quad_segs=48)
                         for p in self.survey+[point]+kept]
                if not unary_union(disks).covers(ARENA):
                    return False
                removed = []
                # Prefer removing anchors whose inclusion causes the largest
                # open-route detour from the current observable task set.
                while kept:
                    feasible = []
                    for index, anchor in enumerate(kept):
                        trial = kept[:index]+kept[index+1:]
                        cover = unary_union([
                            Point(p).buffer(999, quad_segs=48)
                            for p in self.survey+[point]+trial])
                        if cover.covers(ARENA):
                            route_points = np.asarray(trial).reshape((-1, 2))
                            remaining_length = open_path_length(
                                point, route_points, open_route(point, route_points))
                            feasible.append((remaining_length, index))
                    if not feasible:
                        break
                    _, index = min(feasible)
                    removed.append(kept.pop(index))
                if not removed:
                    return False
                base_points = np.asarray(kept+removed).reshape((-1, 2))
                kept_points = np.asarray(kept).reshape((-1, 2))
                before = open_path_length(
                    point, base_points, open_route(point, base_points))
                after = open_path_length(
                    point, kept_points, open_route(point, kept_points))
                features = np.asarray([
                    (before-after)/3000,
                    (6*len(self.unseen))/120,
                    len(removed)/6,
                    len(self.unseen)/20,
                    sum(track.known for track in self.tracks)/16,
                    self.covered.intersection(ARENA).area/ARENA.area,
                    len(self.survey)/7,
                    after/10000,
                ], dtype=np.float32)
                accept = (True if self.replacement_selector is None else
                          bool(self.replacement_selector(features)))
                self.replacement_features_seen.append(features.copy())
                self.replacement_actions.append(int(accept))
                if not accept:
                    return False
                self.anchors = [
                    p for p in self.anchors
                    if not any(np.linalg.norm(p-r) < 1e-5 for r in removed)
                ]
                replaced = True
            elif not self.portfolio.scan_sources:
                return False
        # A certified substitution is intentionally independent of the generic
        # area-gain threshold: it replaces an already mandatory full scan.
        result = super().scan(point, force or replaced)
        if result and self.anchors is not None:
            self.prune_anchors()
        return result

    def make_anchors(self):
        cfg = self.portfolio
        angle = cfg.angle
        if cfg.rotate_initial and self.known:
            centers = np.array([t.estimate() for t in self.known])
            directions = np.linspace(0, 2*np.pi/cfg.ring_count, 12, endpoint=False)
            candidates = []
            for rotation in directions:
                a = rotation+np.arange(cfg.ring_count)*2*np.pi/cfg.ring_count
                pts = cfg.ring_radius*np.column_stack([np.cos(a), np.sin(a)])
                combined = np.vstack([centers, pts])
                length = open_path_length(self.client.position, combined,
                                          open_route(self.client.position, combined))
                candidates.append((length, rotation))
            angle = min(candidates)[1]
        a = angle+np.arange(cfg.ring_count)*2*np.pi/cfg.ring_count
        self.anchors = list(cfg.ring_radius*np.column_stack([np.cos(a), np.sin(a)]))
        coverage = unary_union([Point(p).buffer(999, quad_segs=48)
                                for p in [np.zeros(2)]+self.anchors])
        if not coverage.covers(ARENA):
            raise ValueError("Ring does not certify arena coverage")
        self.sweep_angle = angle

    def tasks(self):
        known = self.known
        centers = []
        for track in known:
            if self.portfolio.source_task_point == "center":
                point = track.estimate()
            else:
                _, radius = enclosing_circle(track.shape)
                if radius <= self.config.optimistic_radius and track.attempts < 2:
                    point = track.estimate()
                else:
                    point = self._local_point(track)
            centers.append(point)
        extras = []
        if self._needs_discovery():
            if self.portfolio.layout == "adaptive":
                extras = self._cover_plan_q3(centers)
            else:
                extras = [p.copy() for p in self.anchors
                          if not any(np.linalg.norm(p-q) < 1e-5 for q in self.survey)]
                if self.portfolio.relax and extras:
                    remainder = ARENA.difference(self.covered)
                    for _ in range(self.portfolio.relax_iterations):
                        extras = self._relax_cover(remainder, centers, extras)
                    self.anchors = [p.copy() for p in extras]
        return known, np.asarray(centers+extras).reshape((-1, 2))

    def prune_anchors(self):
        if self.anchors is None:
            return
        # Only actual accepted survey locations participate in the proof.
        for anchor in list(self.anchors):
            if any(np.linalg.norm(anchor-q) < 1e-5 for q in self.survey):
                continue
            remaining = [p for p in self.anchors
                         if np.linalg.norm(p-anchor) >= 1e-5
                         and not any(np.linalg.norm(p-q) < 1e-5 for q in self.survey)]
            cover = unary_union([Point(p).buffer(999, quad_segs=48)
                                 for p in self.survey+remaining])
            if cover.covers(ARENA):
                self.anchors = [p for p in self.anchors
                                if np.linalg.norm(p-anchor) >= 1e-5]

    def _share_value(self, point, skip):
        """Observable value of bearings that share can actually collect."""
        value = 0.
        for track in self.known:
            if track is skip:
                continue
            center = track.estimate()
            delta = center-point
            distance = float(np.linalg.norm(delta))
            if not 25 < distance < self.config.share_range:
                continue
            old = [p for p, angle in track.positives if angle is not None]
            if not old or min(np.linalg.norm(point-p) for p in old) < self.config.share_baseline:
                continue
            sine = max(abs((center-p)[0]*delta[1]-(center-p)[1]*delta[0])
                       / max(np.linalg.norm(center-p)*distance, 1e-9) for p in old)
            if sine < self.config.share_sine:
                continue
            _, radius = enclosing_circle(track.shape)
            if radius > 20:
                value += min(radius/200., 2.)*sine
        return value

    def share(self, point, skip=None):
        if self.share_selector is None:
            return super().share(point, skip)
        point = np.asarray(point, dtype=float)
        for track in self.known:
            if track is skip:
                continue
            center = track.estimate()
            delta = center-point
            distance = float(np.linalg.norm(delta))
            if not 25 < distance < self.config.share_range:
                continue
            old = [p for p, angle in track.positives if angle is not None]
            if not old:
                continue
            baseline = min(np.linalg.norm(point-p) for p in old)
            if baseline < self.config.share_baseline:
                continue
            sine = max(
                abs((center-p)[0]*delta[1]-(center-p)[1]*delta[0])
                / max(np.linalg.norm(center-p)*distance, 1e-9) for p in old)
            if sine < self.config.share_sine:
                continue
            _, radius = enclosing_circle(track.shape)
            if radius <= 20:
                continue
            features = np.asarray([
                min(radius, 1000)/1000,
                sine,
                distance/1500,
                min(baseline, 1500)/1500,
                min(len(track.positives), 6)/6,
                min(track.attempts, 3)/3,
                len(self.known)/16,
                len(self.unseen)/20,
                self.covered.intersection(ARENA).area/ARENA.area,
                float(skip is not None),
                float(track.channel == self.client.channel),
                sum(item.known for item in self.tracks)/16,
            ], dtype=np.float32)
            accept = bool(self.share_selector(features))
            self.share_features_seen.append(features.copy())
            self.share_actions.append(int(accept))
            if accept:
                self.measure(track, point)

    def _local_point(self, track):
        weight = self.portfolio.joint_share_weight
        if not weight:
            return super()._local_point(track)
        center, radius = enclosing_circle(track.shape)
        estimate = track.estimate()
        current = self.client.position
        if len(track.positives) == 1 and track.positives[0][1] is not None:
            origin, angle = track.positives[0]
            a = math.radians(angle)
            along = np.array([math.cos(a), math.sin(a)])
            perpendicular = np.array([-along[1], along[0]])
            projections = (vertices(track.shape)-origin) @ along
            candidates = [
                origin+(projections.min()+self.config.first_fraction*np.ptp(projections))*along
                + sign*self.config.lateral*perpendicular
                for sign in (-1, 1)
            ]
        else:
            vector = estimate-current
            distance = np.linalg.norm(vector)
            along = vector/max(distance, 1e-9)
            perpendicular = np.array([-along[1], along[0]])
            offset = min(self.config.lateral, max(25., radius*.7))
            candidates = [estimate+sign*offset*perpendicular for sign in (-1, 1)]
        others = [t.estimate() for t in self.known if t is not track]
        def cost(point):
            onward = min((np.linalg.norm(point-q) for q in others), default=0.)
            route_cost = (np.linalg.norm(point-current)
                          + self.config.local_onward_weight*onward)
            return route_cost-weight*self._share_value(point, track)
        return min(candidates, key=cost)

    def features(self, known, points):
        n = len(points)
        position = self.client.position
        distances = np.linalg.norm(points-position, axis=1)
        pair = np.linalg.norm(points[:, None]-points[None, :], axis=2)
        nearest = np.min(pair+np.eye(n)*1e8, axis=1) if n > 1 else np.zeros(n)
        route = open_route(position, points)
        radii = [enclosing_circle(t.shape)[1] for t in known]
        remainder = ARENA.difference(self.covered)
        result = []
        # Forced-first deterministic continuations are a small model-based
        # rollout, not POMCP and not an oracle using unknown true coordinates.
        for i, point in enumerate(points):
            ids = [j for j in range(n) if j != i]
            rest = points[ids]
            cost = distances[i]+open_path_length(point, rest, open_route(point, rest))
            information = 0.
            for j, track in enumerate(known):
                if i == j or pair[i, j] > 1450:
                    continue
                origin, _ = track.positives[-1]
                a, b = points[j]-origin, points[j]-point
                sine = abs(a[0]*b[1]-a[1]*b[0])/max(np.linalg.norm(a)*np.linalg.norm(b), 1e-8)
                information += min(radii[j]/200, 1)*sine
            gain = remainder.intersection(Point(point).buffer(990, quad_segs=16)).area/ARENA.area
            local = (0. if i >= len(known) else min(radii[i]*.3, 180)/1000)
            angle = math.atan2(point[1], point[0])
            forward = (angle-self.sweep_angle) % (2*np.pi)
            result.append([
                float(i < len(known)), distances[i]/1800,
                min(radii[i]/750, 2) if i < len(known) else 0.,
                (np.sum(pair[i] < 700)-1)/16, gain, information/16,
                cost/15000, nearest[i]/1800,
                sum(t.cleared for t in self.tracks)/16, len(known)/16,
                len(self.unseen)/20, 1-remainder.area/ARENA.area,
                forward/(2*np.pi),
                float(i < len(known) and radii[i] <= 20), local,
                float(i == route[0]),
            ])
        return np.asarray(result, dtype=np.float32)

    def select(self, known, points):
        mode = self.portfolio.mode
        if mode == "route":
            if self.portfolio.survey_share_bonus and len(points) > len(known):
                route = annealed_route(
                    self.client.position, points, self.config.anneal_steps)
                base_cost = open_path_length(self.client.position, points, route)
                best = (base_cost, route[0])
                for index in range(len(known), len(points)):
                    point = points[index]
                    value = self._share_value(point, None)
                    if value <= 0:
                        continue
                    rest = np.delete(points, index, axis=0)
                    cost = (
                        np.linalg.norm(point-self.client.position)
                        + open_path_length(
                            point, rest,
                            annealed_route(point, rest, self.config.anneal_steps))
                        - self.portfolio.survey_share_bonus*value
                    )
                    if cost < best[0]:
                        best = (cost, index)
                return best[1]
            return annealed_route(self.client.position, points, self.config.anneal_steps)[0]
        if mode == "nearest":
            return int(np.argmin(np.linalg.norm(points-self.client.position, axis=1)))
        if mode == "sweep":
            angle = np.arctan2(points[:, 1], points[:, 0])
            forward = (angle-self.sweep_angle) % (2*np.pi)
            forward[forward > 2*np.pi-self.portfolio.sweep_slack] = 0.
            cost = forward*900+np.linalg.norm(points-self.client.position, axis=1)*.3
            index = int(np.argmin(cost))
            self.sweep_angle = float(angle[index])
            return index
        features = self.features(known, points)
        self.features_seen.append(features)
        if mode == "neural":
            if self.selector is None:
                raise ValueError("Neural mode requires a selector")
            index = int(self.selector(features))
        elif mode == "linear":
            weights = np.asarray(self.portfolio.linear_weights, dtype=float)
            if weights.shape != (len(FEATURES),) or not np.isfinite(weights).all():
                raise ValueError("Invalid linear weights")
            index = int(np.argmin(features @ weights))
        else:
            costs = (features[:, 6]*15000
                     - self.portfolio.info_weight*features[:, 5]*16
                     - self.portfolio.discovery_weight*features[:, 4])
            if self.portfolio.rollout_samples:
                centers = points.copy()
                for _ in range(self.portfolio.rollout_samples):
                    for j, track in enumerate(known):
                        vv = np.array(track.shape.convex_hull.exterior.coords[:-1])
                        centers[j] = vv[self.rng.integers(len(vv))]
                    for i in range(len(points)):
                        rest = np.delete(centers, i, axis=0)
                        costs[i] += (np.linalg.norm(centers[i]-self.client.position)
                                     + open_path_length(centers[i], rest, open_route(centers[i], rest))
                                     )/self.portfolio.rollout_samples
            index = int(np.argmin(costs))
        if not 0 <= index < len(points):
            raise ValueError("Selector produced an invalid action")
        self.selected_indices.append(index)
        return index

    def run(self):
        self.client.call("/enter")
        self.scan(self.client.position, force=True)
        self.make_anchors()
        while self.known or self._needs_discovery():
            start = time.perf_counter()
            known, points = self.tasks()
            if not len(points):
                raise RuntimeError("No action before completion")
            index = self.select(known, points)
            self.planning_ms.append((time.perf_counter()-start)*1000)
            if index < len(known):
                self.localize(known[index], self.portfolio.commitment or None)
            else:
                self.scan(points[index], force=True)
                self.prune_anchors()
                self.share(self.client.position)
        certificate = (sum(t.cleared for t in self.tracks) == 16
                       or (not self.known and self.covered.covers(ARENA)))
        if not certificate:
            raise RuntimeError("Missing completion certificate")
        self.client.call("/exit")
        return dict(completion_certificate=True, survey_stops=len(self.survey),
                    optical_fallbacks=self.fallbacks,
                    mean_planning_ms=float(np.mean(self.planning_ms)),
                    max_planning_ms=max(self.planning_ms, default=0.))


BEST_TOUR_CONFIG = TourConfig(
    scan_area=1928732.8720092773,
    optimistic_radius=73.61662745475769,
    first_fraction=0.35,
    lateral=60.0,
    share_sine=0.1,
    share_range=1205.2131671321795,
    share_baseline=144.49086086252382,
    cover_power=0.2,
    scan_price=4.651067206294206,
    retain_cover=True,
    relax_cover=True,
    ring_candidates=True,
    anneal_steps=4000,
    intermediate_scan=False,
    intermediate_share=True,
    q4_rings=True,
    local_onward_weight=1.2,
    max_local_actions=10,
    max_actions=5500
)

BEST_PORTFOLIO_CONFIG = PortfolioConfig(
    layout='ring',
    mode='route',
    ring_radius=1200.0,
    ring_count=6,
    angle=0.0,
    rotate_initial=False,
    relax=True,
    scan_sources=False,
    replace_anchors=False,
    scan_intermediate=False,
    info_weight=0.0,
    discovery_weight=0.0,
    sweep_slack=0.35,
    rollout_samples=0,
    linear_weights=None,
    commitment=1,
    source_task_point='center'
)

BUILD_ID = "fae8726975f5df06"


class ProtocolError(ValueError):
    def __init__(self, status, message):
        self.status = status
        super().__init__(f"{status}: {message}")


def finite_number(value):
    return (isinstance(value, Real)
            and not isinstance(value, (bool, np.bool_))
            and math.isfinite(value))


def validate_action(point, channel):
    if (not finite_number(channel) or int(channel) != channel
            or not 1 <= channel <= 20):
        raise ProtocolError(400, "channel must be an integer in 1..20")
    if (len(point) != 2
            or any(not finite_number(value) or abs(value) > 2_000_000
                   for value in point)):
        raise ProtocolError(
            400, "coordinates must be finite numbers within +/-2000000")


def validate_identifier(value, limit):
    if (not isinstance(value, str) or not value
            or any(unicodedata.category(char) in ("Cc", "Cf", "Cs")
                   for char in value)
            or len(value.encode("utf-8")) > limit):
        raise ProtocolError(400, "invalid identifier")


class RobotClient:
    def __init__(self, transport, robot_id):
        validate_identifier(robot_id, 128)
        self._transport = transport
        self.robot_id = robot_id
        self.counter = 0
        self.position = np.zeros(2)
        self.channel = 1
        self.time = 0.
        self.deadline = math.inf

    def call(self, path, point=None, channel=None):
        if point is not None:
            validate_action(point, channel)
        self.counter += 1
        payload = {
            "arena_id": "default",
            "robot_id": self.robot_id,
            "request_id": f"robot-{self.counter}",
        }
        if point is not None:
            payload.update(
                position={"x": float(point[0]), "y": float(point[1])},
                channel=int(channel))
        result = self._transport.request(path, payload)
        if result.get("accepted") is not True:
            raise RuntimeError(f"Action rejected: {path}")
        self.time = result["virtual_time_s"]
        if point is not None:
            self.position = np.asarray(point, dtype=float)
        if path == "/measure":
            self.channel = int(channel)
        if path == "/enter":
            self.deadline = (
                time.monotonic()+result["remaining_real_duration_s"]-3)
        return result


class SimulatorTransport:
    def __init__(self, url, log_path):
        parsed = urlparse(url)
        if (parsed.scheme != "http"
                or parsed.hostname not in ("127.0.0.1", "localhost")
                or parsed.path not in ("", "/")):
            raise ValueError(
                "Simulator URL must be a local loopback HTTP address")
        self.url = url.rstrip("/")
        self.log = Path(log_path).open("x", encoding="utf-8")

    def request(self, path, payload):
        if path not in ("/enter", "/measure", "/clear", "/exit"):
            raise ValueError("Unsupported simulator operation")
        wire = json.dumps(
            payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        for attempt in range(4):
            request = Request(
                self.url+path,
                data=wire,
                headers={"Content-Type": "application/json"},
                method="POST")
            try:
                with urlopen(request, timeout=10) as response:
                    status, body = response.status, response.read()
                result = json.loads(body.decode("utf-8"))
                if status != 200 or result.get("accepted") is not True:
                    raise RuntimeError(
                        f"HTTP {status}, accepted="
                        f"{result.get('accepted')}: {result}")
                self.log.write(json.dumps({
                    "path": path,
                    "request": payload,
                    "response": result,
                    "network_retries": attempt,
                }, ensure_ascii=False)+"\n")
                self.log.flush()
                return result
            except HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
            except (URLError, TimeoutError, socket.timeout):
                if attempt == 3:
                    raise
                time.sleep(.25*(attempt+1))
        raise RuntimeError("Unreachable retry state")

    def close(self):
        self.log.close()


def main():
    parser = argparse.ArgumentParser(
        description="Selected standalone controller for Problem 3")
    parser.add_argument("--robot-id", required=True, help="Current team ID")
    parser.add_argument("--url", default="http://127.0.0.1:2026")
    parser.add_argument("--log", default="q3_best_actions.jsonl")
    args = parser.parse_args()
    transport = SimulatorTransport(args.url, args.log)
    client = RobotClient(transport, args.robot_id)
    started = time.perf_counter()
    try:
        result = PortfolioTour(
            client, BEST_TOUR_CONFIG, BEST_PORTFOLIO_CONFIG).run()
        result.update(
            build_id=BUILD_ID,
            problem=3,
            virtual_time_s=client.time,
            runtime_s=time.perf_counter()-started)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        transport.close()


if __name__ == "__main__":
    main()
