"""Mesh data container and builders. CODE_REFERENCE.md S2."""
from __future__ import annotations

from dataclasses import dataclass, field

from roadup.common.types import Vec2, Vec3


@dataclass
class MeshData:
    """Raw triangulated mesh, framework-agnostic (no pxr types)."""

    points: list[Vec3] = field(default_factory=list)
    face_vertex_counts: list[int] = field(default_factory=list)
    face_vertex_indices: list[int] = field(default_factory=list)
    normals: list[Vec3] = field(default_factory=list)
    uvs: list[Vec2] = field(default_factory=list)

    def merge(self, other: "MeshData") -> "MeshData":
        """Return a new mesh combining ``self`` and ``other`` (re-indexed)."""
        raise NotImplementedError

    def is_manifold(self) -> bool:
        raise NotImplementedError


class MeshBuilder:
    def ribbon(self, left: list[Vec3], right: list[Vec3]) -> MeshData:
        """Triangulated strip between two boundary polylines (road / marking surface)."""
        raise NotImplementedError

    def extrude(self, path: list[Vec3], cross_section: list[Vec2]) -> MeshData:
        """Extrude a 2D cross-section along a 3D path (curbs, barriers)."""
        raise NotImplementedError

    def polygon_surface(self, boundary: list[Vec3]) -> MeshData:
        """Cap a closed boundary polyline into a surface (intersection area)."""
        raise NotImplementedError
