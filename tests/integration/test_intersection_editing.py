"""Integration: build a junction, edit a connection spline, and round-trip the <junction>.

The author-side intersection counterpart to test_segment_creation: four roads meet at a node, the
ConnectivitySolver seeds movements, the JunctionBuilder authors connecting roads with default
connection splines, a control point upgrades one connection arc -> paramPoly3, the surface
re-meshes, and a write -> read cycle preserves junction topology + connecting-road editing intent.
"""
from __future__ import annotations

from pathlib import Path

from roadup.common.types import GeometryType, RoadType
from roadup.geometry.splines import ControlPoint, Spline
from roadup.intersections.connectivity import ConnectivitySolver
from roadup.intersections.junction_builder import JunctionBuilder
from roadup.intersections.surface import IntersectionSurface
from roadup.opendrive.eval.sampler import Sampler
from roadup.opendrive.io.reader import LxmlFallbackReader
from roadup.opendrive.io.writer import ScenarioGenerationWriter
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


def _four_way() -> tuple[OpenDriveModel, JunctionBuilder, Junction]:
    model = OpenDriveModel()
    model.add_road(_line_road("road_001", (8.0, 0.0, 0.0), (50.0, 0.0, 0.0)))
    model.add_road(_line_road("road_002", (0.0, 8.0, 0.0), (0.0, 50.0, 0.0)))
    model.add_road(_line_road("road_003", (-8.0, 0.0, 0.0), (-50.0, 0.0, 0.0)))
    model.add_road(_line_road("road_004", (0.0, -8.0, 0.0), (0.0, -50.0, 0.0)))
    node = ["road_001", "road_002", "road_003", "road_004"]
    movements = ConnectivitySolver(model).movements_at(node)
    builder = JunctionBuilder(model)
    junction = builder.build("junction_001", movements)
    return model, builder, junction


def _turning_connection_id(model: OpenDriveModel, junction: Junction) -> str:
    """A connection whose default geometry is an arc (a turn, not the straight-through line)."""
    for conn in junction.connections:
        if any(g.type == GeometryType.ARC for g in model.get_road(conn.connecting_road).geometry):
            return conn.id
    raise AssertionError("expected at least one turning (arc) connection")


def test_editing_a_connection_upgrades_geometry_and_resamples_surface() -> None:
    model, builder, junction = _four_way()
    assert model.validate() == []

    conn_id = _turning_connection_id(model, junction)
    road_id = next(c.connecting_road for c in junction.connections if c.id == conn_id)
    sampler = Sampler(model)
    before_centerline = [f.position for f in sampler.reference_frames(road_id)]

    # Default arc bakes a single <arc>; editing it upgrades to paramPoly3 records.
    assert [g.type for g in model.get_road(road_id).geometry] == [GeometryType.ARC]
    spline = builder.connection_spline("junction_001", conn_id)
    cp_id = spline.add_control_point(0.5)
    # Drag the new control point off the arc so the connecting road's shape genuinely changes.
    mid = spline.spline.evaluate(0.5)
    spline.move_control_point(cp_id, (mid[0] + 3.0, mid[1] + 3.0, mid[2]))
    builder.rebuild_connection("junction_001", conn_id)
    assert {g.type for g in model.get_road(road_id).geometry} == {GeometryType.PARAM_POLY3}

    # The edited reference line deviates from the original arc, and the surface re-meshes cleanly.
    after_centerline = [f.position for f in sampler.reference_frames(road_id)]
    max_shift = max(
        abs(a[0] - b[0]) + abs(a[1] - b[1])
        for a, b in zip(before_centerline, after_centerline, strict=False)
    )
    assert max_shift > 0.5
    after = IntersectionSurface(sampler).generate(junction)
    assert after.is_manifold()
    assert after.points


def test_junction_write_read_round_trip(tmp_path: Path) -> None:
    model, builder, junction = _four_way()
    conn_id = _turning_connection_id(model, junction)
    builder.connection_spline("junction_001", conn_id).add_control_point(0.5)
    builder.rebuild_connection("junction_001", conn_id)

    out = tmp_path / "junction.xodr"
    ScenarioGenerationWriter().write(model, str(out))
    restored = LxmlFallbackReader().parse(str(out))

    assert restored.validate() == []
    assert list(restored.junctions) == ["junction_001"]
    rj = restored.junctions["junction_001"]
    oj = model.junctions["junction_001"]
    assert len(rj.connections) == len(oj.connections)

    # Connection topology survives (incoming/connecting roads, contact point, lane links).
    r_by_id = {c.id: c for c in rj.connections}
    for oc in oj.connections:
        rc = r_by_id[oc.id]
        assert rc.incoming_road == oc.incoming_road
        assert rc.connecting_road == oc.connecting_road
        assert rc.contact_point == oc.contact_point
        assert [(ll.from_lane, ll.to_lane) for ll in rc.lane_links] == \
               [(ll.from_lane, ll.to_lane) for ll in oc.lane_links]

    # Connecting roads carry the junction id and the connection-spline editing intent round-trips.
    edited_road_id = next(c.connecting_road for c in oj.connections if c.id == conn_id)
    assert restored.get_road(edited_road_id).junction == "junction_001"
    assert restored.get_road(edited_road_id).user_data == model.get_road(edited_road_id).user_data
