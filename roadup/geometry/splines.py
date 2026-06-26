"""Editable control-point splines for reference lines and connectors. CODE_REFERENCE.md S2."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from roadup.common.errors import GeometryError
from roadup.common.ids import make_id
from roadup.common.types import Vec3
from roadup.geometry.sampling import resample_by_arclength

# Number of samples used for arc-length / length integration along the whole spline.
_DENSE_SAMPLES = 256


@dataclass
class ControlPoint:
    position: Vec3
    in_handle: Vec3 | None = None   # explicit incoming tangent (Bezier); None -> derived
    out_handle: Vec3 | None = None  # explicit outgoing tangent
    id: str = ""


def _v(p: Vec3) -> np.ndarray:
    return np.asarray(p, dtype=float)


def _t3(a: np.ndarray) -> Vec3:
    return (float(a[0]), float(a[1]), float(a[2]))


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
        self._cp_counter = len(self.points)
        # Populated for kind == "arc" by circular_arc(): (center, radius, a0, a1).
        self._arc: tuple[np.ndarray, float, float, float] | None = None

    # --- evaluation -------------------------------------------------------------------
    def evaluate(self, t: float) -> Vec3:
        t = min(1.0, max(0.0, t))
        if self.kind == "arc":
            return self._evaluate_arc(t)
        if len(self.points) < 2:
            raise GeometryError("spline needs at least two control points")
        i, lt = self._segment(t)
        if self.kind == "line":
            p0, p1 = _v(self.points[i].position), _v(self.points[i + 1].position)
            return _t3(p0 + (p1 - p0) * lt)
        if self.kind == "catmullRom":
            return _t3(self._catmull_rom(i, lt))
        if self.kind == "bezier":
            return _t3(self._bezier(i, lt))
        raise GeometryError(f"unknown spline kind: {self.kind!r}")

    def tangent(self, t: float) -> Vec3:
        h = 1e-5
        a = _v(self.evaluate(min(1.0, t + h)))
        b = _v(self.evaluate(max(0.0, t - h)))
        d = a - b
        norm = np.linalg.norm(d)
        if norm == 0.0:
            raise GeometryError("degenerate tangent")
        return _t3(d / norm)

    def curvature(self, t: float) -> float:
        h = 1e-4
        p_prev = _v(self.evaluate(max(0.0, t - h)))
        p0 = _v(self.evaluate(min(1.0, max(0.0, t))))
        p_next = _v(self.evaluate(min(1.0, t + h)))
        d1 = (p_next - p_prev) / (2 * h)
        d2 = (p_next - 2 * p0 + p_prev) / (h * h)
        cross_z = d1[0] * d2[1] - d1[1] * d2[0]
        speed = np.linalg.norm(d1[:2])
        if speed == 0.0:
            return 0.0
        return float(cross_z / (speed**3))

    def length(self, t0: float = 0.0, t1: float = 1.0) -> float:
        ts = np.linspace(t0, t1, _DENSE_SAMPLES)
        pts = np.array([_v(self.evaluate(float(t))) for t in ts])
        return float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1)))

    def sample(self, step: float) -> list[Vec3]:
        """Sample at ~``step`` metres (approximately arc-length spaced)."""
        if step <= 0.0:
            raise GeometryError("step must be positive")
        ts = np.linspace(0.0, 1.0, _DENSE_SAMPLES)
        dense = [self.evaluate(float(t)) for t in ts]
        return resample_by_arclength(dense, step)

    # --- editing (driven by tooling) --------------------------------------------------
    def insert_control_point(self, t: float) -> ControlPoint:
        """Add a control point at parameter ``t``, preserving shape; returns the new point."""
        if self.kind == "arc":
            raise GeometryError("cannot insert control points into an arc spline")
        if len(self.points) < 2:
            raise GeometryError("spline needs at least two control points")
        i, _ = self._segment(t)
        self._cp_counter += 1
        cp = ControlPoint(position=self.evaluate(t), id=make_id("cp", self._cp_counter))
        self.points.insert(i + 1, cp)
        return cp

    def remove_control_point(self, cp_id: str) -> None:
        idx = self._index_of(cp_id)
        if len(self.points) <= 2:
            raise GeometryError("spline must keep at least two control points")
        del self.points[idx]

    def move_control_point(self, cp_id: str, position: Vec3) -> None:
        idx = self._index_of(cp_id)
        self.points[idx].position = position

    # --- construction helpers ---------------------------------------------------------
    @classmethod
    def circular_arc(
        cls,
        start: Vec3,
        start_tangent: Vec3,
        end: Vec3,
        end_tangent: Vec3,
    ) -> Spline:
        """Minimal circular arc matching both tangents (the default intersection connector).

        The circle is fixed by the start point, the start tangent, and the end point (a single
        arc is over-determined by two tangents); ``end_tangent`` only disambiguates turn
        direction. Suited to lane-end connectors where the tangents are near-consistent.
        """
        p0, p1 = _v(start), _v(end)
        t0 = _v(start_tangent)
        t0 /= np.linalg.norm(t0)
        # Center lies along the left/right normal of the start tangent. Pick the side the end
        # point falls on; use end_tangent's turn sign to break ties on a straight shot.
        left = np.array([-t0[1], t0[0], 0.0])
        chord = p1 - p0
        side = float(np.dot(chord, left))
        if abs(side) < 1e-9:
            turn = float(t0[0] * end_tangent[1] - t0[1] * end_tangent[0])
            side = turn if abs(turn) > 1e-9 else 1.0
        n = left if side > 0 else -left
        # R from the perpendicular-bisector condition |C-p0| == |C-p1| with C = p0 + R*n.
        denom = 2.0 * float(np.dot(chord, n))
        if abs(denom) < 1e-9:
            raise GeometryError("cannot fit a circular arc to these endpoints/tangent")
        radius = float(np.dot(chord, chord) / denom)
        center = p0 + radius * n
        r = abs(radius)
        a0 = float(np.arctan2(p0[1] - center[1], p0[0] - center[0]))
        a1 = float(np.arctan2(p1[1] - center[1], p1[0] - center[0]))
        # Choose sweep direction consistent with the start tangent.
        if radius > 0:  # center on the left -> counter-clockwise
            while a1 < a0:
                a1 += 2 * np.pi
        else:
            while a1 > a0:
                a1 -= 2 * np.pi

        sp = cls(
            points=[ControlPoint(position=start, id="cp_001"),
                    ControlPoint(position=end, id="cp_002")],
            kind="arc",
        )
        sp._arc = (center, r, a0, a1)
        return sp

    # --- internals --------------------------------------------------------------------
    def _segment(self, t: float) -> tuple[int, float]:
        n_seg = len(self.points) - 1
        scaled = min(1.0, max(0.0, t)) * n_seg
        i = min(int(scaled), n_seg - 1)
        return i, scaled - i

    def _catmull_rom(self, i: int, lt: float) -> np.ndarray:
        pts = [_v(cp.position) for cp in self.points]
        n = len(pts)
        p0 = pts[max(0, i - 1)]
        p1 = pts[i]
        p2 = pts[min(n - 1, i + 1)]
        p3 = pts[min(n - 1, i + 2)]
        t2 = lt * lt
        t3 = t2 * lt
        return 0.5 * (
            (2 * p1)
            + (-p0 + p2) * lt
            + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
            + (-p0 + 3 * p1 - 3 * p2 + p3) * t3
        )

    def _bezier(self, i: int, lt: float) -> np.ndarray:
        p0 = _v(self.points[i].position)
        p3 = _v(self.points[i + 1].position)
        out_h = self.points[i].out_handle
        in_h = self.points[i + 1].in_handle
        p1 = _v(out_h) if out_h is not None else p0 + (p3 - p0) / 3.0
        p2 = _v(in_h) if in_h is not None else p3 - (p3 - p0) / 3.0
        u = 1.0 - lt
        return (u**3) * p0 + 3 * (u**2) * lt * p1 + 3 * u * (lt**2) * p2 + (lt**3) * p3

    def _evaluate_arc(self, t: float) -> Vec3:
        if self._arc is None:
            raise GeometryError("arc spline has no arc parameters")
        center, r, a0, a1 = self._arc
        a = a0 + (a1 - a0) * t
        z0 = self.points[0].position[2]
        z1 = self.points[-1].position[2]
        return (
            float(center[0] + r * np.cos(a)),
            float(center[1] + r * np.sin(a)),
            float(z0 + (z1 - z0) * t),
        )

    def _index_of(self, cp_id: str) -> int:
        for idx, cp in enumerate(self.points):
            if cp.id == cp_id:
                return idx
        raise GeometryError(f"no control point with id {cp_id!r}")
