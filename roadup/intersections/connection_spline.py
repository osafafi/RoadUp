"""Editable connection spline for one junction connection. CODE_REFERENCE.md S9.

The default connector is the simplest curve that honours both lane-end tangents: a straight
``<line>`` when both ends point along the chord, a minimal circular ``<arc>`` when one arc matches
both tangents (symmetric turns), else a tangent-matched cubic Bézier baked to ``paramPoly3`` (the
general skewed/offset case — a single arc cannot honour two arbitrary tangents). Adding control
points upgrades whatever the default is to an editable control-point spline. See ARCHITECTURE.md S6.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from roadup.common.errors import GeometryError
from roadup.common.types import Vec3
from roadup.geometry.splines import ControlPoint, Spline
from roadup.segments.builder import bake_reference_line

if TYPE_CHECKING:
    from roadup.opendrive.model.road import Geometry

# Interior samples used when an editable arc is upgraded to a control-point spline (keeps shape).
_UPGRADE_SAMPLES = 3
# A unit-tangent dot above this counts as "aligned" (~2.6°) for line/arc feasibility tests.
_TANGENT_TOL = 0.999


class ConnectionSpline:
    """The editable path of one connecting road's reference line."""

    spline: Spline
    is_default_arc: bool   # True until the user edits control points

    def __init__(self, spline: Spline, is_default_arc: bool) -> None:
        self.spline = spline
        self.is_default_arc = is_default_arc

    @classmethod
    def default_arc(
        cls,
        start: Vec3,
        start_tangent: Vec3,
        end: Vec3,
        end_tangent: Vec3,
    ) -> ConnectionSpline:
        """The simplest tangent-honouring connector between two lane ends (the default).

        Line if both tangents point along the chord; minimal circular arc if one arc honours both
        tangents (symmetric turns); otherwise a tangent-matched cubic Bézier (general skewed case).
        Named ``default_arc`` for the spec/round-trip payload; ``is_default_arc`` marks the shape as
        the unedited default regardless of which primitive was chosen.
        """
        return cls(_default_spline(start, start_tangent, end, end_tangent), is_default_arc=True)

    def add_control_point(self, t: float) -> str:
        """Add an editable control point (flips ``is_default_arc`` False); returns its id."""
        if self.is_default_arc:
            self._upgrade_to_control_points()
        return self.spline.insert_control_point(t).id

    def move_control_point(self, cp_id: str, position: Vec3) -> None:
        self.spline.move_control_point(cp_id, position)

    def remove_control_point(self, cp_id: str) -> None:
        self.spline.remove_control_point(cp_id)

    def to_geometry_records(self) -> list[Geometry]:
        """Bake to plan-view records: a single ``<arc>`` if default, else ``<paramPoly3>``(s)."""
        return bake_reference_line(self.spline)

    def userdata(self) -> dict:
        """``<userData>`` payload so editing intent round-trips (CODE_REFERENCE S14)."""
        return {
            "kind": "connectionSpline",
            "isDefaultArc": self.is_default_arc,
            "controlPoints": [
                {"id": cp.id, "pos": list(cp.position)} for cp in self.spline.points
            ],
        }

    # --- internals --------------------------------------------------------------------
    def _upgrade_to_control_points(self) -> None:
        """Replace the default shape with an equivalent Catmull-Rom control-point spline."""
        n = _UPGRADE_SAMPLES + 1
        pts = [
            ControlPoint(position=self.spline.evaluate(i / n), id=f"cp_{i + 1:03d}")
            for i in range(n + 1)
        ]
        self.spline = Spline(points=pts, kind="catmullRom")
        self.is_default_arc = False


def _default_spline(start: Vec3, st: Vec3, end: Vec3, et: Vec3) -> Spline:
    chord = np.asarray(end, dtype=float) - np.asarray(start, dtype=float)
    chord_len = float(np.linalg.norm(chord))
    st_u, et_u = _unit(st), _unit(et)
    # Straight line: both tangents point along the chord.
    if chord_len > 1e-9:
        chord_u = chord / chord_len
        along_chord = min(float(np.dot(st_u, chord_u)), float(np.dot(et_u, chord_u)))
        if along_chord > _TANGENT_TOL:
            return _line(start, end)
    # Minimal circular arc, when a single arc honours both tangents (symmetric turns).
    try:
        arc = Spline.circular_arc(start, st, end, et)
    except GeometryError:
        arc = None
    if arc is not None and float(np.dot(_unit(arc.tangent(1.0)), et_u)) > _TANGENT_TOL:
        return arc
    # General case: a cubic Bézier matching position + tangent at both ends (bakes to paramPoly3).
    return _hermite_bezier(start, st_u, end, et_u, chord_len)


def _line(start: Vec3, end: Vec3) -> Spline:
    return Spline(
        points=[ControlPoint(position=start, id="cp_001"),
                ControlPoint(position=end, id="cp_002")],
        kind="line",
    )


def _hermite_bezier(start: Vec3, st_u: np.ndarray, end: Vec3, et_u: np.ndarray,
                    chord_len: float) -> Spline:
    """Bézier whose end tangents are st/et; handle length chord/3 is the standard smooth default."""
    p0 = np.asarray(start, dtype=float)
    p1 = np.asarray(end, dtype=float)
    handle = (chord_len / 3.0) or 1.0
    out_h = _vec3(p0 + st_u * handle)
    in_h = _vec3(p1 - et_u * handle)
    return Spline(
        points=[ControlPoint(position=start, out_handle=out_h, id="cp_001"),
                ControlPoint(position=end, in_handle=in_h, id="cp_002")],
        kind="bezier",
    )


def _unit(v: Vec3) -> np.ndarray:
    a = np.asarray(v, dtype=float)
    n = np.linalg.norm(a)
    return a / n if n else a


def _vec3(a: np.ndarray) -> Vec3:
    return (float(a[0]), float(a[1]), float(a[2]))
