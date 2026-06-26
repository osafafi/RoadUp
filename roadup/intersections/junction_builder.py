"""Build a Junction + connecting roads from movements. CODE_REFERENCE.md S9."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from roadup.intersections.connection_spline import ConnectionSpline
    from roadup.intersections.connectivity import Movement
    from roadup.opendrive.model.junction import Junction
    from roadup.opendrive.model.network import OpenDriveModel


class JunctionBuilder:
    """Create a junction and its connecting roads (each with a :class:`ConnectionSpline`)."""

    def __init__(self, model: "OpenDriveModel") -> None:
        self._model = model

    def build(self, junction_id: str, movements: list["Movement"]) -> "Junction":
        """For each movement author a connecting road with a default-arc spline and the
        ``<connection>``/``<laneLink>`` records, then register everything on the model."""
        raise NotImplementedError

    def connection_spline(self, junction_id: str, connection_id: str) -> "ConnectionSpline":
        """Fetch the editable spline for a connection (for the tooling layer to manipulate)."""
        raise NotImplementedError

    def rebuild_connection(self, junction_id: str, connection_id: str) -> None:
        """Re-bake one connection's geometry after its spline was edited."""
        raise NotImplementedError
