"""UI-agnostic interaction controller. The Kit extension drives these methods. CODE_REFERENCE.md S11."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from roadup.common.types import Vec3

if TYPE_CHECKING:
    from roadup.opendrive.model.network import OpenDriveModel
    from roadup.tooling.manipulators import ManipulatorModel


class RoadToolController:
    """Headless controller. No ``omni.*`` imports - the app binds input/render to this."""

    TOOL_MODES = ("DRAW_ROAD", "EDIT_SPLINE", "EDIT_INTERSECTION", "EDIT_LANES", "INSPECT")

    def __init__(self, model: "OpenDriveModel") -> None:
        self._model = model

    def set_mode(self, mode: str) -> None:
        raise NotImplementedError

    # --- input (already hit-tested by the app; ids resolved via usd.mapping) -----------
    def on_hover(self, hit: dict | None) -> "ManipulatorModel":
        """``hit`` = ``{kind, id, point}`` or ``None``. Returns the manipulator state to render."""
        raise NotImplementedError

    def on_click(self, hit: dict, modifiers: dict) -> None:
        raise NotImplementedError

    def on_drag(self, world_point: Vec3, modifiers: dict) -> None:
        raise NotImplementedError

    def on_release(self, world_point: Vec3, modifiers: dict) -> None:
        raise NotImplementedError

    # --- render state ------------------------------------------------------------------
    def manipulators(self) -> "ManipulatorModel":
        raise NotImplementedError

    def preview(self) -> Any:  # -> Usd.Stage
        raise NotImplementedError
