"""Unit tests for roadup.intersections.junction_builder."""
from __future__ import annotations

import pytest

from roadup.common.errors import IntersectionError
from roadup.common.types import GeometryType, RoadType
from roadup.geometry.splines import ControlPoint, Spline
from roadup.intersections.connectivity import ConnectivitySolver
from roadup.intersections.junction_builder import JunctionBuilder
from roadup.opendrive.model.junction import Junction
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


def _cross_model() -> tuple[OpenDriveModel, list[str]]:
    model = OpenDriveModel()
    model.add_road(_line_road("road_001", (8.0, 0.0, 0.0), (50.0, 0.0, 0.0)))
    model.add_road(_line_road("road_002", (0.0, 8.0, 0.0), (0.0, 50.0, 0.0)))
    model.add_road(_line_road("road_003", (-8.0, 0.0, 0.0), (-50.0, 0.0, 0.0)))
    model.add_road(_line_road("road_004", (0.0, -8.0, 0.0), (0.0, -50.0, 0.0)))
    return model, ["road_001", "road_002", "road_003", "road_004"]


def _built_junction() -> tuple[OpenDriveModel, JunctionBuilder, Junction]:
    model, node = _cross_model()
    movements = ConnectivitySolver(model).movements_at(node)
    builder = JunctionBuilder(model)
    junction = builder.build("junction_001", movements)
    return model, builder, junction


def test_build_authors_connecting_roads_and_connections() -> None:
    model, _builder, junction = _built_junction()
    assert len(junction.connections) == 12
    # One connecting road per connection, each tagged with the junction and registered on the model.
    assert junction.id in model.junctions
    for conn in junction.connections:
        road = model.get_road(conn.connecting_road)
        assert road.junction == "junction_001"
        assert road.link.predecessor == ("road", conn.incoming_road)
        assert conn.lane_links and conn.lane_links[0].to_lane == -1
    assert model.validate() == []


def test_connecting_road_geometry_matches_turn_shape() -> None:
    model, _builder, junction = _built_junction()
    # Turning connections bake an arc; straight ones a line — so both shapes appear.
    types = {
        g.type
        for c in junction.connections
        for g in model.get_road(c.connecting_road).geometry
    }
    assert GeometryType.ARC in types
    assert GeometryType.LINE in types


def test_rebuild_connection_rebakes_after_edit() -> None:
    model, builder, _junction = _built_junction()
    spline = builder.connection_spline("junction_001", "connection_000")
    road_id = next(
        c.connecting_road
        for c in model.junctions["junction_001"].connections
        if c.id == "connection_000"
    )

    spline.add_control_point(0.5)
    builder.rebuild_connection("junction_001", "connection_000")

    road = model.get_road(road_id)
    assert {g.type for g in road.geometry} == {GeometryType.PARAM_POLY3}
    assert road.user_data["isDefaultArc"] is False
    assert abs(road.length - sum(g.length for g in road.geometry)) < 1e-9


def test_build_rejects_empty_movements() -> None:
    model, _node = _cross_model()
    with pytest.raises(IntersectionError):
        JunctionBuilder(model).build("junction_001", [])


def test_connection_spline_lookup_unknown_raises() -> None:
    _model, builder, _junction = _built_junction()
    with pytest.raises(IntersectionError):
        builder.connection_spline("junction_001", "connection_999")
