"""Lane connectivity resolution at a node. CODE_REFERENCE.md S9.

Decides *which* incoming lanes connect to *which* outgoing lanes when several roads meet at a node.
This is independent of the connection *shape* (that is the connection spline, see
:mod:`roadup.intersections.connection_spline`): connectivity defines the set of connecting roads,
the spline defines each one's path.

Default policy (geometry-aware, right-hand traffic / RHT, UAE-GCC):

* Each road touches the node at one endpoint (``contact``); the other endpoint radiates away.
* For RHT a road's **right** lanes (negative ids) travel in ``+s`` and its **left** lanes (positive
  ids) travel in ``-s``. So a road's lanes flowing *toward* the node are the negative lanes when it
  meets the node at its **end** and the positive lanes when it meets at its **start** (and the
  reverse for lanes flowing *away*).
* For every ordered pair of distinct roads ``A -> B`` the heading change from A's approach direction
  to B's departure direction classifies the :class:`~roadup.common.types.TurnType`
  (straight / left / right; near-180 u-turns are dropped from the default set). Incoming driving
  lanes of A are paired inner-to-inner with outgoing driving lanes of B.

The user can add or remove movements afterwards; this only seeds a sensible default.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from roadup.common.types import LaneType, TurnType
from roadup.opendrive.eval.sampler import Sampler

if TYPE_CHECKING:
    from roadup.geometry.sampling import Frame
    from roadup.opendrive.model.network import OpenDriveModel
    from roadup.opendrive.model.road import Lane

# Turn classification thresholds, in degrees of signed heading change (CCW positive = left).
_STRAIGHT_MAX = 45.0
_TURN_MAX = 135.0


@dataclass
class Movement:
    incoming_road: str
    incoming_lane: int
    outgoing_road: str
    outgoing_lane: int
    turn: TurnType


@dataclass
class RoadEnd:
    """One road's relationship to the node: which end touches it and the travel direction there."""

    road_id: str
    contact: str          # "start" | "end" — which endpoint of the road meets the node
    position: tuple[float, float]
    approach: np.ndarray  # unit xy direction of travel *into* the node
    departure: np.ndarray  # unit xy direction of travel *out of* the node


class ConnectivitySolver:
    """Decide which incoming lanes connect to which outgoing lanes."""

    def __init__(self, model: OpenDriveModel) -> None:
        self._model = model
        self._sampler = Sampler(model)

    def movements_at(self, node_road_ids: list[str]) -> list[Movement]:
        """Default movements by geometry + lane type; the user can add/remove afterwards."""
        if len(node_road_ids) < 2:
            return []
        ends = list(self.road_ends(node_road_ids).values())
        movements: list[Movement] = []
        for a in ends:
            for b in ends:
                if a.road_id == b.road_id:
                    continue
                turn = self._classify(a.approach, b.departure)
                if turn == TurnType.U_TURN:
                    continue
                movements.extend(self._pair_lanes(a, b, turn))
        return movements

    # --- geometry ---------------------------------------------------------------------
    def road_ends(self, node_road_ids: list[str]) -> dict[str, RoadEnd]:
        """For each road, which endpoint meets the node and the travel direction there.

        Shared with :class:`~roadup.intersections.junction_builder.JunctionBuilder` so the
        connecting-road tangents match the movement geometry.
        """
        frames: dict[str, list[Frame]] = {
            rid: self._sampler.reference_frames(rid) for rid in node_road_ids
        }
        endpoints: list[np.ndarray] = []
        for fr in frames.values():
            endpoints.append(_xy(fr[0].position))
            endpoints.append(_xy(fr[-1].position))
        avg = np.mean(endpoints, axis=0)

        ends: dict[str, RoadEnd] = {}
        for rid, fr in frames.items():
            start_f, end_f = fr[0], fr[-1]
            # The endpoint nearest the cluster average is the one that meets the node.
            if np.linalg.norm(_xy(start_f.position) - avg) <= np.linalg.norm(
                _xy(end_f.position) - avg
            ):
                contact, node_f = "start", start_f
            else:
                contact, node_f = "end", end_f
            tan = _xy(node_f.tangent)
            tan = tan / (np.linalg.norm(tan) or 1.0)
            # +s tangent points away from the start and toward the end. Travel *into* the node is
            # along +s when the node is at the end, along -s when the node is at the start.
            approach = tan if contact == "end" else -tan
            ends[rid] = RoadEnd(
                road_id=rid,
                contact=contact,
                position=(float(node_f.position[0]), float(node_f.position[1])),
                approach=approach,
                departure=-approach,
            )
        return ends

    @staticmethod
    def _classify(approach: np.ndarray, departure: np.ndarray) -> TurnType:
        dot = float(np.dot(approach, departure))
        cross = float(approach[0] * departure[1] - approach[1] * departure[0])
        angle = math.degrees(math.atan2(cross, dot))  # CCW positive
        if abs(angle) <= _STRAIGHT_MAX:
            return TurnType.STRAIGHT
        if abs(angle) >= _TURN_MAX:
            return TurnType.U_TURN
        return TurnType.LEFT if angle > 0 else TurnType.RIGHT

    # --- lanes ------------------------------------------------------------------------
    def _pair_lanes(self, a: RoadEnd, b: RoadEnd, turn: TurnType) -> list[Movement]:
        incoming = self._flow_lanes(a, into_node=True)
        outgoing = self._flow_lanes(b, into_node=False)
        movements: list[Movement] = []
        for in_lane, out_lane in zip(incoming, outgoing, strict=False):  # inner-to-inner
            movements.append(
                Movement(
                    incoming_road=a.road_id,
                    incoming_lane=in_lane.id,
                    outgoing_road=b.road_id,
                    outgoing_lane=out_lane.id,
                    turn=turn,
                )
            )
        return movements

    def _flow_lanes(self, end: RoadEnd, into_node: bool) -> list[Lane]:
        """Driving lanes flowing toward (``into_node``) or away from the node, inner-to-inner.

        RHT: negative lanes travel ``+s``, positive lanes travel ``-s``. At an ``end`` contact the
        negative lanes flow into the node; at a ``start`` contact the positive lanes do.
        """
        road = self._model.get_road(end.road_id)
        section = road.lane_sections[-1] if end.contact == "end" else road.lane_sections[0]
        want_negative = (end.contact == "end") == into_node
        lanes = section.right if want_negative else section.left
        driving = [ln for ln in lanes if ln.type == LaneType.DRIVING]
        return sorted(driving, key=lambda ln: abs(ln.id))  # innermost first


def _xy(p: tuple[float, float, float]) -> np.ndarray:
    return np.asarray((p[0], p[1]), dtype=float)
