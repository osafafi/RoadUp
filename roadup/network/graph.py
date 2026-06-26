"""Connectivity view of the model. CODE_REFERENCE.md S6."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from roadup.opendrive.model.network import OpenDriveModel


class RoadGraph:
    """Endpoints/junctions as nodes, roads as edges; derived from the OpenDRIVE model.

    Adjacency is the set of roads a road links to directly (road-type ``<link>`` ends) plus the
    sibling connecting roads of any junction it links into. Call :meth:`rebuild` after model edits.
    """

    def __init__(self, model: OpenDriveModel) -> None:
        self._model = model
        self._adjacency: dict[str, set[str]] = {}
        self.rebuild()

    def neighbors(self, road_id: str) -> list[str]:
        if road_id not in self._model.roads:
            raise KeyError(f"no road {road_id!r}")
        return sorted(self._adjacency.get(road_id, set()))

    def junction_of(self, road_id: str) -> str | None:
        return self._model.get_road(road_id).junction

    def rebuild(self) -> None:
        """Recompute the graph after model edits."""
        adjacency: dict[str, set[str]] = {rid: set() for rid in self._model.roads}
        # Roads grouped by the junction they belong to (connecting roads share a node).
        in_junction: dict[str, list[str]] = {}
        for rid, road in self._model.roads.items():
            if road.junction is not None:
                in_junction.setdefault(road.junction, []).append(rid)

        for rid, road in self._model.roads.items():
            for end in (road.link.predecessor, road.link.successor):
                if end is None:
                    continue
                elem_type, elem_id = end
                if elem_type == "road" and elem_id in adjacency:
                    adjacency[rid].add(elem_id)
                    adjacency[elem_id].add(rid)
                elif elem_type == "junction":
                    for sibling in in_junction.get(elem_id, ()):
                        if sibling != rid:
                            adjacency[rid].add(sibling)
                            adjacency[sibling].add(rid)
        self._adjacency = adjacency
