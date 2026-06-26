"""Unit tests for roadup.segments.builder."""
import math

import pytest

from roadup.common.types import GeometryType, LaneType, RoadType
from roadup.geometry.splines import ControlPoint, Spline
from roadup.segments.builder import SegmentBuilder, bake_reference_line
from roadup.segments.lane_width import WidthLaw


def _line(length: float = 60.0) -> Spline:
    return Spline(
        points=[
            ControlPoint(position=(0.0, 0.0, 0.0), id="cp_001"),
            ControlPoint(position=(length, 0.0, 0.0), id="cp_002"),
        ],
        kind="line",
    )


# --- bake_reference_line ----------------------------------------------------------------
def test_bake_line_single_record() -> None:
    records = bake_reference_line(_line(60.0))
    assert len(records) == 1
    assert records[0].type == GeometryType.LINE
    assert records[0].length == pytest.approx(60.0)
    assert records[0].hdg == pytest.approx(0.0)


def test_bake_arc_curvature_sign_and_magnitude() -> None:
    # Quarter-circle-ish left turn: start heading +x, curving up (+y).
    arc = Spline.circular_arc(
        start=(0.0, 0.0, 0.0), start_tangent=(1.0, 0.0, 0.0),
        end=(40.0, 40.0, 0.0), end_tangent=(0.0, 1.0, 0.0),
    )
    records = bake_reference_line(arc)
    assert len(records) == 1
    assert records[0].type == GeometryType.ARC
    assert records[0].params["curvature"] > 0.0  # left turn = +ve curvature
    radius = 1.0 / abs(records[0].params["curvature"])
    assert records[0].length == pytest.approx(radius * (math.pi / 2), rel=1e-6)


def test_bake_cubic_one_record_per_segment() -> None:
    sp = Spline(
        points=[
            ControlPoint(position=(0.0, 0.0, 0.0), id="cp_001"),
            ControlPoint(position=(20.0, 8.0, 0.0), id="cp_002"),
            ControlPoint(position=(40.0, 0.0, 0.0), id="cp_003"),
        ],
        kind="catmullRom",
    )
    records = bake_reference_line(sp)
    assert len(records) == 2
    assert all(r.type == GeometryType.PARAM_POLY3 for r in records)
    # Local frame: aU/aV are zero and the first record starts at the spline origin.
    assert records[0].params["aU"] == 0.0
    assert records[0].params["aV"] == 0.0
    assert (records[0].x, records[0].y) == pytest.approx((0.0, 0.0))


# --- SegmentBuilder ---------------------------------------------------------------------
def test_highway_build_lane_layout() -> None:
    road = SegmentBuilder(RoadType.HIGHWAY).with_reference_line(_line(50.0)).build("road_001")
    section = road.lane_sections[0]
    assert section.center is not None and section.center.id == 0
    assert [ln.id for ln in section.right] == [-1, -2, -3, -4]
    assert [ln.id for ln in section.left] == [1, 2, 3, 4]
    assert section.right[-1].type == LaneType.SHOULDER
    assert road.length == pytest.approx(50.0)


def test_lanes_carry_width_and_marks() -> None:
    road = SegmentBuilder(RoadType.LOCAL).with_reference_line(_line()).build("road_002")
    lane = road.lane_sections[0].right[0]
    assert lane.widths and lane.widths[0].a == pytest.approx(3.25)
    assert lane.road_marks and lane.road_marks[0].preset_id == "white_solid"
    assert lane.user_data["markingPreset"] == "white_solid"


def test_lane_count_override_and_width_law() -> None:
    road = (
        SegmentBuilder(RoadType.ARTERIAL)
        .with_reference_line(_line())
        .with_lane_count(left=1, right=3)
        .set_lane_width_law(-1, WidthLaw.taper(0.0, 3.5, 20.0, 4.5))
        .build("road_003")
    )
    section = road.lane_sections[0]
    assert len(section.left) == 1
    assert len(section.right) == 3  # extended beyond the 2 preset specs
    assert section.right[0].widths[0].b == pytest.approx((4.5 - 3.5) / 20.0)


def test_build_without_reference_line_raises() -> None:
    from roadup.common.errors import ValidationError

    with pytest.raises(ValidationError):
        SegmentBuilder(RoadType.LOCAL).build("road_004")
