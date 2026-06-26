"""Connectivity view of the model. CODE_REFERENCE.md S6."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from roadup.opendrive.model.network import OpenDriveModel


class RoadGraph:
    """Endpoints/junctions as nodes, roads as edges; derived from the OpenDRIVE model."""

    def __init__(self, model: "OpenDriveModel") -> None:
        self._model = model

    def neighbors(self, road_id: str) -> list[str]:
        raise NotImplementedError

    def junction_of(self, road_id: str) -> str | None:
        raise NotImplementedError

    def rebuild(self) -> None:
        """Recompute the graph after model edits."""
        raise NotImplementedError
