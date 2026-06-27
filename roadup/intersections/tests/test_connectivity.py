"""Unit tests for roadup.intersections.connectivity."""
from __future__ import annotations

from collections import Counter

from roadup.common.types import RoadType, TurnType
from roadup.geometry.splines import ControlPoint, Spline
from roadup.intersections.connectivity import ConnectivitySolver
from roadup.opendrive.model.network import OpenDriveModel
from roadup.opendrive.model.road import Road
from roadup.segments.builder import SegmentBuilder


def _line_road(rid: str, p0: tuple, p1: tuple) -> Road:
    spline = Spline(
        points=[ControlPoint(position=p0, id="cp_001"), ControlPoint(position=p1, id="cp_002")],
        kind="line",
    )
    return (
        SegmentBuilder(RoadType.ARTERIAL)
        .with_lane_count(1, 1)
        .with_reference_line(spline)
        .build(rid)
    )


def _cross_model() -> OpenDriveModel:
    """Four roads radiating from the origin (each meets the node at its start)."""
    model = OpenDriveModel()
    model.add_road(_line_road("road_001", (8.0, 0.0, 0.0), (50.0, 0.0, 0.0)))    # east
    model.add_road(_line_road("road_002", (0.0, 8.0, 0.0), (0.0, 50.0, 0.0)))    # north
    model.add_road(_line_road("road_003", (-8.0, 0.0, 0.0), (-50.0, 0.0, 0.0)))  # west
    model.add_road(_line_road("road_004", (0.0, -8.0, 0.0), (0.0, -50.0, 0.0)))  # south
    return model


def test_four_way_movements_cover_all_turn_types() -> None:
    model = _cross_model()
    movements = ConnectivitySolver(model).movements_at(
        ["road_001", "road_002", "road_003", "road_004"]
    )
    # 4 roads * 3 other roads, one driving lane each (u-turns dropped) = 12 movements.
    assert len(movements) == 12
    counts = Counter(mv.turn for mv in movements)
    assert counts == {TurnType.STRAIGHT: 4, TurnType.LEFT: 4, TurnType.RIGHT: 4}
    # No u-turns and no self-connections.
    assert all(mv.incoming_road != mv.outgoing_road for mv in movements)
    assert TurnType.U_TURN not in counts


def test_turn_geometry_is_right_handed() -> None:
    """Travelling west (from the east road): north is a right turn, south a left turn (RHT)."""
    model = _cross_model()
    movements = ConnectivitySolver(model).movements_at(
        ["road_001", "road_002", "road_003", "road_004"]
    )
    by_target = {mv.outgoing_road: mv for mv in movements if mv.incoming_road == "road_001"}
    assert by_target["road_003"].turn == TurnType.STRAIGHT  # east -> west
    assert by_target["road_002"].turn == TurnType.RIGHT     # east -> north
    assert by_target["road_004"].turn == TurnType.LEFT      # east -> south
    # Incoming lanes flow toward the node (left/positive at a start contact); outgoing flow away.
    assert by_target["road_003"].incoming_lane == 1
    assert by_target["road_003"].outgoing_lane == -1


def test_t_junction_three_roads() -> None:
    model = _cross_model()
    model.remove_road("road_004")  # drop the south arm -> a T
    movements = ConnectivitySolver(model).movements_at(["road_001", "road_002", "road_003"])
    # 3 roads * 2 others = 6 movements, still no u-turns.
    assert len(movements) == 6
    assert all(mv.turn != TurnType.U_TURN for mv in movements)


def test_single_road_has_no_movements() -> None:
    model = _cross_model()
    assert ConnectivitySolver(model).movements_at(["road_001"]) == []
