"""Unit tests for roadup.tooling.controller."""
from __future__ import annotations

import pytest

from roadup.common.errors import ValidationError
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
