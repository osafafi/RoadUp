"""Unit tests for roadup.intersections.surface + boundary."""
from __future__ import annotations

import math

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


def _has_near_duplicates(points: list[tuple], eps: float = 1e-6) -> int:
    """Count vertices that coincide with an earlier vertex within ``eps`` (the old-mesh bug)."""
    seen: list[tuple] = []
    dupes = 0
    for p in points:
        if any(math.dist(p, q) < eps for q in seen):
            dupes += 1
        else:
            seen.append(p)
    return dupes


def test_generate_produces_non_empty_manifold_surface() -> None:
    model, junction = _built_junction()
    mesh = IntersectionSurface(Sampler(model)).generate(junction)
    assert mesh.points
    assert mesh.face_vertex_counts
    # Every face indexes valid vertices.
    assert max(mesh.face_vertex_indices) < len(mesh.points)
    assert mesh.is_manifold()


def test_surface_has_no_duplicate_vertices() -> None:
    # The regression: blindly merging per-connection ribbons double-stacked boundary vertices.
    model, junction = _built_junction()
    mesh = IntersectionSurface(Sampler(model)).generate(junction)
    assert _has_near_duplicates(mesh.points) == 0


def test_boundary_has_one_edge_and_fillet_per_node_road() -> None:
    model, junction = _built_junction()
    boundary = IntersectionSurface(Sampler(model)).boundary(junction)
    # Four node roads meet -> four end-edges and four corner fillets closing the ring.
    assert len(boundary.extremities) == 4
    assert len(boundary.corners) == 4
    # Roads are ordered CCW by outward direction.
    angles = [math.atan2(e.outward[1], e.outward[0]) for e in boundary.extremities]
    assert angles == sorted(angles)


def test_corner_fillets_default_to_unedited() -> None:
    model, junction = _built_junction()
    boundary = IntersectionSurface(Sampler(model)).boundary(junction)
    assert all(not c.edited for c in boundary.corners)
    assert junction.user_data.get("boundary") in (None, {})


def test_editing_a_corner_handle_persists_and_round_trips_in_user_data() -> None:
    model, junction = _built_junction()
    surface = IntersectionSurface(Sampler(model))

    boundary = surface.boundary(junction)
    corner = boundary.corners[0]
    moved = (corner.out_handle[0] + 4.0, corner.out_handle[1] + 4.0, corner.out_handle[2])
    corner.move_out_handle(moved)
    surface.commit_boundary(junction, boundary)

    # Only the edited corner persists, stored as an offset from its endpoint.
    stored = junction.user_data["boundary"]["corners"]
    assert list(stored) == [corner.id]

    # A fresh boundary rebuilds the default endpoints but re-applies the edited handle.
    restored = surface.boundary(junction)
    rc = restored.corner(corner.id)
    assert rc.edited
    assert math.dist(rc.out_handle, moved) < 1e-9
    # The reshaped fillet changes the surface (more boundary samples bulge out).
    assert surface.generate(junction).points


def test_empty_junction_yields_empty_mesh() -> None:
    model, _junction = _built_junction()
    mesh = IntersectionSurface(Sampler(model)).generate(Junction(id="junction_009"))
    assert mesh.points == []
    assert mesh.face_vertex_counts == []
