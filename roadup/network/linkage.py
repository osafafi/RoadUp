"""Road-level + lane-level link resolution. Segment connections aware of lane connections.

See ARCHITECTURE.md S8 and CODE_REFERENCE.md S6.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from roadup.common.errors import TopologyError
from roadup.common.types import LaneType
from roadup.opendrive.model.road import LaneSection, Road, RoadLink

if TYPE_CHECKING:
    from roadup.opendrive.model.network import OpenDriveModel

_CONTACTS = ("start", "end")


class LinkResolver:
    """Keeps road links and lane links consistent.

    Invariant: a road link is never authored without a consistent set of lane links.

    Lane matching (``default_lane_map``) is intentionally simple — it pairs **driving** lanes that
    share the same signed id across the boundary. This suits same-direction roads joined end→start;
    sign flips (end→end), merges, and lane-count changes are left to an explicit ``lane_map``.
    """

    def __init__(self, model: OpenDriveModel) -> None:
        self._model = model

    def connect_roads(
        self,
        road_a: str,
        contact_a: str,
        road_b: str,
        contact_b: str,
        lane_map: dict[int, int] | None = None,
    ) -> None:
        """Author the road link AND resolve lane links."""
        self._check_contact(contact_a)
        self._check_contact(contact_b)
        a = self._model.get_road(road_a)
        b = self._model.get_road(road_b)

        mapping = lane_map if lane_map is not None else self.default_lane_map(road_a, road_b)
        sec_a = self._boundary_section(a, contact_a)
        sec_b = self._boundary_section(b, contact_b)
        # Validate the mapping fully before mutating anything (keep the invariant atomic).
        for a_id, b_id in mapping.items():
            sec_a.lane(a_id)
            sec_b.lane(b_id)

        self._set_road_link(a, contact_a, ("road", road_b))
        self._set_road_link(b, contact_b, ("road", road_a))
        for a_id, b_id in mapping.items():
            self._set_lane_link(sec_a, a_id, contact_a, b_id)
            self._set_lane_link(sec_b, b_id, contact_b, a_id)

    def default_lane_map(self, road_a: str, road_b: str) -> dict[int, int]:
        a_ids = self._driving_ids(self._model.get_road(road_a))
        b_ids = self._driving_ids(self._model.get_road(road_b))
        return {lid: lid for lid in sorted(a_ids & b_ids, reverse=True)}

    def revalidate(self, road_id: str) -> list[str]:
        """Re-check this road's links after a re-laning/width change; return warnings."""
        warnings: list[str] = []
        road = self._model.get_road(road_id)
        for contact, end in (("start", road.link.predecessor), ("end", road.link.successor)):
            if end is None or end[0] != "road":
                continue
            other_id = end[1]
            if other_id not in self._model.roads:
                warnings.append(f"{road_id}: {contact} links missing road {other_id}")
                continue
            other = self._model.get_road(other_id)
            section = self._boundary_section(road, contact)
            for lane in section.left + section.right:
                target = lane.link.successor if contact == "end" else lane.link.predecessor
                if target is None:
                    continue
                if not self._other_has_lane(other, target):
                    warnings.append(
                        f"{road_id} lane {lane.id} -> {other_id} lane {target}: target missing"
                    )
        return warnings

    def disconnect(self, road_a: str, road_b: str) -> None:
        for src, dst in ((road_a, road_b), (road_b, road_a)):
            road = self._model.get_road(src)
            for contact, end in (("start", road.link.predecessor), ("end", road.link.successor)):
                if end == ("road", dst):
                    self._clear_road_link(road, contact)
                    self._clear_lane_links(self._boundary_section(road, contact), contact)

    # --- internals --------------------------------------------------------------------
    @staticmethod
    def _check_contact(contact: str) -> None:
        if contact not in _CONTACTS:
            raise TopologyError(f"contact must be one of {_CONTACTS}, got {contact!r}")

    @staticmethod
    def _boundary_section(road: Road, contact: str) -> LaneSection:
        if not road.lane_sections:
            raise TopologyError(f"road {road.id} has no lane sections to link")
        return road.lane_sections[0] if contact == "start" else road.lane_sections[-1]

    @staticmethod
    def _driving_ids(road: Road) -> set[int]:
        if not road.lane_sections:
            return set()
        section = road.lane_sections[0]
        return {ln.id for ln in section.left + section.right if ln.type == LaneType.DRIVING}

    @staticmethod
    def _other_has_lane(road: Road, lane_id: int) -> bool:
        return any(lane_id in sec.lane_ids() for sec in road.lane_sections)

    @staticmethod
    def _set_road_link(road: Road, contact: str, end: tuple[str, str]) -> None:
        if road.link is None:  # defensive; Road always defaults a RoadLink
            road.link = RoadLink()
        if contact == "end":
            road.link.successor = end
        else:
            road.link.predecessor = end

    @staticmethod
    def _clear_road_link(road: Road, contact: str) -> None:
        if contact == "end":
            road.link.successor = None
        else:
            road.link.predecessor = None

    @staticmethod
    def _set_lane_link(section: LaneSection, lane_id: int, contact: str, other_id: int) -> None:
        lane = section.lane(lane_id)
        if contact == "end":
            lane.link.successor = other_id
        else:
            lane.link.predecessor = other_id

    @staticmethod
    def _clear_lane_links(section: LaneSection, contact: str) -> None:
        for lane in section.left + section.right:
            if contact == "end":
                lane.link.successor = None
            else:
                lane.link.predecessor = None
