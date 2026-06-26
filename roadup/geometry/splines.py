"""Editable control-point splines for reference lines and connection curves. CODE_REFERENCE.md S2."""
from __future__ import annotations

from dataclasses import dataclass, field

from roadup.common.types import Vec3


@dataclass
class ControlPoint:
    position: Vec3
    in_handle: Vec3 | None = None   # explicit incoming tangent (Bezier); None -> derived
    out_handle: Vec3 | None = None  # explicit outgoing tangent
    id: str = ""


class Spline:
    """Editable control-point spline.

    Planar in xy for reference lines; ``z`` carries elevation. ``kind`` selects the
    interpolation/basis used by :meth:`evaluate` and the baked OpenDRIVE geometry.
    """

    points: list[ControlPoint]
    kind: str  # "bezier" | "catmullRom" | "line" | "arc"

    def __init__(self, points: list[ControlPoint] | None = None, kind: str = "catmullRom") -> None:
        self.points = points or []
        self.kind = kind

    # --- evaluation -------------------------------------------------------------------
    def evaluate(self, t: float) -> Vec3:
        raise NotImplementedError

    def tangent(self, t: float) -> Vec3:
        raise NotImplementedError

    def curvature(self, t: float) -> float:
        raise NotImplementedError

    def length(self, t0: float = 0.0, t1: float = 1.0) -> float:
        raise NotImplementedError

    def sample(self, step: float) -> list[Vec3]:
        """Sample at ~``step`` metres (approximately arc-length spaced)."""
        raise NotImplementedError

    # --- editing (driven by tooling) --------------------------------------------------
    def insert_control_point(self, t: float) -> ControlPoint:
        """Add a control point at parameter ``t``, preserving shape; returns the new point."""
        raise NotImplementedError

    def remove_control_point(self, cp_id: str) -> None:
        raise NotImplementedError

    def move_control_point(self, cp_id: str, position: Vec3) -> None:
        raise NotImplementedError

    # --- construction helpers ---------------------------------------------------------
    @classmethod
    def circular_arc(
        cls,
        start: Vec3,
        start_tangent: Vec3,
        end: Vec3,
        end_tangent: Vec3,
    ) -> "Spline":
        """Minimal circular arc matching both tangents (the default intersection connector)."""
        raise NotImplementedError
