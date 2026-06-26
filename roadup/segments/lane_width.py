"""Editable lane width-along-length law, baked to OpenDRIVE <width> records (CODE_REFERENCE S7)."""
from __future__ import annotations

from dataclasses import dataclass, field

from roadup.common.errors import ValidationError
from roadup.opendrive.model.road import WidthRecord


@dataclass
class WidthLaw:
    """Width as a function of arc length, authored as control points and baked to cubics.

    ``control`` is ``[(s, width), ...]`` sorted by ``s``. ``kind`` selects how the curve between
    control points is interpolated when baking to OpenDRIVE ``<width>`` cubic records
    (``w(ds) = a + b·ds + c·ds² + d·ds³``, ``ds`` local to each record's ``sOffset``).
    """

    kind: str = "constant"   # "constant" | "linear" | "spline"
    control: list[tuple[float, float]] = field(default_factory=list)  # [(s, width), ...]

    def width_at(self, s: float) -> float:
        records = self.bake_records()
        # The record governing s is the last one whose s_offset <= s.
        rec = records[0]
        for candidate in records:
            if candidate.s_offset <= s:
                rec = candidate
            else:
                break
        ds = s - rec.s_offset
        return rec.a + rec.b * ds + rec.c * ds * ds + rec.d * ds * ds * ds

    def bake_records(self) -> list[WidthRecord]:
        """Produce piecewise-cubic ``<width>`` records covering the lane length."""
        pts = self._sorted_control()
        if not pts:
            raise ValidationError("width law has no control points")
        if len(pts) == 1 or self.kind == "constant":
            return [WidthRecord(s_offset=pts[0][0], a=pts[0][1])]
        if self.kind == "linear":
            return self._bake_linear(pts)
        if self.kind == "spline":
            return self._bake_spline(pts)
        raise ValidationError(f"unknown width law kind: {self.kind!r}")

    # --- construction helpers ---------------------------------------------------------
    @classmethod
    def constant(cls, width: float) -> WidthLaw:
        return cls(kind="constant", control=[(0.0, width)])

    @classmethod
    def taper(cls, s0: float, w0: float, s1: float, w1: float) -> WidthLaw:
        return cls(kind="linear", control=[(s0, w0), (s1, w1)])

    # --- internals --------------------------------------------------------------------
    def _sorted_control(self) -> list[tuple[float, float]]:
        return sorted(self.control, key=lambda c: c[0])

    @staticmethod
    def _bake_linear(pts: list[tuple[float, float]]) -> list[WidthRecord]:
        records: list[WidthRecord] = []
        for (s0, w0), (s1, w1) in zip(pts, pts[1:], strict=False):
            length = s1 - s0
            slope = (w1 - w0) / length if length > 0 else 0.0
            records.append(WidthRecord(s_offset=s0, a=w0, b=slope))
        records.append(WidthRecord(s_offset=pts[-1][0], a=pts[-1][1]))
        return records

    def _bake_spline(self, pts: list[tuple[float, float]]) -> list[WidthRecord]:
        tangents = self._catmull_rom_tangents(pts)
        records: list[WidthRecord] = []
        for i, ((s0, w0), (s1, w1)) in enumerate(zip(pts, pts[1:], strict=False)):
            length = s1 - s0
            if length <= 0:
                continue
            m0, m1 = tangents[i], tangents[i + 1]
            dw = w1 - w0
            a = w0
            b = m0
            c = (3.0 * dw) / (length * length) - (2.0 * m0 + m1) / length
            d = (-2.0 * dw) / (length ** 3) + (m0 + m1) / (length * length)
            records.append(WidthRecord(s_offset=s0, a=a, b=b, c=c, d=d))
        records.append(WidthRecord(s_offset=pts[-1][0], a=pts[-1][1]))
        return records

    @staticmethod
    def _catmull_rom_tangents(pts: list[tuple[float, float]]) -> list[float]:
        """Finite-difference dw/ds tangent at each control point (one-sided at the ends)."""
        n = len(pts)
        tangents: list[float] = []
        for i in range(n):
            lo = max(0, i - 1)
            hi = min(n - 1, i + 1)
            ds = pts[hi][0] - pts[lo][0]
            tangents.append((pts[hi][1] - pts[lo][1]) / ds if ds > 0 else 0.0)
        return tangents
