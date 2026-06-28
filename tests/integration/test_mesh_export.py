"""Integration: mesh the showcase and assert the ribbons are structurally sound.

The *programmatic* gate that the sampler→mesher path produces a clean mesh per road — every road a
drivable surface plus one ribbon per lane, with in-range, well-formed faces, plus a watertight
junction surface. Guards against silent mesh regressions. (The real 3D output layer is
``roadup/usd``; ``examples/generate_usd.py`` writes the inspectable USD stage.)
"""
from __future__ import annotations

from examples.showcase import build_showcase_model
from roadup.geometry.mesh import MeshBuilder, MeshData
from roadup.intersections.surface import IntersectionSurface
from roadup.opendrive.eval.sampler import Sampler
from roadup.opendrive.model.network import OpenDriveModel


def road_meshes(sampler: Sampler, road_id: str) -> list[tuple[str, MeshData]]:
    """Build the (name, mesh) ribbons for one road: a surface ribbon + one ribbon per lane."""
    builder = MeshBuilder()
    frames = sampler.reference_frames(road_id)
    meshes: list[tuple[str, MeshData]] = []
    if len(frames) < 2:
        return meshes
    left, right = sampler.road_surface_polylines(road_id)
    if len(left) >= 2 and len(right) >= 2:
        meshes.append((f"{road_id}_Surface", builder.ribbon(left, right)))
    for lb in sampler.lane_boundaries(road_id, frames[0].s, frames[-1].s):
        if len(lb.inner) >= 2 and len(lb.outer) >= 2:
            meshes.append((f"{road_id}_Lane_{lb.lane_id}", builder.ribbon(lb.inner, lb.outer)))
    return meshes


def model_meshes(model: OpenDriveModel, step: float = 1.0) -> list[tuple[str, MeshData]]:
    """All (name, mesh) meshes: each non-junction road's ribbons + one surface per junction."""
    sampler = Sampler(model, step=step)
    meshes: list[tuple[str, MeshData]] = []
    for road_id, road in model.roads.items():
        if road.junction is not None:  # connecting roads are subsumed by the junction surface
            continue
        meshes.extend(road_meshes(sampler, road_id))
    for junction_id, junction in model.junctions.items():
        surface = IntersectionSurface(sampler).generate(junction)
        if surface.points:
            meshes.append((f"{junction_id}_Surface", surface))
    return meshes


def test_every_road_yields_a_surface_and_one_ribbon_per_lane() -> None:
    model = build_showcase_model()
    sampler = Sampler(model, step=1.0)
    for road_id, road in model.roads.items():
        names = [name for name, _ in road_meshes(sampler, road_id)]
        assert f"{road_id}_Surface" in names
        section = road.lane_sections[0]
        for lane in section.left + section.right:  # center (0) has no width -> no ribbon
            assert f"{road_id}_Lane_{lane.id}" in names


def test_ribbon_faces_are_in_range_quads() -> None:
    model = build_showcase_model()
    meshes = model_meshes(model)
    assert meshes
    junction_surfaces = {f"{jid}_Surface" for jid in model.junctions}
    for name, mesh in meshes:
        assert mesh.points, "mesh has no vertices"
        assert max(mesh.face_vertex_indices) < len(mesh.points)
        assert mesh.is_manifold()
        if name in junction_surfaces:
            continue  # junction surface = a fan cap over the boundary loop (tris), not a ribbon
        # ribbon between two equal-length polylines -> even vertex count, all quad faces.
        assert len(mesh.points) % 2 == 0
        assert set(mesh.face_vertex_counts) == {4}


def test_junction_surface_is_a_clean_delaunay_cap() -> None:
    model = build_showcase_model()
    meshes = dict(model_meshes(model))
    for jid in model.junctions:
        surface = meshes[f"{jid}_Surface"]
        # Delaunay cap over the boundary loop: all triangles, every vertex distinct, +Z winding.
        assert set(surface.face_vertex_counts) == {3}
        assert len({tuple(round(c, 6) for c in p) for p in surface.points}) == len(surface.points)
        cur = 0
        for c in surface.face_vertex_counts:
            i, j, k = surface.face_vertex_indices[cur:cur + c]
            cur += c
            a, b, d = surface.points[i], surface.points[j], surface.points[k]
            area = (b[0] - a[0]) * (d[1] - a[1]) - (b[1] - a[1]) * (d[0] - a[0])
            assert area > 0.0, "every cap triangle must wind +Z (no back-facing normals)"


def test_adaptive_straight_is_minimal_and_curve_is_denser() -> None:
    model = build_showcase_model()
    sampler = Sampler(model)                                   # adaptive (default)
    # road_001 is a straight highway -> each lane ribbon is a single quad (2 triangles).
    straight = dict(road_meshes(sampler, "road_001"))
    straight_quads = len(straight["road_001_Lane_-1"].face_vertex_counts)
    # road_002 is an arc connector -> its ribbons must have more quads than the straight.
    curve = dict(road_meshes(sampler, "road_002"))
    curve_quads = len(curve["road_002_Lane_-1"].face_vertex_counts)
    assert straight_quads == 1
    assert curve_quads > straight_quads


def test_elevated_road_mesh_climbs_and_banks() -> None:
    model = build_showcase_model()
    sampler = Sampler(model)
    meshes = dict(road_meshes(sampler, "road_006"))           # the climbing, banked curve
    surface = meshes["road_006_Surface"]
    zs = [z for _, _, z in surface.points]
    assert max(zs) - min(zs) > 1.0, "elevation grade should lift the surface well above flat"
    # Banking tilts the cross-section: at a station the left and right edges sit at different z.
    lane = meshes["road_006_Lane_1"]
    n = len(lane.points) // 2
    inner_z = lane.points[n - 1][2]      # last inner-edge vertex
    outer_z = lane.points[2 * n - 1][2]  # matching outer-edge vertex
    assert abs(inner_z - outer_z) > 1e-3, "superelevation should offset the edges vertically"
