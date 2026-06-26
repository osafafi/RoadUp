"""Top-level OpenDRIVE container - the single source of truth. CODE_REFERENCE.md S3."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from roadup.opendrive.model.junction import Junction
    from roadup.opendrive.model.road import Road


@dataclass
class Header:
    version: str = "1.7"
    name: str = "RoadUp"
    geo_reference: str | None = None


@dataclass
class OpenDriveModel:
    """Container for the whole network. Authoritative; USD is generated from this."""

    header: Header = field(default_factory=Header)
    roads: dict[str, "Road"] = field(default_factory=dict)
    junctions: dict[str, "Junction"] = field(default_factory=dict)

    def add_road(self, road: "Road") -> None:
        raise NotImplementedError

    def remove_road(self, road_id: str) -> None:
        """Remove a road and cascade to links/junction connections that reference it."""
        raise NotImplementedError

    def get_road(self, road_id: str) -> "Road":
        raise NotImplementedError

    def add_junction(self, junction: "Junction") -> None:
        raise NotImplementedError

    def validate(self) -> list[str]:
        """Return validation messages (empty list = valid)."""
        raise NotImplementedError
