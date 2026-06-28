"""Planar triangulation helpers for filling a polygon with well-shaped triangles. CODE_REFERENCE S2.

The junction cap used to fan every boundary vertex to a single centroid — correct, but it produces
long thin "stretchy" triangles when the boundary is large or irregular. :func:`fill_polygon` instead
scatters interior **Steiner points** on a grid and runs a Bowyer–Watson **Delaunay** triangulation
over boundary + interior, then keeps only the triangles that lie inside the polygon. Delaunay
maximises the minimum angle, so the result is near-isotropic (no slivers) and its triangle size is
controlled by one knob — the interior point spacing.

Pure-Python / numpy only (no native deps), so it runs in CI. Intended for the star-convex junction
caps RoadUp generates; wildly concave boundaries are a Blender-accelerated path (Stage 7).
"""
from __future__ import annotations

import numpy as np

# A bad triangle's circumcircle test is done in float; this slack absorbs round-off on cocircular
# points (a regular grid produces many) so insertion stays robust. Pure scale-relative epsilon.
_INCIRCLE_EPS = 1e-9


def point_in_polygon(x: float, y: float, poly: np.ndarray) -> bool:
    """Even–odd ray-cast test: is ``(x, y)`` inside the closed xy polygon ``poly`` (N×2)?"""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i, 0], poly[i, 1]
        xj, yj = poly[j, 0], poly[j, 1]
        if (yi > y) != (yj > y):
            x_cross = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < x_cross:
                inside = not inside
        j = i
    return inside


def interior_grid(
    boundary_xy: np.ndarray, spacing: float, *, margin_frac: float = 0.5
) -> np.ndarray:
    """Grid of points strictly inside ``boundary_xy`` (N×2), spaced ~``spacing`` metres apart.

    Points closer than ``margin_frac * spacing`` to a boundary vertex are dropped so interior
    Steiner points never collide with the (denser) boundary samples. Returns an M×2 array (possibly
    empty for a polygon smaller than the spacing).
    """
    if spacing <= 0.0:
        return np.empty((0, 2))
    lo = boundary_xy.min(axis=0)
    hi = boundary_xy.max(axis=0)
    margin = margin_frac * spacing
    xs = np.arange(lo[0] + spacing, hi[0], spacing)
    ys = np.arange(lo[1] + spacing, hi[1], spacing)
    pts: list[tuple[float, float]] = []
    for x in xs:
        for y in ys:
            if not point_in_polygon(float(x), float(y), boundary_xy):
                continue
            if np.min(np.hypot(boundary_xy[:, 0] - x, boundary_xy[:, 1] - y)) < margin:
                continue
            pts.append((float(x), float(y)))
    return np.asarray(pts, dtype=float) if pts else np.empty((0, 2))


def delaunay(points: np.ndarray) -> list[tuple[int, int, int]]:
    """Bowyer–Watson Delaunay triangulation of ``points`` (N×2). Returns CCW index triples.

    Incremental: start from a super-triangle enclosing all points, insert each point by deleting the
    triangles whose circumcircle contains it and re-filling the resulting hole, then drop every
    triangle still touching a super-triangle vertex.
    """
    n = len(points)
    if n < 3:
        return []
    lo = points.min(axis=0)
    hi = points.max(axis=0)
    centre = (lo + hi) / 2.0
    span = float(np.max(hi - lo)) or 1.0
    # Super-triangle vertices, far enough out to enclose every point's circumcircle.
    sup = np.array(
        [
            [centre[0] - 20 * span, centre[1] - span],
            [centre[0] + 20 * span, centre[1] - span],
            [centre[0], centre[1] + 20 * span],
        ]
    )
    verts = np.vstack([points, sup])
    a, b, c = n, n + 1, n + 2
    triangles: list[tuple[int, int, int]] = [(a, b, c)]

    for i in range(n):
        p = verts[i]
        bad = [t for t in triangles if _in_circumcircle(verts[t[0]], verts[t[1]], verts[t[2]], p)]
        # The hole boundary = edges of `bad` triangles that aren't shared by two bad triangles.
        edge_count: dict[tuple[int, int], int] = {}
        for t in bad:
            for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                key = (e[0], e[1]) if e[0] < e[1] else (e[1], e[0])
                edge_count[key] = edge_count.get(key, 0) + 1
        bad_set = set(bad)
        triangles = [t for t in triangles if t not in bad_set]
        for t in bad:
            for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                key = (e[0], e[1]) if e[0] < e[1] else (e[1], e[0])
                if edge_count[key] == 1:  # boundary edge of the hole
                    triangles.append(_ccw(verts, (e[0], e[1], i)))

    return [t for t in triangles if a not in t and b not in t and c not in t]


def fill_polygon(boundary_xy: np.ndarray, interior_xy: np.ndarray) -> list[tuple[int, int, int]]:
    """Triangulate the polygon: Delaunay over boundary+interior, keep interior triangles only.

    Indices reference ``np.vstack([boundary_xy, interior_xy])``. A triangle is kept when its
    centroid lies inside ``boundary_xy`` — this discards the convex-hull fill outside a (mildly)
    concave boundary while leaving a star-convex cap fully covered.
    """
    pts = np.vstack([boundary_xy, interior_xy]) if len(interior_xy) else boundary_xy
    tris = delaunay(pts)
    kept: list[tuple[int, int, int]] = []
    for t in tris:
        cx = (pts[t[0], 0] + pts[t[1], 0] + pts[t[2], 0]) / 3.0
        cy = (pts[t[0], 1] + pts[t[1], 1] + pts[t[2], 1]) / 3.0
        if point_in_polygon(float(cx), float(cy), boundary_xy):
            kept.append(t)
    return kept


def _ccw(verts: np.ndarray, t: tuple[int, int, int]) -> tuple[int, int, int]:
    """Order a triangle counter-clockwise (positive signed area) so face normals point +Z."""
    a, b, c = verts[t[0]], verts[t[1]], verts[t[2]]
    area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return (t[0], t[2], t[1]) if area < 0.0 else t


def _in_circumcircle(a: np.ndarray, b: np.ndarray, c: np.ndarray, p: np.ndarray) -> bool:
    """True if ``p`` is inside the circumcircle of CCW triangle (a, b, c) — in-circle predicate."""
    ax, ay = a[0] - p[0], a[1] - p[1]
    bx, by = b[0] - p[0], b[1] - p[1]
    cx, cy = c[0] - p[0], c[1] - p[1]
    det = (
        (ax * ax + ay * ay) * (bx * cy - cx * by)
        - (bx * bx + by * by) * (ax * cy - cx * ay)
        + (cx * cx + cy * cy) * (ax * by - bx * ay)
    )
    # Triangles are kept CCW, for which det > 0 ⇔ p strictly inside the circumcircle.
    return det > _INCIRCLE_EPS
