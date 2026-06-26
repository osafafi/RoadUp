"""Unit tests for roadup.segments.presets."""
import pytest

from roadup.common.types import LaneType, RoadType
from roadup.segments.presets import get_road_type_preset, load_road_type_presets


def test_loads_all_seeded_road_types() -> None:
    presets = load_road_type_presets()
    assert set(presets) == {
        RoadType.HIGHWAY, RoadType.ARTERIAL, RoadType.LOCAL,
        RoadType.PEDESTRIAN, RoadType.BIKE,
    }


def test_highway_layout_and_speed() -> None:
    p = get_road_type_preset(RoadType.HIGHWAY)
    assert p.design_speed_kmh == pytest.approx(120.0)
    assert len(p.lane_specs_right) == 4
    assert p.lane_specs_right[0].type == LaneType.DRIVING
    assert p.lane_specs_right[-1].type == LaneType.SHOULDER
    assert p.center_marking_preset == "yellow_double"


def test_lane_specs_are_tuples_of_lanespec() -> None:
    p = get_road_type_preset(RoadType.ARTERIAL)
    assert isinstance(p.lane_specs_right, tuple)
    assert p.lane_specs_right[0].width == pytest.approx(3.5)


def test_pedestrian_has_empty_left() -> None:
    p = get_road_type_preset(RoadType.PEDESTRIAN)
    assert p.lane_specs_left == ()
