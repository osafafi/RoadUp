"""Road-type presets: lane layout, default markings, speeds. CODE_REFERENCE.md S7.

The numbers below are illustrative starting points; tune during the build session.
"""
from __future__ import annotations

from dataclasses import dataclass

from roadup.common.types import LaneType, RoadType


@dataclass(frozen=True)
class LaneSpec:
    type: LaneType
    width: float
    marking_preset: str = ""   # outer-edge marking preset id (see markings.presets)


@dataclass(frozen=True)
class RoadTypePreset:
    road_type: RoadType
    lane_specs_right: tuple[LaneSpec, ...]   # in id order -1, -2, ...
    lane_specs_left: tuple[LaneSpec, ...]    # in id order +1, +2, ...
    center_marking_preset: str
    design_speed_kmh: float
    default_fillet_radius: float


# Illustrative presets - extend/tune during the build session.
ROAD_TYPE_PRESETS: dict[RoadType, RoadTypePreset] = {
    RoadType.LOCAL: RoadTypePreset(
        road_type=RoadType.LOCAL,
        lane_specs_right=(LaneSpec(LaneType.DRIVING, 3.25, "white_solid"),),
        lane_specs_left=(LaneSpec(LaneType.DRIVING, 3.25, "white_solid"),),
        center_marking_preset="yellow_solid",
        design_speed_kmh=50.0,
        default_fillet_radius=3.0,
    ),
    RoadType.ARTERIAL: RoadTypePreset(
        road_type=RoadType.ARTERIAL,
        lane_specs_right=(
            LaneSpec(LaneType.DRIVING, 3.5, "white_dashed"),
            LaneSpec(LaneType.DRIVING, 3.5, "white_solid"),
        ),
        lane_specs_left=(
            LaneSpec(LaneType.DRIVING, 3.5, "white_dashed"),
            LaneSpec(LaneType.DRIVING, 3.5, "white_solid"),
        ),
        center_marking_preset="yellow_double",
        design_speed_kmh=80.0,
        default_fillet_radius=8.0,
    ),
    # HIGHWAY / PEDESTRIAN / BIKE: add during build.
}


def get_road_type_preset(road_type: RoadType) -> RoadTypePreset:
    raise NotImplementedError
