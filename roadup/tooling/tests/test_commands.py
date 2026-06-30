"""Unit tests for roadup.tooling.commands."""
from __future__ import annotations

import pytest

from roadup.common.errors import ValidationError
from roadup.common.types import RoadType
from roadup.opendrive.model.network import OpenDriveModel
from roadup.segments.lane_width import WidthLaw
from roadup.tooling.commands import (
    AddControlPoint,
    CommandStack,
    ConnectSegments,
    CreateRoad,
    MoveControlPoint,
    SetLaneCount,
    SetLaneMarking,
    SetLaneWidthLaw,
)


def _cp(road, cp_id):
    return next(c for c in road.user_data["controlPoints"] if c["id"] == cp_id)


def test_command_stack_undo_redo() -> None:
    log: list[str] = []

    class Toggle:
        def do(self) -> None:
            log.append("do")

        def undo(self) -> None:
            log.append("undo")

    stack = CommandStack()
    stack.execute(Toggle())
    assert log == ["do"] and stack.can_undo
    stack.undo()
    assert log == ["do", "undo"] and not stack.can_undo and stack.can_redo
    stack.redo()
    assert log == ["do", "undo", "do"]


def test_create_road_builds_and_undoes() -> None:
    model = OpenDriveModel()
    seen: list[str] = []
    cmd = CreateRoad(
        model,
        "road_001",
        [(0.0, 0.0, 0.0), (30.0, 10.0, 0.0), (60.0, 0.0, 0.0)],
        RoadType.LOCAL,
        on_change=seen.append,
    )
    cmd.do()
    assert seen == ["road_001"]
    road = model.get_road("road_001")
    assert road.geometry  # plan-view records baked
    assert road.length > 0.0
    assert road.user_data["splineKind"] == "catmullRom"
    assert [cp["id"] for cp in road.user_data["controlPoints"]] == ["cp_001", "cp_002", "cp_003"]
    cmd.undo()
    assert "road_001" not in model.roads


def test_create_road_needs_two_points() -> None:
    with pytest.raises(ValidationError):
        CreateRoad(OpenDriveModel(), "road_001", [(0.0, 0.0, 0.0)], RoadType.LOCAL)


def test_move_control_point_rebakes_and_undoes(simple_model) -> None:
    road = simple_model.get_road("road_002")
    seen: list[str] = []
    cmd = MoveControlPoint(simple_model, "road_002", "cp_002", (20.0, 70.0, 0.0),
                           on_change=seen.append)
    before_len = road.length
    cmd.do()
    assert seen == ["road_002"]
    assert _cp(road, "cp_002")["pos"] == [20.0, 70.0, 0.0]
    assert road.length != before_len  # geometry re-baked
    cmd.undo()
    assert _cp(road, "cp_002")["pos"] == [20.0, 48.0, 0.0]
    assert road.length == pytest.approx(before_len)


def test_add_control_point_then_undo(simple_model) -> None:
    road = simple_model.get_road("road_002")
    n0 = len(road.user_data["controlPoints"])
    cmd = AddControlPoint(simple_model, "road_002", 0.5)
    cmd.do()
    assert len(road.user_data["controlPoints"]) == n0 + 1
    cmd.undo()
    assert len(road.user_data["controlPoints"]) == n0


def test_set_lane_marking_roundtrip(simple_model) -> None:
    road = simple_model.get_road("road_001")
    lane = road.lane_section_at(0.0).lane(1)
    old_preset = lane.user_data.get("markingPreset", "")
    cmd = SetLaneMarking(simple_model, "road_001", 1, "yellow_double")
    cmd.do()
    assert lane.user_data["markingPreset"] == "yellow_double"
    assert lane.road_marks  # a mark was authored
    cmd.undo()
    assert lane.user_data["markingPreset"] == old_preset


def test_set_lane_width_law_rebakes_records(simple_model) -> None:
    road = simple_model.get_road("road_001")
    lane = road.lane_section_at(0.0).lane(-1)
    cmd = SetLaneWidthLaw(simple_model, "road_001", -1, WidthLaw.taper(0.0, 3.0, 30.0, 4.5))
    cmd.do()
    assert lane.user_data["widthLaw"]["kind"] == "linear"
    assert len(lane.widths) >= 1
    cmd.undo()
    assert lane.user_data["widthLaw"]["kind"] == "constant"


def test_set_lane_count_grows_and_undoes(simple_model) -> None:
    road = simple_model.get_road("road_001")
    section = road.lane_section_at(0.0)
    original = len(section.right)
    cmd = SetLaneCount(simple_model, "road_001", "right", original + 2)
    cmd.do()
    assert len(section.right) == original + 2
    assert [ln.id for ln in section.right] == [-(i + 1) for i in range(original + 2)]
    cmd.undo()
    assert len(section.right) == original


def test_connect_segments_links_and_undoes(simple_model) -> None:
    cmd = ConnectSegments(simple_model, "road_001", "end", "road_002", "start")
    cmd.do()
    assert simple_model.get_road("road_001").link.successor is not None
    cmd.undo()
    assert simple_model.get_road("road_001").link.successor is None


def test_move_on_arc_reference_line_raises(simple_model) -> None:
    road = simple_model.get_road("road_001")
    road.user_data["splineKind"] = "arc"  # arcs cannot be rebaked from control points
    cmd = MoveControlPoint(simple_model, "road_001", "cp_001", (1.0, 1.0, 0.0))
    with pytest.raises(ValidationError):
        cmd.do()
