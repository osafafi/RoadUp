"""Adaptive intersection surface generation. CODE_REFERENCE.md S9.

Pure-Python path: the junction surface is the union of each connecting road's drivable ribbon, plus
a central cap over the interior polygon formed by the connecting-road endpoints. Heavy
concave/boolean cases are delegated to :class:`roadup.blender.processor.MeshProcessor` later
(Stage 7); this default suits the common star-convex junction.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from roadup.geometry.mesh import MeshBuilder, MeshData

if TYPE_CHECKING:
    from roadup.common.types import Vec3
    from roadup.opendrive.eval.sampler import Sampler
    from roadup.opendrive.model.junction import Junction


class IntersectionSurface:
    """Generate the junction surface from current connection splines + incoming lane edges."""

    def __init__(self, sampler: Sampler) -> None:
        self._sampler = sampler
        self._mesh = MeshBuilder()

    def generate(self, junction: Junction) -> MeshData:
        """Build the capped surface for the junction area.

        Boundary = union of the connecting-road ribbons + a central cap. Heavy boolean cases
        may be delegated to :class:`roadup.blender.processor.MeshProcessor`.
        """
        surface = MeshData()
        corners: list[Vec3] = []
        for conn in junction.connections:
            left, right = self._sampler.road_surface_polylines(conn.connecting_road)
            if len(left) < 2 or len(right) < 2:
                continue
            surface = surface.merge(self._mesh.ribbon(left, right))
            # The connecting road's two endpoints (left+right edges) bound the interior cap.
            corners.extend([left[0], right[0], left[-1], right[-1]])

        cap = self._central_cap(corners)
        if cap is not None:
            surface = surface.merge(cap)
        return surface

    # --- internals --------------------------------------------------------------------
    def _central_cap(self, corners: list[Vec3]) -> MeshData | None:
        """Fan-cap the interior: the connecting-road endpoints ordered around the centroid."""
        if len(corners) < 3:
            return None
        cx = sum(p[0] for p in corners) / len(corners)
        cy = sum(p[1] for p in corners) / len(corners)
        ordered = sorted(corners, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
        return self._mesh.polygon_surface(ordered)
