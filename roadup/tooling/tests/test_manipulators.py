"""Unit tests for roadup.tooling.manipulators."""
from __future__ import annotations

from roadup.tooling.manipulators import Handle, ManipulatorModel


def _h(hid: str) -> Handle:
    return Handle(id=hid, position=(0.0, 0.0, 0.0), kind="spline_point", owner="road_001")


def test_set_handles_replaces_visible() -> None:
    m = ManipulatorModel()
    m.set_handles([_h("cp_001"), _h("cp_002")])
    assert [h.id for h in m.visible] == ["cp_001", "cp_002"]


def test_set_handles_drops_stale_selection_and_hover() -> None:
    m = ManipulatorModel()
    m.set_handles([_h("cp_001")])
    m.selected = "cp_001"
    m.hovered = "cp_001"
    m.set_handles([_h("cp_002")])  # cp_001 no longer present
    assert m.selected is None
    assert m.hovered is None


def test_handle_lookup() -> None:
    m = ManipulatorModel()
    m.set_handles([_h("cp_001"), _h("cp_002")])
    found = m.handle("cp_002")
    assert found is not None and found.id == "cp_002"
    assert m.handle("missing") is None
