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
    meshes = model_meshes(build_showcase_model())
    assert meshes
    for _name, mesh in meshes:
        assert mesh.points, "ribbon has no vertices"
        # ribbon between two equal-length polylines -> even vertex count, all quad faces.
        assert len(mesh.points) % 2 == 0
        assert set(mesh.face_vertex_counts) == {4}
        assert max(mesh.face_vertex_indices) < len(mesh.points)
        assert mesh.is_manifold()


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
