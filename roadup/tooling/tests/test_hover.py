"""Unit tests for roadup.tooling.hover."""
from __future__ import annotations

from roadup.tooling.hover import HoverModel
from roadup.tooling.manipulators import Handle


def test_hover_road_returns_its_control_points(simple_model) -> None:
    hover = HoverModel(simple_model)
    handles = hover.on_hover_element("road", "road_002")
    assert [h.id for h in handles] == ["cp_001", "cp_002", "cp_003"]
    assert all(h.owner == "road_002" and h.kind == "spline_point" for h in handles)


def test_hover_unknown_road_is_empty(simple_model) -> None:
    hover = HoverModel(simple_model)
    assert hover.on_hover_element("road", "road_999") == []


def test_hover_clear_returns_only_pinned(simple_model) -> None:
    hover = HoverModel(simple_model)
    pinned = [Handle(id="cp_001", position=(0.0, 0.0, 0.0), kind="spline_point", owner="road_001")]
    hover.set_pinned(pinned)
    assert hover.on_hover_clear() == pinned


def test_pinned_handles_merge_without_duplicates(simple_model) -> None:
    hover = HoverModel(simple_model)
    hover.set_pinned(
        [Handle(id="cp_001", position=(9.0, 9.0, 9.0), kind="spline_point", owner="road_002")]
    )
    handles = hover.on_hover_element("road", "road_002")
    assert [h.id for h in handles].count("cp_001") == 1
