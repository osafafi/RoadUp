"""Road-level + lane-level link resolution. Segment connections aware of lane connections.

See ARCHITECTURE.md S8 and CODE_REFERENCE.md S6.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from roadup.opendrive.model.network import OpenDriveModel


class LinkResolver:
    """Keeps road links and lane links consistent.

    Invariant: a road link is never authored without a consistent set of lane links.
    """

    def __init__(self, model: "OpenDriveModel") -> None:
        self._model = model

    def connect_roads(
        self,
        road_a: str,
        contact_a: str,
        road_b: str,
        contact_b: str,
        lane_map: dict[int, int] | None = None,
    ) -> None:
        """Author the road link AND resolve lane links.

        ``lane_map`` overrides the default; when ``None`` lanes are matched by type then
        position across the shared boundary.
        """
        raise NotImplementedError

    def default_lane_map(self, road_a: str, road_b: str) -> dict[int, int]:
        raise NotImplementedError

    def revalidate(self, road_id: str) -> list[str]:
        """Re-resolve links after a re-laning/width change; return unsatisfiable-link warnings."""
        raise NotImplementedError

    def disconnect(self, road_a: str, road_b: str) -> None:
        raise NotImplementedError
