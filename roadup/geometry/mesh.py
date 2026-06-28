"""Mesh data container and builders. CODE_REFERENCE.md S2."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from roadup.common.errors import GeometryError
from roadup.common.types import Vec2, Vec3


@dataclass
class MeshData:
    """Raw triangulated mesh, framework-agnostic (no pxr types)."""

    points: list[Vec3] = field(default_factory=list)
    face_vertex_counts: list[int] = field(default_factory=list)
    face_vertex_indices: list[int] = field(default_factory=list)
    normals: list[Vec3] = field(default_factory=list)
    uvs: list[Vec2] = field(default_factory=list)

    def merge(self, other: MeshData) -> MeshData:
        """Return a new mesh combining ``self`` and ``other`` (re-indexed)."""
        offset = len(self.points)
        return MeshData(
            points=self.points + other.points,
            face_vertex_counts=self.face_vertex_counts + other.face_vertex_counts,
            face_vertex_indices=self.face_vertex_indices
            + [i + offset for i in other.face_vertex_indices],
            normals=self.normals + other.normals,
            uvs=self.uvs + other.uvs,
        )

    def _faces(self) -> list[list[int]]:
        faces: list[list[int]] = []
        cursor = 0
        for count in self.face_vertex_counts:
            faces.append(self.face_vertex_indices[cursor : cursor + count])
            cursor += count
        return faces

    def is_manifold(self) -> bool:
        """Edge-manifold check: no undirected edge is shared by more than two faces."""
        edge_count: dict[tuple[int, int], int] = {}
        for face in self._faces():
            n = len(face)
            if n < 3:
                return False
            for k in range(n):
                a, b = face[k], face[(k + 1) % n]
                key = (a, b) if a < b else (b, a)
                edge_count[key] = edge_count.get(key, 0) + 1
        return all(c <= 2 for c in edge_count.values())


class MeshBuilder:
    def ribbon(self, left: list[Vec3], right: list[Vec3]) -> MeshData:
        """Triangulated strip between two boundary polylines (road / marking surface)."""
        if len(left) != len(right):
            raise GeometryError("ribbon boundaries must have equal length")
        if len(left) < 2:
            raise GeometryError("ribbon needs at least two stations")
        n = len(left)
        points = list(left) + list(right)  # right indices offset by n
        counts: list[int] = []
        indices: list[int] = []
        for i in range(n - 1):
            li, lj = i, i + 1
            ri, rj = n + i, n + i + 1
            # CCW seen from +z so face normals point up.
            counts.append(4)
            indices.extend([li, ri, rj, lj])
        return MeshData(points=points, face_vertex_counts=counts, face_vertex_indices=indices)

    def extrude(self, path: list[Vec3], cross_section: list[Vec2]) -> MeshData:
        """Extrude a 2D cross-section (lateral t, vertical z) along a 3D path (curbs, barriers)."""
        if len(path) < 2:
            raise GeometryError("extrude path needs at least two points")
        if len(cross_section) < 2:
            raise GeometryError("cross_section needs at least two points")
        pts = np.asarray(path, dtype=float)
        rings: list[np.ndarray] = []
        for i, p in enumerate(pts):
            nxt = pts[min(i + 1, len(pts) - 1)]
            prv = pts[max(i - 1, 0)]
            tangent = nxt - prv
            tn = np.linalg.norm(tangent)
            if tn == 0.0:
                raise GeometryError("degenerate extrude path segment")
            tangent /= tn
            lateral = np.array([-tangent[1], tangent[0], 0.0])  # +t left
            up = np.array([0.0, 0.0, 1.0])
            ring = np.array([p + lateral * c[0] + up * c[1] for c in cross_section])
            rings.append(ring)

        m = len(cross_section)
        points: list[Vec3] = []
        for ring in rings:
            points.extend((float(x), float(y), float(z)) for x, y, z in ring)
        counts: list[int] = []
        indices: list[int] = []
        for i in range(len(rings) - 1):
            base_a = i * m
            base_b = (i + 1) * m
            for j in range(m - 1):
                counts.append(4)
                indices.extend([base_a + j, base_b + j, base_b + j + 1, base_a + j + 1])
        return MeshData(points=points, face_vertex_counts=counts, face_vertex_indices=indices)

    def polygon_surface(
        self,
        boundary: list[Vec3],
        *,
        interior_spacing: float | None = None,
        boundary_max_edge: float | None = None,
    ) -> MeshData:
        """Cap a closed boundary polyline into a surface (intersection area).

        ``interior_spacing`` selects the topology:

        * ``None`` — **centroid fan**: one central vertex to every boundary vertex. Exact for
          star-convex boundaries but yields long thin triangles on a large/irregular cap.
        * a metre value — **Delaunay fill**: scatter interior Steiner points ~``interior_spacing``
          apart and Delaunay-triangulate boundary + interior, for near-isotropic triangles (no
          slivers). ``boundary_max_edge`` (metres) first subdivides any long boundary edge — e.g. a
          road's straight end-edge — so the boundary sampling matches the interior density. Falls
          back to the fan when the cap is smaller than the spacing.

        Heavy concave/boolean cases are delegated to ``roadup.blender`` (Stage 7).
        """
        if len(boundary) < 3:
            raise GeometryError("polygon_surface needs at least three boundary points")
        if interior_spacing is None:
            return self._fan_cap(boundary)
        return self._delaunay_cap(boundary, interior_spacing, boundary_max_edge)

    # --- cap topologies ---------------------------------------------------------------
    def _fan_cap(self, boundary: list[Vec3]) -> MeshData:
        pts = np.asarray(boundary, dtype=float)
        centroid = pts.mean(axis=0)
        points: list[Vec3] = [(float(centroid[0]), float(centroid[1]), float(centroid[2]))]
        points.extend((float(x), float(y), float(z)) for x, y, z in pts)
        counts: list[int] = []
        indices: list[int] = []
        n = len(pts)
        for i in range(n):
            counts.append(3)
            indices.extend([0, 1 + i, 1 + (i + 1) % n])
        return MeshData(points=points, face_vertex_counts=counts, face_vertex_indices=indices)

    def _delaunay_cap(
        self, boundary: list[Vec3], spacing: float, max_edge: float | None
    ) -> MeshData:
        from roadup.geometry.triangulate import fill_polygon, interior_grid

        ring = _densify_ring(boundary, max_edge) if max_edge else list(boundary)
        ring_arr = np.asarray(ring, dtype=float)
        boundary_xy = ring_arr[:, :2]
        plane = _fit_plane(ring_arr)
        interior_xy = interior_grid(boundary_xy, spacing)
        tris = fill_polygon(boundary_xy, interior_xy)
        if not tris:  # cap smaller than the spacing — nothing scattered inside; fan is safe.
            return self._fan_cap(boundary)

        interior_z = (
            _plane_z(plane, interior_xy)
            if len(interior_xy)
            else np.empty((0,))
        )
        points: list[Vec3] = [(float(x), float(y), float(z)) for x, y, z in ring_arr]
        points.extend(
            (float(interior_xy[k, 0]), float(interior_xy[k, 1]), float(interior_z[k]))
            for k in range(len(interior_xy))
        )
        counts = [3] * len(tris)
        indices: list[int] = [idx for tri in tris for idx in tri]
        return MeshData(points=points, face_vertex_counts=counts, face_vertex_indices=indices)


def _densify_ring(boundary: list[Vec3], max_edge: float) -> list[Vec3]:
    """Subdivide any closed-ring edge longer than ``max_edge`` by linear interpolation (incl. z)."""
    pts = np.asarray(boundary, dtype=float)
    n = len(pts)
    out: list[Vec3] = []
    for i in range(n):
        a = pts[i]
        b = pts[(i + 1) % n]
        out.append((float(a[0]), float(a[1]), float(a[2])))
        seg = float(np.linalg.norm(b - a))
        cuts = int(seg // max_edge) if max_edge > 0.0 else 0
        for k in range(1, cuts + 1):
            t = k / (cuts + 1)
            p = a + (b - a) * t
            out.append((float(p[0]), float(p[1]), float(p[2])))
    return out


def _fit_plane(ring: np.ndarray) -> tuple[float, float, float]:
    """Least-squares plane ``z = a*x + b*y + c`` through the boundary (for interior-point z).

    Junctions are near-flat or gently sloped, so a single plane is plenty; degenerate fits (all
    points collinear in xy) fall back to a constant mean z.
    """
    a_mat = np.column_stack([ring[:, 0], ring[:, 1], np.ones(len(ring))])
    try:
        coeffs, *_ = np.linalg.lstsq(a_mat, ring[:, 2], rcond=None)
        return float(coeffs[0]), float(coeffs[1]), float(coeffs[2])
    except np.linalg.LinAlgError:
        return 0.0, 0.0, float(ring[:, 2].mean())


def _plane_z(plane: tuple[float, float, float], xy: np.ndarray) -> np.ndarray:
    a, b, c = plane
    return a * xy[:, 0] + b * xy[:, 1] + c
