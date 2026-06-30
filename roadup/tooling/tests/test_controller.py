"""Unit tests for roadup.tooling.controller."""
from __future__ import annotations

import pytest

from roadup.common.errors import ValidationError
from roadup.opendrive.model.network import OpenDriveModel
from roadup.tooling.controller import RoadToolController


def test_hover_populates_handles_in_road_context(simple_model) -> None:
    ctrl = RoadToolController(simple_model)
    manip = ctrl.on_hover({"kind": "road", "id": "road_002"})
    assert [h.id for h in manip.visible] == ["cp_001", "cp_002", "cp_003"]
    assert manip.hovered == "road_002" or manip.hovered is None  # id is the road, not a handle


def test_scene_context_suppresses_road_handles(simple_model) -> None:
    ctrl = RoadToolController(simple_model)
    ctrl.set_context("SCENE")
    manip = ctrl.on_hover({"kind": "road", "id": "road_002"})
    assert manip.visible == []


def test_unknown_context_and_mode_raise(simple_model) -> None:
    ctrl = RoadToolController(simple_model)
    with pytest.raises(ValidationError):
        ctrl.set_context("WORLD")
    with pytest.raises(ValidationError):
        ctrl.set_mode("FLY")


def test_drag_release_commits_undoable_move(simple_model) -> None:
    ctrl = RoadToolController(simple_model)
    ctrl.on_hover({"kind": "road", "id": "road_002"})
    ctrl.on_click({"kind": "spline_point", "id": "cp_002"}, modifiers={})
    ctrl.on_drag((20.0, 80.0, 0.0), modifiers={})
    ctrl.on_release((20.0, 80.0, 0.0), modifiers={})

    cps = simple_model.get_road("road_002").user_data["controlPoints"]
    cp = next(c for c in cps if c["id"] == "cp_002")
    assert cp["pos"] == [20.0, 80.0, 0.0]
    ctrl.undo()
    assert cp["pos"] == [20.0, 48.0, 0.0]
    ctrl.redo()
    assert cp["pos"] == [20.0, 80.0, 0.0]


def test_regen_callback_hits_stage_generator(simple_model) -> None:
    calls: list[str] = []

    class FakeStage:
        def update_road(self, road_id: str) -> None:
            calls.append(road_id)

    ctrl = RoadToolController(simple_model, stage=FakeStage())  # type: ignore[arg-type]
    ctrl.on_hover({"kind": "road", "id": "road_002"})
    ctrl.on_click({"kind": "spline_point", "id": "cp_001"}, modifiers={})
    ctrl.on_release((1.0, 41.0, 0.0), modifiers={})
    assert calls == ["road_002"]


def test_draw_road_cycle_creates_and_undoes() -> None:
    model = OpenDriveModel()
    ctrl = RoadToolController(model)
    ctrl.set_mode("DRAW_ROAD")
    for p in [(0.0, 0.0, 0.0), (30.0, 10.0, 0.0), (60.0, 0.0, 0.0)]:
        ctrl.add_draft_point(p)
    assert len(ctrl.draft_points()) == 3
    road_id = ctrl.finish_draw()
    assert road_id == "road_001"
    assert road_id in model.roads
    assert ctrl.draft_points() == []  # draft cleared on commit
    ctrl.undo()
    assert "road_001" not in model.roads


def test_draw_road_ignores_points_outside_draw_mode() -> None:
    ctrl = RoadToolController(OpenDriveModel())  # default mode INSPECT
    ctrl.add_draft_point((0.0, 0.0, 0.0))
    assert ctrl.draft_points() == []


def test_finish_draw_with_too_few_points_is_noop() -> None:
    model = OpenDriveModel()
    ctrl = RoadToolController(model)
    ctrl.set_mode("DRAW_ROAD")
    ctrl.add_draft_point((0.0, 0.0, 0.0))
    assert ctrl.finish_draw() is None
    assert not model.roads
    assert ctrl.draft_points() == []  # cleared even when not enough points


def test_cancel_draw_clears_draft() -> None:
    ctrl = RoadToolController(OpenDriveModel())
    ctrl.set_mode("DRAW_ROAD")
    ctrl.add_draft_point((0.0, 0.0, 0.0))
    ctrl.add_draft_point((10.0, 0.0, 0.0))
    ctrl.cancel_draw()
    assert ctrl.draft_points() == []


def test_draw_road_regen_creates_then_removes_prims() -> None:
    created: list[str] = []
    removed: list[str] = []

    class FakeStage:
        def update_road(self, road_id: str) -> None:
            created.append(road_id)

        def remove_road(self, road_id: str) -> None:
            removed.append(road_id)

    model = OpenDriveModel()
    ctrl = RoadToolController(model, stage=FakeStage())  # type: ignore[arg-type]
    ctrl.set_mode("DRAW_ROAD")
    ctrl.add_draft_point((0.0, 0.0, 0.0))
    ctrl.add_draft_point((60.0, 0.0, 0.0))
    road_id = ctrl.finish_draw()
    assert created == [road_id]
    ctrl.undo()
    assert removed == [road_id]
