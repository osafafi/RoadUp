"""Top-level OpenDRIVE container - the single source of truth. CODE_REFERENCE.md S3."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from roadup.common.errors import ValidationError

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
    roads: dict[str, Road] = field(default_factory=dict)
    junctions: dict[str, Junction] = field(default_factory=dict)

    def add_road(self, road: Road) -> None:
        if road.id in self.roads:
            raise ValidationError(f"duplicate road id {road.id!r}")
        self.roads[road.id] = road

    def remove_road(self, road_id: str) -> None:
        """Remove a road and cascade to junction connections that reference it."""
        if road_id not in self.roads:
            raise ValidationError(f"no road with id {road_id!r}")
        del self.roads[road_id]
        for junction in self.junctions.values():
            junction.connections = [
                c
                for c in junction.connections
                if c.incoming_road != road_id and c.connecting_road != road_id
            ]

    def get_road(self, road_id: str) -> Road:
        try:
            return self.roads[road_id]
        except KeyError as exc:
            raise ValidationError(f"no road with id {road_id!r}") from exc

    def add_junction(self, junction: Junction) -> None:
        if junction.id in self.junctions:
            raise ValidationError(f"duplicate junction id {junction.id!r}")
        self.junctions[junction.id] = junction

    def validate(self) -> list[str]:
        """Return validation messages (empty list = valid)."""
        messages: list[str] = []
        for road_id, road in self.roads.items():
            if road_id != road.id:
                messages.append(f"road keyed {road_id!r} has mismatched id {road.id!r}")
            if not road.lane_sections:
                messages.append(f"road {road_id!r} has no lane sections")
            if road.junction is not None and road.junction not in self.junctions:
                messages.append(
                    f"road {road_id!r} references unknown junction {road.junction!r}"
                )
            for end in ("predecessor", "successor"):
                link = getattr(road.link, end)
                if link is None:
                    continue
                elem_type, elem_id = link
                table = self.roads if elem_type == "road" else self.junctions
                if elem_id not in table:
                    messages.append(
                        f"road {road_id!r} {end} references unknown {elem_type} {elem_id!r}"
                    )
        for junction in self.junctions.values():
            for conn in junction.connections:
                for field_name in ("incoming_road", "connecting_road"):
                    rid = getattr(conn, field_name)
                    if rid not in self.roads:
                        messages.append(
                            f"junction {junction.id!r} connection {conn.id!r} "
                            f"{field_name} references unknown road {rid!r}"
                        )
        return messages
