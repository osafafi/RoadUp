"""Unit tests for roadup.opendrive.eval.sampler (pure-Python model sampling)."""
import math

from roadup.common.types import GeometryType, LaneType
from roadup.opendrive.eval.sampler import Sampler
from roadup.opendrive.model.network import OpenDriveModel
from roadup.opendrive.model.road import Geometry, Lane, LaneSection, Road, WidthRecord


def _two_lane_road(geom: Geometry, *, left_w: float = 3.5, right_w: float = 3.5) -> OpenDriveModel:
    section = LaneSection(
        s=0.0,
        center=Lane(id=0, type=LaneType.NONE),
        left=[Lane(id=1, type=LaneType.DRIVING, widths=[WidthRecord(s_offset=0.0, a=left_w)])],
        right=[Lane(id=-1, type=LaneType.DRIVING, widths=[WidthRecord(s_offset=0.0, a=right_w)])],
    )
    road = Road(id="road_001", length=geom.length, geometry=[geom], lane_sections=[section])
    model = OpenDriveModel()
    model.add_road(road)
    return model


def test_reference_frames_on_straight() -> None:
    geom = Geometry(s=0.0, x=0.0, y=0.0, hdg=0.0, length=40.0, type=GeometryType.LINE)
    frames = Sampler(_two_lane_road(geom), step=5.0).reference_frames("road_001")
    assert len(frames) == 9                       # 0..40 every 5 m, inclusive
    assert math.isclose(frames[-1].s, 40.0)
    assert math.isclose(frames[-1].position[0], 40.0, abs_tol=1e-9)
    assert all(math.isclose(f.position[1], 0.0, abs_tol=1e-9) for f in frames)


def test_arc_frames_curve_left() -> None:
    geom = Geometry(s=0.0, x=0.0, y=0.0, hdg=0.0, length=62.0,
                    type=GeometryType.ARC, params={"curvature": 1.0 / 80.0})
    frames = Sampler(_two_lane_road(geom), step=2.0).reference_frames("road_001")
    # A left turn (positive curvature) bends +y and the heading increases along the road.
    assert frames[-1].position[1] > frames[0].position[1]
    assert math.atan2(frames[-1].tangent[1], frames[-1].tangent[0]) > 0.0


def test_lane_boundary_offsets_match_widths() -> None:
    geom = Geometry(s=0.0, x=0.0, y=0.0, hdg=0.0, length=20.0, type=GeometryType.LINE)
    s = Sampler(_two_lane_road(geom, left_w=3.0, right_w=4.0), step=5.0)
    boundaries = {b.lane_id: b for b in s.lane_boundaries("road_001", 0.0, 20.0)}
    assert set(boundaries) == {1, -1}
    # Inner boundary hugs the reference line; outer sits a lane-width out, on the correct side.
    left = boundaries[1]
    assert math.isclose(left.inner[0][1], 0.0, abs_tol=1e-9)
    assert math.isclose(left.outer[0][1], 3.0, abs_tol=1e-9)
    right = boundaries[-1]
    assert math.isclose(right.outer[0][1], -4.0, abs_tol=1e-9)


def test_lane_boundary_honours_width_taper() -> None:
    geom = Geometry(s=0.0, x=0.0, y=0.0, hdg=0.0, length=25.0, type=GeometryType.LINE)
    section = LaneSection(
        s=0.0,
        center=Lane(id=0, type=LaneType.NONE),
        right=[Lane(id=-1, type=LaneType.DRIVING,
                    widths=[WidthRecord(s_offset=0.0, a=3.0, b=0.04)])],  # widens 4 cm/m
    )
    road = Road(id="road_001", length=25.0, geometry=[geom], lane_sections=[section])
    model = OpenDriveModel()
    model.add_road(road)
    b = Sampler(model, step=5.0).lane_boundaries("road_001", 0.0, 25.0)[0]
    assert math.isclose(abs(b.outer[0][1]), 3.0, abs_tol=1e-9)            # a at s=0
    assert math.isclose(abs(b.outer[-1][1]), 3.0 + 0.04 * 25.0, abs_tol=1e-9)  # a + b*25


def test_road_surface_polylines_span_all_lanes() -> None:
    geom = Geometry(s=0.0, x=0.0, y=0.0, hdg=0.0, length=10.0, type=GeometryType.LINE)
    left, right = Sampler(_two_lane_road(geom, left_w=3.5, right_w=3.5),
                          step=5.0).road_surface_polylines("road_001")
    assert math.isclose(left[0][1], 3.5, abs_tol=1e-9)
    assert math.isclose(right[0][1], -3.5, abs_tol=1e-9)
