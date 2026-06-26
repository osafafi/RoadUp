"""Draw control points from the tooling ManipulatorModel via omni.ui.scene. CODE_REFERENCE.md S13.

Each handle is an ``sc.Arc`` / ``sc.Points`` with a hover gesture (show on hover) and a drag
gesture (-> ``controller.on_drag``). Visibility comes straight from ``ManipulatorModel.visible``.
"""
from __future__ import annotations

from typing import Any

from omni.ui import scene as sc


class ManipulatorView(sc.Manipulator):
    def on_build(self) -> None:
        raise NotImplementedError

    def sync(self, model: Any) -> None:
        """Update drawn handles to match the tooling manipulator state, then ``invalidate()``."""
        raise NotImplementedError
