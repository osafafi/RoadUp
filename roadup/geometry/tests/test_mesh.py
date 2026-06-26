"""Unit tests for roadup.geometry.mesh."""
import pytest

from roadup.common.errors import GeometryError
from roadup.geometry.mesh import MeshBuilder, MeshData


def test_ribbon_quad_strip() -> None:
    left = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]
    right = [(0.0, 3.0, 0.0), (1.0, 3.0, 0.0)]
    mesh = MeshBuilder().ribbon(left, right)
    assert len(mesh.points) == 4
    assert mesh.face_vertex_counts == [4]
    assert len(mesh.face_vertex_indices) == 4
    assert mesh.is_manifold()


def test_ribbon_length_mismatch_raises() -> None:
    with pytest.raises(GeometryError):
        MeshBuilder().ribbon([(0.0, 0.0, 0.0)], [(0.0, 1.0, 0.0), (1.0, 1.0, 0.0)])


def test_polygon_surface_fan() -> None:
    boundary = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, 2.0, 0.0), (0.0, 2.0, 0.0)]
    mesh = MeshBuilder().polygon_surface(boundary)
    # centroid + 4 boundary verts; 4 triangles.
    assert len(mesh.points) == 5
    assert mesh.face_vertex_counts == [3, 3, 3, 3]
    assert mesh.is_manifold()


def test_extrude_builds_quads() -> None:
    path = [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0)]
    cross = [(0.0, 0.0), (0.0, 0.5)]  # 0.5 m tall vertical wall
    mesh = MeshBuilder().extrude(path, cross)
    assert len(mesh.points) == 4
    assert mesh.face_vertex_counts == [4]


def test_merge_reindexes_faces() -> None:
    a = MeshBuilder().ribbon([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)],
                             [(0.0, 1.0, 0.0), (1.0, 1.0, 0.0)])
    b = MeshBuilder().ribbon([(0.0, 0.0, 1.0), (1.0, 0.0, 1.0)],
                             [(0.0, 1.0, 1.0), (1.0, 1.0, 1.0)])
    merged = a.merge(b)
    assert len(merged.points) == 8
    assert merged.face_vertex_counts == [4, 4]
    # Second face's indices were shifted by len(a.points) == 4.
    assert max(merged.face_vertex_indices) == 7
    assert min(merged.face_vertex_indices[4:]) >= 4


def test_non_manifold_detected() -> None:
    # Three triangles sharing one edge (0,1) -> non-manifold.
    mesh = MeshData(
        points=[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
                (0.0, -1.0, 0.0), (1.0, 1.0, 0.0)],
        face_vertex_counts=[3, 3, 3],
        face_vertex_indices=[0, 1, 2, 0, 1, 3, 0, 1, 4],
    )
    assert not mesh.is_manifold()
