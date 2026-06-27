"""Editable elevation + superelevation laws, baked to OpenDRIVE profile records. CODE_REFERENCE S7.

The vertical profile (``z`` along ``s``) and the lateral superelevation (bank angle along ``s``) are
each authored as a 1D control-point law and baked to piecewise-cubic records — the exact same shape
as :class:`~roadup.segments.lane_width.WidthLaw`, just over a different quantity. The shared
``_bake_poly3`` mirrors that baker (constant / linear / Catmull-Rom spline) so the three laws stay
consistent. Empty/flat laws produce no records, so a flat road serializes identically to today.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from roadup.common.errors import ValidationError
from roadup.opendrive.model.road import ElevationRecord, SuperelevationRecord

# One baked record as raw coefficients: (s, a, b, c, d).
_Poly3Coeffs = tuple[float, float, float, float, float]


def _sorted_control(control: list[tuple[float, float]]) -> list[tuple[float, float]]:
    return sorted(control, key=lambda c: c[0])


def _catmull_rom_tangents(pts: list[tuple[float, float]]) -> list[float]:
    """Finite-difference ``dv/ds`` tangent at each control point (one-sided at the ends)."""
    n = len(pts)
    tangents: list[float] = []
    for i in range(n):
        lo = max(0, i - 1)
        hi = min(n - 1, i + 1)
        ds = pts[hi][0] - pts[lo][0]
        tangents.append((pts[hi][1] - pts[lo][1]) / ds if ds > 0 else 0.0)
    return tangents


def _bake_poly3(kind: str, control: list[tuple[float, float]]) -> list[_Poly3Coeffs]:
    """Bake control points ``[(s, value), ...]`` to piecewise-cubic ``(s, a, b, c, d)`` records."""
    pts = _sorted_control(control)
    if not pts:
        raise ValidationError("profile law has no control points")
    if len(pts) == 1 or kind == "constant":
        return [(pts[0][0], pts[0][1], 0.0, 0.0, 0.0)]
    if kind == "linear":
        records: list[_Poly3Coeffs] = []
        for (s0, v0), (s1, v1) in zip(pts, pts[1:], strict=False):
            length = s1 - s0
            slope = (v1 - v0) / length if length > 0 else 0.0
            records.append((s0, v0, slope, 0.0, 0.0))
        records.append((pts[-1][0], pts[-1][1], 0.0, 0.0, 0.0))
        return records
    if kind == "spline":
        tangents = _catmull_rom_tangents(pts)
        records = []
        for i, ((s0, v0), (s1, v1)) in enumerate(zip(pts, pts[1:], strict=False)):
            length = s1 - s0
            if length <= 0:
                continue
            m0, m1 = tangents[i], tangents[i + 1]
            dv = v1 - v0
            a = v0
            b = m0
            c = (3.0 * dv) / (length * length) - (2.0 * m0 + m1) / length
            d = (-2.0 * dv) / (length ** 3) + (m0 + m1) / (length * length)
            records.append((s0, a, b, c, d))
        records.append((pts[-1][0], pts[-1][1], 0.0, 0.0, 0.0))
        return records
    raise ValidationError(f"unknown profile law kind: {kind!r}")


def _value_at(records: list[_Poly3Coeffs], s: float) -> float:
    rec = records[0]
    for candidate in records:
        if candidate[0] <= s:
            rec = candidate
        else:
            break
    s0, a, b, c, d = rec
    ds = s - s0
    return a + b * ds + c * ds * ds + d * ds * ds * ds


@dataclass
class ElevationLaw:
    """Elevation ``z`` as a function of arc length, authored as control points ``[(s, z), ...]``."""

    kind: str = "constant"   # "constant" | "linear" | "spline"
    control: list[tuple[float, float]] = field(default_factory=list)

    def elevation_at(self, s: float) -> float:
        return _value_at(_bake_poly3(self.kind, self.control), s)

    def bake_records(self) -> list[ElevationRecord]:
        return [ElevationRecord(s=s, a=a, b=b, c=c, d=d)
                for s, a, b, c, d in _bake_poly3(self.kind, self.control)]

    @classmethod
    def constant(cls, z: float) -> ElevationLaw:
        return cls(kind="constant", control=[(0.0, z)])

    @classmethod
    def grade(cls, length: float, slope: float, z0: float = 0.0) -> ElevationLaw:
        """A steady grade: ``z(s) = z0 + slope·s`` over ``[0, length]`` (``slope`` = rise/run)."""
        return cls(kind="linear", control=[(0.0, z0), (length, z0 + slope * length)])

    @classmethod
    def crest(cls, s0: float, z0: float, s1: float, z1: float,
              s2: float, z2: float) -> ElevationLaw:
        """A smooth crest/sag through three control points (Catmull-Rom)."""
        return cls(kind="spline", control=[(s0, z0), (s1, z1), (s2, z2)])


@dataclass
class SuperelevationLaw:
    """Bank/roll angle (rad) as a function of arc length; control points ``[(s, angle), ...]``."""

    kind: str = "constant"   # "constant" | "linear" | "spline"
    control: list[tuple[float, float]] = field(default_factory=list)

    def angle_at(self, s: float) -> float:
        return _value_at(_bake_poly3(self.kind, self.control), s)

    def bake_records(self) -> list[SuperelevationRecord]:
        return [SuperelevationRecord(s=s, a=a, b=b, c=c, d=d)
                for s, a, b, c, d in _bake_poly3(self.kind, self.control)]

    @classmethod
    def constant(cls, angle: float) -> SuperelevationLaw:
        return cls(kind="constant", control=[(0.0, angle)])

    @classmethod
    def ramp(cls, s0: float, a0: float, s1: float, a1: float) -> SuperelevationLaw:
        """Linearly ramp the bank angle from ``a0`` at ``s0`` to ``a1`` at ``s1`` (radians)."""
        return cls(kind="linear", control=[(s0, a0), (s1, a1)])
