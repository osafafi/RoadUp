"""model -> .xodr via scenariogeneration. Owns all scenariogeneration imports. CODE_REFERENCE.md S4."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from roadup.opendrive.model.network import OpenDriveModel


class ScenarioGenerationWriter:
    """Translate the model into ``scenariogeneration.xodr`` objects and write the file.

    All editing intent that OpenDRIVE cannot express is attached as ``<userData>`` (see
    :mod:`roadup.opendrive.io.userdata`).
    """

    def write(self, model: "OpenDriveModel", xodr_path: str) -> None:
        # import scenariogeneration here, never at module top.
        raise NotImplementedError
