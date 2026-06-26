"""Lightweight preview geometry for in-progress edits. CODE_REFERENCE.md S11."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from roadup.opendrive.model.road import Road


class PreviewGenerator:
    """Low-res preview on a separate USD layer above committed data."""

    def road_preview(self, road: "Road") -> Any:  # -> Usd.Stage
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError
