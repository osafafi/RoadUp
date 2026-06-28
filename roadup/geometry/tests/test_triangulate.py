"""Unit tests for roadup.geometry.triangulate + the Delaunay junction cap."""
from __future__ import annotations

import math

import numpy as np

from roadup.geometry.mesh import MeshBuilder
from roadup.geometry.triangulate import delaunay, fill_polygon, interior_grid, point_in_polygon


def _square(n: int = 12, r: float = 10.0) -> list[tuple[float, float, float]]:
    """A closed ring approximating a square (n samples per side), flat at z=0."""
    pts: list[tuple[float, float, float]] = []
    side = [(-r, -r), (r, -r), (r, r), (-r, r)]
    for k in range(4):
        a = np.array(side[k])
        b = np.array(side[(k + 1) % 4])
        for i in range(n):
            p = a + (b - a) * (i / n)
            pts.append((float(p[0]), float(p[1]), 0.0))
    return pts


def _min_angle(points: list[tuple], counts: list[int], indices: list[int]) -> float:
    P = [np.array(p[:2]) for p in points]
    cur = 0
    worst = 180.0
    for c in counts:
        idx = indices[cur:cur + c]
        cur += c
        a, b, d = P[idx[0]], P[idx[1]], P[idx[2]]
        for u, v, w in ((a, b, d), (b, d, a), (d, a, b)):
            e1, e2 = v - u, w - u
            cosv = float(np.dot(e1, e2) / ((np.linalg.norm(e1) * np.linalg.norm(e2)) or 1.0))
            worst = min(worst, math.degrees(math.acos(max(-1.0, min(1.0, cosv)))))
    return worst


def test_point_in_polygon() -> None:
    poly = np.array([(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)])
    assert point_in_polygon(5.0, 5.0, poly)
    assert not point_in_polygon(-1.0, 5.0, poly)
    assert not point_in_polygon(15.0, 5.0, poly)


def test_interior_grid_stays_inside() -> None:
    poly = np.array([(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)])
    grid = interior_grid(poly, spacing=2.0)
    assert len(grid) > 0
    assert all(point_in_polygon(float(x), float(y), poly) for x, y in grid)


def test_delaunay_is_edge_manifold() -> None:
    rng = np.random.default_rng(0)
    pts = rng.uniform(0.0, 10.0, size=(30, 2))
    tris = delaunay(pts)
    assert tris
    edge_count: dict[tuple[int, int], int] = {}
    for t in tris:
        for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            key = (e[0], e[1]) if e[0] < e[1] else (e[1], e[0])
            edge_count[key] = edge_count.get(key, 0) + 1
    assert all(c <= 2 for c in edge_count.values())  # no edge shared by 3+ triangles


def test_fill_polygon_triangles_are_ccw_and_inside() -> None:
    boundary = np.array([(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)])
    interior = interior_grid(boundary, spacing=2.5)
    pts = np.vstack([boundary, interior])
    tris = fill_polygon(boundary, interior)
    assert tris
    for t in tris:
        a, b, c = pts[t[0]], pts[t[1]], pts[t[2]]
        area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        assert area > 0.0, "triangles must be CCW (so face normals point +Z)"


def test_delaunay_cap_beats_fan_on_min_angle() -> None:
    boundary = _square()
    fan = MeshBuilder().polygon_surface(boundary)
    delaunay_cap = MeshBuilder().polygon_surface(
        boundary, interior_spacing=4.0, boundary_max_edge=4.0
    )
    assert delaunay_cap.is_manifold()
    # No duplicate vertices, all triangles.
    assert set(delaunay_cap.face_vertex_counts) == {3}
    assert len({tuple(round(c, 6) for c in p) for p in delaunay_cap.points}) == len(
        delaunay_cap.points
    )
    fan_worst = _min_angle(fan.points, fan.face_vertex_counts, fan.face_vertex_indices)
    cap_worst = _min_angle(
        delaunay_cap.points, delaunay_cap.face_vertex_counts, delaunay_cap.face_vertex_indices
    )
    assert cap_worst > fan_worst, "Delaunay cap should have a larger smallest angle (fewer slivers)"


def test_delaunay_cap_falls_back_to_fan_when_tiny() -> None:
    # A cap far smaller than the spacing scatters no interior points -> safe centroid fan.
    boundary = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
    mesh = MeshBuilder().polygon_surface(boundary, interior_spacing=50.0)
    assert mesh.points and mesh.is_manifold()


def test_delaunay_cap_interpolates_z_on_a_slope() -> None:
    # Boundary tilted along x (z = 0.1*x); interior vertices should follow the plane, not sit at 0.
    boundary = [
        (float(x), float(y), 0.1 * float(x))
        for x, y, _ in _square(n=10, r=10.0)
    ]
    mesh = MeshBuilder().polygon_surface(boundary, interior_spacing=4.0, boundary_max_edge=4.0)
    for x, _y, z in mesh.points:
        assert abs(z - 0.1 * x) < 1e-6
