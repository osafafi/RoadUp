"""Adaptive intersection surface generation. CODE_REFERENCE.md S9."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from roadup.geometry.mesh import MeshData
    from roadup.opendrive.eval.sampler import Sampler
    from roadup.opendrive.model.junction import Junction


class IntersectionSurface:
    """Generate the junction surface from current connection splines + incoming lane edges."""

    def __init__(self, sampler: "Sampler") -> None:
        self._sampler = sampler

    def generate(self, junction: "Junction") -> "MeshData":
        """Build the capped surface for the junction area.

        Boundary = union of outer lane edges + connection-spline fans. Heavy boolean cases
        may be delegated to :class:`roadup.blender.processor.MeshProcessor`.
        """
        raise NotImplementedError
