"""Unit tests for roadup.intersections.surface."""
from __future__ import annotations

from roadup.common.types import RoadType
from roadup.geometry.splines import ControlPoint, Spline
from roadup.intersections.connectivity import ConnectivitySolver
from roadup.intersections.junction_builder import JunctionBuilder
from roadup.intersections.surface import IntersectionSurface
from roadup.opendrive.eval.sampler import Sampler
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


def _built_junction() -> tuple[OpenDriveModel, Junction]:
    model = OpenDriveModel()
    model.add_road(_line_road("road_001", (8.0, 0.0, 0.0), (50.0, 0.0, 0.0)))
    model.add_road(_line_road("road_002", (0.0, 8.0, 0.0), (0.0, 50.0, 0.0)))
    model.add_road(_line_road("road_003", (-8.0, 0.0, 0.0), (-50.0, 0.0, 0.0)))
    model.add_road(_line_road("road_004", (0.0, -8.0, 0.0), (0.0, -50.0, 0.0)))
    node = ["road_001", "road_002", "road_003", "road_004"]
    movements = ConnectivitySolver(model).movements_at(node)
    junction = JunctionBuilder(model).build("junction_001", movements)
    return model, junction


def test_generate_produces_non_empty_manifold_surface() -> None:
    model, junction = _built_junction()
    mesh = IntersectionSurface(Sampler(model)).generate(junction)
    assert mesh.points
    assert mesh.face_vertex_counts
    # Every face indexes valid vertices.
    assert max(mesh.face_vertex_indices) < len(mesh.points)
    assert mesh.is_manifold()


def test_empty_junction_yields_empty_mesh() -> None:
    model, _junction = _built_junction()
    mesh = IntersectionSurface(Sampler(model)).generate(Junction(id="junction_009"))
    assert mesh.points == []
    assert mesh.face_vertex_counts == []
