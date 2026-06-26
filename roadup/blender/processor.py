"""MeshProcessor interface + pure-Python default. CODE_REFERENCE.md S12.

Blender is optional. The boundary is ``MeshData`` in / ``MeshData`` out; ``bpy`` types never
cross this line. See ARCHITECTURE.md S11.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from roadup.geometry.mesh import MeshData


class MeshProcessor(Protocol):
    def boolean_union(self, meshes: list["MeshData"]) -> "MeshData": ...
    def remesh(self, mesh: "MeshData", voxel_size: float) -> "MeshData": ...
    def decimate(self, mesh: "MeshData", ratio: float) -> "MeshData": ...


class PurePythonMeshProcessor:
    """numpy/geometry-based default - sufficient for simple junctions."""

    def boolean_union(self, meshes: list["MeshData"]) -> "MeshData":
        raise NotImplementedError

    def remesh(self, mesh: "MeshData", voxel_size: float) -> "MeshData":
        raise NotImplementedError

    def decimate(self, mesh: "MeshData", ratio: float) -> "MeshData":
        raise NotImplementedError


def get_processor(prefer_blender: bool = False) -> MeshProcessor:
    """Return a Blender-backed processor if requested and available, else the pure-Python one."""
    raise NotImplementedError
