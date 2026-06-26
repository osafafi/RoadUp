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

    def polygon_surface(self, boundary: list[Vec3]) -> MeshData:
        """Cap a closed boundary polyline into a surface (intersection area).

        Fan triangulation from the centroid — exact for star-convex boundaries (the common
        intersection cap). Heavy concave/boolean cases are delegated to ``roadup.blender``.
        """
        if len(boundary) < 3:
            raise GeometryError("polygon_surface needs at least three boundary points")
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
