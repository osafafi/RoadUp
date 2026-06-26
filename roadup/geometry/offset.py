"""Lateral offset of reference-line frames into lane boundaries. CODE_REFERENCE.md S2."""
from __future__ import annotations

from typing import TYPE_CHECKING

from roadup.common.types import Vec3

if TYPE_CHECKING:
    from roadup.geometry.sampling import Frame


def offset_polyline(frames: list["Frame"], t_offset: float | list[float]) -> list[Vec3]:
    """Offset along frame normals.

    ``t_offset`` is a scalar (constant offset) or a per-frame list (varying lane width).
    """
    raise NotImplementedError


def lane_boundary(
    frames: list["Frame"],
    inner_t: list[float],
    outer_t: list[float],
) -> tuple[list[Vec3], list[Vec3]]:
    """Inner/outer boundary polylines for a lane given per-station ``t`` offsets."""
    raise NotImplementedError
