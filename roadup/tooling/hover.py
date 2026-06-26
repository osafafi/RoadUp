"""Hover -> control-point visibility policy (headless, unit-tested). CODE_REFERENCE.md S11."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from roadup.tooling.manipulators import Handle


class HoverModel:
    """Decides which control points are visible given what is hovered."""

    def on_hover_element(self, kind: str, element_id: str) -> list["Handle"]:
        """Hover a road/node/junction -> the handles to show (node handles, spline points)."""
        raise NotImplementedError

    def on_hover_clear(self) -> list["Handle"]:
        """Return the handle set to show when nothing is hovered (only selection-pinned ones)."""
        raise NotImplementedError
