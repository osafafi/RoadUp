"""Integration: mesh the showcase and assert the ribbons are structurally sound.

Complements the visual Blender check (examples/generate_obj_meshes.py): this is the *programmatic*
gate that the sampler→mesher path produces a clean mesh per road — every road a drivable surface
plus one ribbon per lane, with in-range, well-formed faces. Guards against silent mesh regressions.
"""
from pathlib import Path

from examples.generate_obj_meshes import model_meshes, road_meshes, write_obj
from examples.showcase import build_showcase_model
from roadup.opendrive.eval.sampler import Sampler


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
            continue  # junction surface = ribbons + a fan cap (mixed quads/tris), not a pure ribbon
        # ribbon between two equal-length polylines -> even vertex count, all quad faces.
        assert len(mesh.points) % 2 == 0
        assert set(mesh.face_vertex_counts) == {4}


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


def test_obj_round_trips_to_disk(tmp_path: Path) -> None:
    meshes = model_meshes(build_showcase_model())
    out = tmp_path / "showcase.obj"
    faces = write_obj(out, meshes)
    text = out.read_text(encoding="utf-8")
    # One object per ribbon; face indices are global + 1-based and never exceed the vertex count.
    assert text.count("\no ") + text.startswith("o ") == len(meshes)
    vertex_count = sum(1 for line in text.splitlines() if line.startswith("v "))
    face_lines = [line for line in text.splitlines() if line.startswith("f ")]
    assert len(face_lines) == faces
    assert all(1 <= int(tok) <= vertex_count for line in face_lines for tok in line.split()[1:])
