"""Generate/update the USD viewport stage from the model. Owns pxr imports. CODE_REFERENCE.md S10."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from roadup.geometry.mesh import MeshData
    from roadup.opendrive.eval.sampler import Sampler
    from roadup.opendrive.model.network import OpenDriveModel


class StageGenerator:
    """Build/update the stage from model + sampler. Updates are incremental per road/junction."""

    def __init__(self, model: "OpenDriveModel", sampler: "Sampler", stage: Any = None) -> None:
        self._model = model
        self._sampler = sampler
        self._stage = stage

    def build_all(self) -> Any:  # -> Usd.Stage
        raise NotImplementedError

    def update_road(self, road_id: str) -> None:
        """Regenerate only this road's prims (surface, marking strips), preserving paths/ids."""
        raise NotImplementedError

    def update_junction(self, junction_id: str) -> None:
        raise NotImplementedError

    def write_marking_strip(
        self,
        mesh: "MeshData",
        road_id: str,
        lane_id: int,
        preset_id: str,
    ) -> None:
        raise NotImplementedError
