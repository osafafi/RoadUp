"""Road/lane/width/road-mark dataclasses (the source-of-truth model). CODE_REFERENCE.md S3."""
from __future__ import annotations

from dataclasses import dataclass, field

from roadup.common.errors import ValidationError
from roadup.common.types import GeometryType, LaneType


@dataclass
class Geometry:
    """One ``<planView><geometry>`` record."""

    s: float
    x: float
    y: float
    hdg: float
    length: float
    type: GeometryType
    params: dict[str, float] = field(default_factory=dict)  # curvature / aU..dV / spiral curvatures


@dataclass
class WidthRecord:
    """``<lane><width>``: ``w(ds) = a + b*ds + c*ds^2 + d*ds^3`` valid from ``s_offset``."""

    s_offset: float
    a: float
    b: float = 0.0
    c: float = 0.0
    d: float = 0.0


@dataclass
class RoadMark:
    """``<lane><roadMark>`` geometric/semantic part; material preset rides in ``user_data``."""

    s_offset: float
    type: str = "solid"            # "solid" | "broken" | "solid solid" | "solid broken" | ...
    weight: str = "standard"       # "standard" | "bold"
    color: str = "white"
    width: float = 0.15
    dash_length: float | None = None  # set for explicit <type>/<line> dashes
    gap_length: float | None = None
    preset_id: str = ""            # RoadUp marking preset id (see markings.presets)


@dataclass
class LaneLink:
    predecessor: int | None = None  # lane id in the previous element
    successor: int | None = None    # lane id in the next element


@dataclass
class Lane:
    id: int                                              # signed OpenDRIVE lane id (0 = center)
    type: LaneType = LaneType.DRIVING
    widths: list[WidthRecord] = field(default_factory=list)   # the width law along length
    road_marks: list[RoadMark] = field(default_factory=list)
    link: LaneLink = field(default_factory=LaneLink)
    user_data: dict = field(default_factory=dict)


@dataclass
class LaneSection:
    s: float
    left: list[Lane] = field(default_factory=list)
    center: Lane | None = None
    right: list[Lane] = field(default_factory=list)

    def _all_lanes(self) -> list[Lane]:
        lanes = list(self.left)
        if self.center is not None:
            lanes.append(self.center)
        lanes.extend(self.right)
        return lanes

    def lane(self, lane_id: int) -> Lane:
        for ln in self._all_lanes():
            if ln.id == lane_id:
                return ln
        raise ValidationError(f"no lane with id {lane_id} in section at s={self.s}")

    def lane_ids(self) -> list[int]:
        """All lane ids, ordered left (most positive) → center (0) → right (most negative)."""
        return sorted((ln.id for ln in self._all_lanes()), reverse=True)


@dataclass
class RoadLink:
    # (elementType, elementId): ("road" | "junction", id)
    predecessor: tuple[str, str] | None = None
    successor: tuple[str, str] | None = None


@dataclass
class Road:
    id: str
    length: float = 0.0
    geometry: list[Geometry] = field(default_factory=list)         # plan-view reference line
    lane_sections: list[LaneSection] = field(default_factory=list)
    link: RoadLink = field(default_factory=RoadLink)
    junction: str | None = None    # set when this is a connecting road inside a junction
    user_data: dict = field(default_factory=dict)

    def lane_section_at(self, s: float) -> LaneSection:
        """The lane section governing station ``s`` (the last one starting at or before ``s``)."""
        if not self.lane_sections:
            raise ValidationError(f"road {self.id} has no lane sections")
        chosen: LaneSection | None = None
        for section in sorted(self.lane_sections, key=lambda ls: ls.s):
            if section.s <= s + 1e-9:
                chosen = section
            else:
                break
        if chosen is None:
            raise ValidationError(f"no lane section at or before s={s} on road {self.id}")
        return chosen
