"""Lateral offset of reference-line frames into lane boundaries. CODE_REFERENCE.md S2."""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from roadup.common.errors import GeometryError
from roadup.common.types import Vec3

if TYPE_CHECKING:
    from roadup.geometry.sampling import Frame


def offset_polyline(frames: list[Frame], t_offset: float | list[float]) -> list[Vec3]:
    """Offset along frame normals.

    ``t_offset`` is a scalar (constant offset) or a per-frame list (varying lane width).
    Positive ``t`` follows each frame's normal (+t = left, OpenDRIVE convention).
    """
    if not frames:
        return []
    if isinstance(t_offset, (int, float)):
        offsets = [float(t_offset)] * len(frames)
    else:
        offsets = [float(o) for o in t_offset]
        if len(offsets) != len(frames):
            raise GeometryError(
                f"t_offset length {len(offsets)} != frame count {len(frames)}"
            )
    out: list[Vec3] = []
    for frame, o in zip(frames, offsets, strict=True):
        p = np.asarray(frame.position, dtype=float)
        n = np.asarray(frame.normal, dtype=float)
        q = p + n * o
        out.append((float(q[0]), float(q[1]), float(q[2])))
    return out


def lane_boundary(
    frames: list[Frame],
    inner_t: list[float],
    outer_t: list[float],
) -> tuple[list[Vec3], list[Vec3]]:
    """Inner/outer boundary polylines for a lane given per-station ``t`` offsets."""
    return offset_polyline(frames, inner_t), offset_polyline(frames, outer_t)
