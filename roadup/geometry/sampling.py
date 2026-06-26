"""Station frames and arc-length resampling. CODE_REFERENCE.md S2."""
from __future__ import annotations

from dataclasses import dataclass

from roadup.common.types import Vec3


@dataclass
class Frame:
    """A station frame along a reference line."""

    s: float          # arc length from the start of the reference line
    position: Vec3
    tangent: Vec3     # unit, along +s
    normal: Vec3      # unit, left of tangent in xy (OpenDRIVE +t direction)


def sample_frames(points: list[Vec3], step: float) -> list[Frame]:
    """Build station frames at ~``step`` metres from a polyline."""
    raise NotImplementedError


def resample_by_arclength(points: list[Vec3], step: float) -> list[Vec3]:
    """Resample a polyline to roughly uniform arc-length spacing."""
    raise NotImplementedError
