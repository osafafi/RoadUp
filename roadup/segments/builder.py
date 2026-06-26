"""Build a Road from a reference-line spline + road-type preset. CODE_REFERENCE.md S7."""
from __future__ import annotations

from typing import TYPE_CHECKING

from roadup.common.types import RoadType

if TYPE_CHECKING:
    from roadup.geometry.splines import Spline
    from roadup.opendrive.model.road import Road
    from roadup.segments.lane_width import WidthLaw


class SegmentBuilder:
    """Fluent builder: reference line + lane layout + width laws + markings -> ``Road``."""

    def __init__(self, road_type: RoadType) -> None:
        self._road_type = road_type

    def with_reference_line(self, spline: "Spline") -> "SegmentBuilder":
        raise NotImplementedError

    def with_lane_count(self, left: int, right: int) -> "SegmentBuilder":
        raise NotImplementedError

    def set_lane_width_law(self, lane_id: int, law: "WidthLaw") -> "SegmentBuilder":
        raise NotImplementedError

    def set_lane_marking(self, lane_id: int, preset_id: str) -> "SegmentBuilder":
        raise NotImplementedError

    def build(self, road_id: str) -> "Road":
        """Bake the spline into plan-view geometry, lanes, width records and road marks."""
        raise NotImplementedError
