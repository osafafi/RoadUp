"""Station frames and arc-length resampling. CODE_REFERENCE.md S2."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from roadup.common.errors import GeometryError
from roadup.common.types import Vec3


@dataclass
class Frame:
    """A station frame along a reference line."""

    s: float          # arc length from the start of the reference line
    position: Vec3
    tangent: Vec3     # unit, along +s
    normal: Vec3      # unit, left of tangent in xy (OpenDRIVE +t direction)


def _as_array(points: list[Vec3]) -> np.ndarray:
    if len(points) < 2:
        raise GeometryError("need at least two points to build frames")
    return np.asarray(points, dtype=float)


def _left_normal_xy(tangent: np.ndarray) -> np.ndarray:
    """Unit normal 90° to the left of ``tangent`` in the xy-plane (OpenDRIVE +t)."""
    return np.array([-tangent[1], tangent[0], 0.0])


def resample_by_arclength(points: list[Vec3], step: float) -> list[Vec3]:
    """Resample a polyline to roughly uniform arc-length spacing.

    The first and last vertices are always preserved; interior samples land at multiples of
    ``step`` along the cumulative arc length.
    """
    if step <= 0.0:
        raise GeometryError("step must be positive")
    pts = _as_array(points)
    seg = np.diff(pts, axis=0)
    seg_len = np.linalg.norm(seg, axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg_len)])
    total = float(cum[-1])
    if total == 0.0:
        raise GeometryError("degenerate polyline (zero length)")

    n = max(1, int(round(total / step)))
    targets = np.linspace(0.0, total, n + 1)
    xs = np.interp(targets, cum, pts[:, 0])
    ys = np.interp(targets, cum, pts[:, 1])
    zs = np.interp(targets, cum, pts[:, 2])
    return [(float(x), float(y), float(z)) for x, y, z in zip(xs, ys, zs, strict=True)]


def sample_frames(points: list[Vec3], step: float) -> list[Frame]:
    """Build station frames at ~``step`` metres from a polyline.

    Tangents come from central differences along the resampled polyline; the normal is the
    left-of-tangent direction in xy (the OpenDRIVE +t direction).
    """
    resampled = resample_by_arclength(points, step)
    pts = np.asarray(resampled, dtype=float)
    # Central-difference tangents (forward/backward at the ends).
    tangents = np.gradient(pts, axis=0)
    seg_len = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    s_values = np.concatenate([[0.0], np.cumsum(seg_len)])

    frames: list[Frame] = []
    for i, p in enumerate(pts):
        t = tangents[i]
        norm = np.linalg.norm(t)
        if norm == 0.0:
            raise GeometryError("zero-length tangent while sampling frames")
        t_unit = t / norm
        n_unit = _left_normal_xy(t_unit)
        frames.append(
            Frame(
                s=float(s_values[i]),
                position=(float(p[0]), float(p[1]), float(p[2])),
                tangent=(float(t_unit[0]), float(t_unit[1]), float(t_unit[2])),
                normal=(float(n_unit[0]), float(n_unit[1]), float(n_unit[2])),
            )
        )
    return frames
