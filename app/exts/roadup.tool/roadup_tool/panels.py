"""omni.ui panels: road-type preset, lane count, marking presets. CODE_REFERENCE.md S13.

Edits issue tooling commands (SetLaneCount, SetLaneMarking, ...).
"""
from __future__ import annotations

from typing import Any

import omni.ui as ui  # noqa: F401  (used when the panel is built)


class RoadUpPanel:
    def __init__(self, controller: Any) -> None:
        self._controller = controller

    def build(self) -> None:
        raise NotImplementedError
