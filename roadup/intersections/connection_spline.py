"""Editable connection spline for one junction connection. CODE_REFERENCE.md S9.

Default is a basic circular curve; adding control points upgrades it to a control-point
spline baked to OpenDRIVE ``paramPoly3``. See ARCHITECTURE.md S6.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from roadup.common.types import Vec3

if TYPE_CHECKING:
    from roadup.geometry.splines import Spline
    from roadup.opendrive.model.road import Geometry


class ConnectionSpline:
    """The editable path of one connecting road's reference line."""

    spline: "Spline"
    is_default_arc: bool   # True until the user edits control points

    @classmethod
    def default_arc(
        cls,
        start: Vec3,
        start_tangent: Vec3,
        end: Vec3,
        end_tangent: Vec3,
    ) -> "ConnectionSpline":
        """Basic circular curve between two connected lane ends (the default)."""
        raise NotImplementedError

    def add_control_point(self, t: float) -> str:
        """Add an editable control point (flips ``is_default_arc`` False); returns its id."""
        raise NotImplementedError

    def move_control_point(self, cp_id: str, position: Vec3) -> None:
        raise NotImplementedError

    def remove_control_point(self, cp_id: str) -> None:
        raise NotImplementedError

    def to_geometry_records(self) -> list["Geometry"]:
        """Bake to plan-view records: a single ``<arc>`` if default, else ``<paramPoly3>``(s)."""
        raise NotImplementedError
