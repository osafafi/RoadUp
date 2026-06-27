"""Hover -> control-point visibility policy (headless, unit-tested). CODE_REFERENCE.md S11.

Pure policy over the model: given what the cursor hovers, decide which control-point handles the
app should draw. No ``omni.*`` — the app renders the returned :class:`Handle` list.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from roadup.tooling.manipulators import Handle

if TYPE_CHECKING:
    from roadup.opendrive.model.network import OpenDriveModel


class HoverModel:
    """Decides which control points are visible given what is hovered."""

    def __init__(self, model: OpenDriveModel) -> None:
        self._model = model
        #: Handles pinned by the current selection (shown even on hover-out).
        self._pinned: list[Handle] = []

    def set_pinned(self, handles: list[Handle]) -> None:
        self._pinned = list(handles)

    def on_hover_element(self, kind: str, element_id: str) -> list[Handle]:
        """Hover a road/node/junction -> the handles to show (node handles, spline points)."""
        if kind in ("road", "lane", "node", "spline_point"):
            handles = self._road_handles(element_id)
        elif kind == "junction":
            handles = self._junction_handles(element_id)
        else:
            handles = []
        return self._merge(handles)

    def on_hover_clear(self) -> list[Handle]:
        """Return the handle set to show when nothing is hovered (only selection-pinned ones)."""
        return list(self._pinned)

    # --- internals --------------------------------------------------------------------
    def _merge(self, handles: list[Handle]) -> list[Handle]:
        seen = {h.id for h in handles}
        return handles + [h for h in self._pinned if h.id not in seen]

    def _road_handles(self, road_id: str) -> list[Handle]:
        road = self._model.roads.get(road_id)
        if road is None:
            return []
        return self._handles_for_road(road_id, owner=road_id)

    def _junction_handles(self, junction_id: str) -> list[Handle]:
        junction = self._model.junctions.get(junction_id)
        if junction is None:
            return []
        handles: list[Handle] = []
        for conn in junction.connections:
            road_id = conn.connecting_road
            if road_id in self._model.roads:
                # owner is the connecting road that carries the spline, so an edit can rebake it.
                handles.extend(self._handles_for_road(road_id, owner=road_id))
        return handles

    def _handles_for_road(self, road_id: str, owner: str) -> list[Handle]:
        road = self._model.roads[road_id]
        control_points = road.user_data.get("controlPoints", [])
        return [
            Handle(
                id=cp["id"],
                position=tuple(cp["pos"]),  # type: ignore[arg-type]
                kind="spline_point",
                owner=owner,
            )
            for cp in control_points
            if "id" in cp and "pos" in cp
        ]
