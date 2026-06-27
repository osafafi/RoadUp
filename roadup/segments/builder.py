"""Build a Road from a reference-line spline + road-type preset. CODE_REFERENCE.md S7."""
from __future__ import annotations

import math

import numpy as np

from roadup.common.errors import ValidationError
from roadup.common.types import GeometryType, LaneType, RoadType
from roadup.geometry.splines import Spline
from roadup.markings.presets import get_preset
from roadup.markings.roadmark import to_road_mark
from roadup.opendrive.model.road import Geometry, Lane, LaneSection, Road
from roadup.segments.lane_width import WidthLaw
from roadup.segments.presets import LaneSpec, RoadTypePreset, get_road_type_preset
from roadup.segments.vertical_profile import ElevationLaw, SuperelevationLaw


class SegmentBuilder:
    """Fluent builder: reference line + lane layout + width laws + markings -> ``Road``."""

    def __init__(self, road_type: RoadType) -> None:
        self._road_type = road_type
        self._spline: Spline | None = None
        self._left_count: int | None = None
        self._right_count: int | None = None
        self._width_laws: dict[int, WidthLaw] = {}
        self._markings: dict[int, str] = {}
        self._elevation: ElevationLaw | None = None
        self._superelevation: SuperelevationLaw | None = None

    def with_reference_line(self, spline: Spline) -> SegmentBuilder:
        self._spline = spline
        return self

    def with_elevation(self, law: ElevationLaw) -> SegmentBuilder:
        """Set the vertical profile (``z`` along ``s``); baked to ``<elevation>`` records."""
        self._elevation = law
        return self

    def with_superelevation(self, law: SuperelevationLaw) -> SegmentBuilder:
        """Set the lateral bank profile (angle along ``s``); baked to ``<superelevation>``."""
        self._superelevation = law
        return self

    def with_lane_count(self, left: int, right: int) -> SegmentBuilder:
        self._left_count = left
        self._right_count = right
        return self

    def set_lane_width_law(self, lane_id: int, law: WidthLaw) -> SegmentBuilder:
        self._width_laws[lane_id] = law
        return self

    def set_lane_marking(self, lane_id: int, preset_id: str) -> SegmentBuilder:
        self._markings[lane_id] = preset_id
        return self

    def build(self, road_id: str) -> Road:
        """Bake the spline into plan-view geometry, lanes, width records and road marks."""
        if self._spline is None:
            raise ValidationError("SegmentBuilder needs a reference line (with_reference_line)")
        preset = get_road_type_preset(self._road_type)
        geometry = bake_reference_line(self._spline)
        length = sum(g.length for g in geometry)
        section = self._build_section(preset)
        user_data: dict = {
            "kind": "referenceLine",
            "splineKind": self._spline.kind,
            "controlPoints": [
                {"id": cp.id, "pos": list(cp.position)} for cp in self._spline.points
            ],
        }
        if self._elevation is not None:
            user_data["elevationLaw"] = {
                "kind": self._elevation.kind,
                "control": [list(c) for c in self._elevation.control],
            }
        if self._superelevation is not None:
            user_data["superelevationLaw"] = {
                "kind": self._superelevation.kind,
                "control": [list(c) for c in self._superelevation.control],
            }
        return Road(
            id=road_id,
            length=length,
            geometry=geometry,
            lane_sections=[section],
            elevation=self._elevation.bake_records() if self._elevation is not None else [],
            superelevation=(
                self._superelevation.bake_records() if self._superelevation is not None else []
            ),
            user_data=user_data,
        )

    # --- lanes ------------------------------------------------------------------------
    def _build_section(self, preset: RoadTypePreset) -> LaneSection:
        right_specs = self._resolve_specs(preset.lane_specs_right, self._right_count)
        left_specs = self._resolve_specs(preset.lane_specs_left, self._left_count)
        right = [self._lane(-(i + 1), spec) for i, spec in enumerate(right_specs)]
        left = [self._lane(i + 1, spec) for i, spec in enumerate(left_specs)]
        return LaneSection(s=0.0, left=left, center=self._center_lane(preset), right=right)

    @staticmethod
    def _resolve_specs(specs: tuple[LaneSpec, ...], count: int | None) -> list[LaneSpec]:
        if count is None:
            return list(specs)
        if count < 0:
            raise ValidationError("lane count cannot be negative")
        if count == 0 or not specs:
            return list(specs[:count]) if specs else []
        result = list(specs[:count])
        while len(result) < count:  # extend by repeating the outermost spec
            result.append(specs[-1])
        return result

    def _center_lane(self, preset: RoadTypePreset) -> Lane:
        preset_id = preset.center_marking_preset
        marks = [to_road_mark(get_preset(preset_id))] if preset_id else []
        user_data = {"kind": "lane", "markingPreset": preset_id} if preset_id else {}
        return Lane(id=0, type=LaneType.NONE, road_marks=marks, user_data=user_data)

    def _lane(self, lane_id: int, spec: LaneSpec) -> Lane:
        preset_id = self._markings.get(lane_id, spec.marking_preset)
        law = self._width_laws.get(lane_id, WidthLaw.constant(spec.width))
        marks = [to_road_mark(get_preset(preset_id))] if preset_id else []
        user_data: dict = {
            "kind": "lane",
            "widthLaw": {"kind": law.kind, "control": [list(c) for c in law.control]},
        }
        if preset_id:
            user_data["markingPreset"] = preset_id
        return Lane(id=lane_id, type=spec.type, widths=law.bake_records(),
                    road_marks=marks, user_data=user_data)


# --- reference-line baking ------------------------------------------------------------
def bake_reference_line(spline: Spline) -> list[Geometry]:
    """Bake an editable :class:`~roadup.geometry.splines.Spline` to OpenDRIVE plan-view records.

    * ``line`` -> one ``<line>`` per polyline segment.
    * ``arc``  -> one ``<arc>`` (signed curvature).
    * ``bezier`` / ``catmullRom`` -> one ``<paramPoly3>`` per cubic segment, expressed in that
      segment's local frame. Exact for cubics. Adjacent records are tangent-continuous for
      ``catmullRom`` (and for C1 beziers); the writer's ``adjust_geometries()`` chains them.
    """
    if spline.kind == "line":
        return _bake_line(spline)
    if spline.kind == "arc":
        return _bake_arc(spline)
    if spline.kind in ("bezier", "catmullRom"):
        return _bake_cubic(spline)
    raise ValidationError(f"cannot bake reference line of kind {spline.kind!r}")


def _bake_line(spline: Spline) -> list[Geometry]:
    pts = [cp.position for cp in spline.points]
    if len(pts) < 2:
        raise ValidationError("line spline needs at least two control points")
    records: list[Geometry] = []
    s = 0.0
    for p0, p1 in zip(pts, pts[1:], strict=False):
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        length = math.hypot(dx, dy)
        records.append(
            Geometry(s=s, x=p0[0], y=p0[1], hdg=math.atan2(dy, dx),
                     length=length, type=GeometryType.LINE)
        )
        s += length
    return records


def _bake_arc(spline: Spline) -> list[Geometry]:
    if spline._arc is None:
        raise ValidationError("arc spline has no arc parameters")
    _center, r, a0, a1 = spline._arc
    sweep = a1 - a0
    length = r * abs(sweep)
    if length <= 0.0:
        raise ValidationError("degenerate arc spline (zero length)")
    curvature = sweep / length  # sign(sweep)/r : +ve = counter-clockwise (OpenDRIVE convention)
    p0 = spline.evaluate(0.0)
    t0 = spline.tangent(0.0)
    return [
        Geometry(s=0.0, x=p0[0], y=p0[1], hdg=math.atan2(t0[1], t0[0]),
                 length=length, type=GeometryType.ARC, params={"curvature": curvature})
    ]


def _bake_cubic(spline: Spline) -> list[Geometry]:
    n = len(spline.points)
    if n < 2:
        raise ValidationError("spline needs at least two control points")
    records: list[Geometry] = []
    s = 0.0
    for i in range(n - 1):
        a, b, c, d = _segment_monomial(spline, i)
        hdg = math.atan2(b[1], b[0])
        cos_h, sin_h = math.cos(hdg), math.sin(hdg)
        bU, bV = _to_local(b, cos_h, sin_h)
        cU, cV = _to_local(c, cos_h, sin_h)
        dU, dV = _to_local(d, cos_h, sin_h)
        t0, t1 = i / (n - 1), (i + 1) / (n - 1)
        length = spline.length(t0, t1)
        records.append(
            Geometry(
                s=s, x=float(a[0]), y=float(a[1]), hdg=hdg, length=length,
                type=GeometryType.PARAM_POLY3,
                params={
                    "aU": 0.0, "bU": bU, "cU": cU, "dU": dU,
                    "aV": 0.0, "bV": bV, "cV": cV, "dV": dV,
                },
            )
        )
        s += length
    return records


def _to_local(v: np.ndarray, cos_h: float, sin_h: float) -> tuple[float, float]:
    """Rotate a global xy vector into a frame whose +u axis is at heading ``hdg``."""
    return (
        float(v[0] * cos_h + v[1] * sin_h),
        float(-v[0] * sin_h + v[1] * cos_h),
    )


def _segment_monomial(
    spline: Spline, i: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Global monomial coefficients (A,B,C,D) of segment ``i``: P(u)=A+Bu+Cu²+Du³, u in [0,1]."""
    pts = [np.asarray(cp.position, dtype=float) for cp in spline.points]
    n = len(pts)
    if spline.kind == "catmullRom":
        p0 = pts[max(0, i - 1)]
        p1 = pts[i]
        p2 = pts[min(n - 1, i + 1)]
        p3 = pts[min(n - 1, i + 2)]
        a = p1
        b = 0.5 * (-p0 + p2)
        c = 0.5 * (2 * p0 - 5 * p1 + 4 * p2 - p3)
        d = 0.5 * (-p0 + 3 * p1 - 3 * p2 + p3)
        return a, b, c, d
    # bezier
    p0 = pts[i]
    p3 = pts[i + 1]
    out_h = spline.points[i].out_handle
    in_h = spline.points[i + 1].in_handle
    p1 = np.asarray(out_h, dtype=float) if out_h is not None else p0 + (p3 - p0) / 3.0
    p2 = np.asarray(in_h, dtype=float) if in_h is not None else p3 - (p3 - p0) / 3.0
    a = p0
    b = 3.0 * (p1 - p0)
    c = 3.0 * (p0 - 2 * p1 + p2)
    d = p3 - 3 * p2 + 3 * p1 - p0
    return a, b, c, d
