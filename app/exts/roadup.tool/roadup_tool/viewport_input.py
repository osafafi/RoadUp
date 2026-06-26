"""Viewport cursor/click/drag -> controller. Resolves hovered prim -> OpenDRIVE id.

CODE_REFERENCE.md S13. Hover hit-test feeds ``RoadToolController.on_hover`` every frame so the
manipulator view can show/hide control points.
"""
from __future__ import annotations

from typing import Any


class ViewportInput:
    def __init__(self, controller: Any, manipulator_view: Any) -> None:
        self._controller = controller
        self._manipulator_view = manipulator_view

    def _on_mouse_moved(self, x: float, y: float) -> None:
        # hit = self._pick(x, y)
        # model = self._controller.on_hover(hit)
        # self._manipulator_view.sync(model)
        raise NotImplementedError

    def _on_mouse_pressed(self, x: float, y: float, button: int, mods: Any) -> None:
        raise NotImplementedError

    def _on_mouse_dragged(self, x: float, y: float, mods: Any) -> None:
        raise NotImplementedError

    def _pick(self, x: float, y: float) -> dict | None:
        """Viewport hit-test -> ``roadup.usd.mapping.resolve_prim`` -> ``{kind, id, point}``."""
        raise NotImplementedError
