"""Lane connectivity resolution at a node. CODE_REFERENCE.md S9."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from roadup.common.types import TurnType

if TYPE_CHECKING:
    from roadup.opendrive.model.network import OpenDriveModel


@dataclass
class Movement:
    incoming_road: str
    incoming_lane: int
    outgoing_road: str
    outgoing_lane: int
    turn: TurnType


class ConnectivitySolver:
    """Decide which incoming lanes connect to which outgoing lanes."""

    def __init__(self, model: "OpenDriveModel") -> None:
        self._model = model

    def movements_at(self, node_road_ids: list[str]) -> list[Movement]:
        """Default movements by geometry + lane type; the user can add/remove afterwards."""
        raise NotImplementedError
