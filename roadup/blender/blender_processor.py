"""Out-of-process headless Blender mesh processor. CODE_REFERENCE.md S12.

This module never imports ``bpy`` in-process; it shells out to the Blender interpreter
running :mod:`roadup.blender._bpy_worker` over a temp exchange file.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from roadup.geometry.mesh import MeshData


class BlenderMeshProcessor:
    def __init__(self, blender_exe: str | None = None) -> None:
        self._blender_exe = blender_exe

    def boolean_union(self, meshes: list["MeshData"]) -> "MeshData":
        raise NotImplementedError

    def remesh(self, mesh: "MeshData", voxel_size: float) -> "MeshData":
        raise NotImplementedError

    def decimate(self, mesh: "MeshData", ratio: float) -> "MeshData":
        raise NotImplementedError
