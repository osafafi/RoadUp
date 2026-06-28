"""Build a Junction + connecting roads from movements. CODE_REFERENCE.md S9.

Each movement (incoming lane -> outgoing lane) becomes a **connecting road** whose reference line is
a :class:`~roadup.intersections.connection_spline.ConnectionSpline` (default circular arc, editable
to a ``paramPoly3``). The connecting road carries a single driving lane linked to the incoming and
outgoing lanes; the junction records the ``<connection>``/``<laneLink>``. See ARCHITECTURE.md S6.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from roadup.common.config import Config
from roadup.common.errors import IntersectionError
from roadup.common.ids import IdAllocator
from roadup.common.types import LaneType, Vec3
from roadup.intersections.connection_spline import ConnectionSpline
from roadup.intersections.connectivity import ConnectivitySolver
from roadup.opendrive.eval.sampler import Sampler
from roadup.opendrive.model.junction import Connection, Junction, LaneLinkPair
from roadup.opendrive.model.road import Lane, LaneLink, LaneSection, Road, RoadLink
from roadup.segments.lane_width import WidthLaw

if TYPE_CHECKING:
    from roadup.intersections.connectivity import Movement, RoadEnd
    from roadup.opendrive.model.network import OpenDriveModel

# Structural invariant (not a tunable): all connecting-road lanes are a single right (-1) driving
# lane, so the reference line anchors on the lane's inner edge. The fallback lane *width* is a knob
# (Config.connecting_lane_default_width).
_CONNECTING_LANE_ID = -1


class JunctionBuilder:
    """Create a junction and its connecting roads (each with a :class:`ConnectionSpline`)."""

    def __init__(self, model: OpenDriveModel, *, config: Config | None = None) -> None:
        self._model = model
        self._config = config or Config()
        self._sampler = Sampler(model, config=self._config)
        self._ids = IdAllocator()
        for road_id in model.roads:
            self._ids.reserve(road_id)
        # Editable splines + their connecting-road ids, keyed by (junction_id, connection_id).
        self._splines: dict[tuple[str, str], ConnectionSpline] = {}
        self._conn_roads: dict[tuple[str, str], str] = {}

    def build(self, junction_id: str, movements: list[Movement]) -> Junction:
        """Author a connecting road + ``<connection>``/``<laneLink>`` per movement, register all."""
        if not movements:
            raise IntersectionError(f"junction {junction_id!r} needs at least one movement")
        node_roads = sorted(
            {m.incoming_road for m in movements} | {m.outgoing_road for m in movements}
        )
        ends = ConnectivitySolver(self._model, config=self._config).road_ends(node_roads)

        junction = Junction(id=junction_id)
        for i, mv in enumerate(movements):
            conn_id = f"connection_{i:03d}"
            road, spline = self._build_connecting_road(junction_id, mv, ends)
            self._model.add_road(road)
            self._splines[(junction_id, conn_id)] = spline
            self._conn_roads[(junction_id, conn_id)] = road.id
            junction.connections.append(
                Connection(
                    id=conn_id,
                    incoming_road=mv.incoming_road,
                    connecting_road=road.id,
                    contact_point="start",
                    lane_links=[
                        LaneLinkPair(from_lane=mv.incoming_lane, to_lane=_CONNECTING_LANE_ID)
                    ],
                )
            )
        self._model.add_junction(junction)
        return junction

    def connection_spline(self, junction_id: str, connection_id: str) -> ConnectionSpline:
        """Fetch the editable spline for a connection (for the tooling layer to manipulate)."""
        try:
            return self._splines[(junction_id, connection_id)]
        except KeyError as exc:
            raise IntersectionError(
                f"no connection {connection_id!r} in junction {junction_id!r}"
            ) from exc

    def rebuild_connection(self, junction_id: str, connection_id: str) -> None:
        """Re-bake one connection's geometry after its spline was edited."""
        spline = self.connection_spline(junction_id, connection_id)
        road = self._model.get_road(self._conn_roads[(junction_id, connection_id)])
        road.geometry = spline.to_geometry_records()
        road.length = sum(g.length for g in road.geometry)
        road.user_data = spline.userdata()

    # --- internals --------------------------------------------------------------------
    def _build_connecting_road(
        self, junction_id: str, mv: Movement, ends: dict[str, RoadEnd]
    ) -> tuple[Road, ConnectionSpline]:
        a, b = ends[mv.incoming_road], ends[mv.outgoing_road]
        # Anchor the connecting road's reference line on each lane's INNER edge: a connecting road
        # carries one right (negative) lane spanning t in [-w, 0], so its reference line is the
        # lane's left/inner boundary. Anchoring on the lane centre would shift it half a width.
        start = self._lane_anchor(mv.incoming_road, mv.incoming_lane, a.contact)
        end = self._lane_anchor(mv.outgoing_road, mv.outgoing_lane, b.contact)
        start_tan = (float(a.approach[0]), float(a.approach[1]), 0.0)
        end_tan = (float(b.departure[0]), float(b.departure[1]), 0.0)
        spline = ConnectionSpline.default_arc(
            start,
            start_tan,
            end,
            end_tan,
            tangent_tol=self._config.connection_tangent_tol,
            upgrade_samples=self._config.connection_upgrade_samples,
        )

        geometry = spline.to_geometry_records()
        length = sum(g.length for g in geometry)
        # Taper the connecting lane from incoming to outgoing width so both ends align.
        w_in = self._lane_width(mv.incoming_road, mv.incoming_lane)
        w_out = self._lane_width(mv.outgoing_road, mv.outgoing_lane)
        law = (
            WidthLaw.constant(w_in)
            if abs(w_in - w_out) < 1e-9 or length <= 0.0
            else WidthLaw.taper(0.0, w_in, length, w_out)
        )
        lane = Lane(
            id=_CONNECTING_LANE_ID,
            type=LaneType.DRIVING,
            widths=law.bake_records(),
            link=LaneLink(predecessor=mv.incoming_lane, successor=mv.outgoing_lane),
        )
        road = Road(
            id=self._ids.next("road"),
            length=sum(g.length for g in geometry),
            geometry=geometry,
            lane_sections=[LaneSection(s=0.0, center=Lane(id=0, type=LaneType.NONE), right=[lane])],
            link=RoadLink(
                predecessor=("road", mv.incoming_road),
                successor=("road", mv.outgoing_road),
            ),
            junction=junction_id,
            user_data=spline.userdata(),
        )
        return road, spline

    def _lane_anchor(self, road_id: str, lane_id: int, contact: str) -> Vec3:
        """The lane's inner-boundary point at the node contact (toward the parent ref line)."""
        road = self._model.get_road(road_id)
        bounds = self._sampler.lane_boundaries(road_id, 0.0, road.length)
        lb = next((b for b in bounds if b.lane_id == lane_id), None)
        if lb is None or not lb.inner:
            raise IntersectionError(f"lane {lane_id} of road {road_id!r} has no sampled boundary")
        return lb.inner[0 if contact == "start" else -1]

    def _lane_width(self, road_id: str, lane_id: int) -> float:
        section = self._model.get_road(road_id).lane_sections[0]
        lane = section.lane(lane_id)
        return lane.widths[0].a if lane.widths else self._config.connecting_lane_default_width
