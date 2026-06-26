"""Unit tests for roadup.geometry.offset."""
import pytest

from roadup.common.errors import GeometryError
from roadup.geometry.offset import lane_boundary, offset_polyline
from roadup.geometry.sampling import sample_frames


def _straight_frames():
    return sample_frames([(0.0, 0.0, 0.0), (10.0, 0.0, 0.0)], step=5.0)


def test_offset_scalar_moves_left() -> None:
    frames = _straight_frames()
    moved = offset_polyline(frames, 3.0)
    # +t left of +x heading -> +y by 3 m.
    for p in moved:
        assert p[1] == pytest.approx(3.0)


def test_offset_negative_moves_right() -> None:
    frames = _straight_frames()
    moved = offset_polyline(frames, -2.5)
    for p in moved:
        assert p[1] == pytest.approx(-2.5)


def test_offset_per_frame_list() -> None:
    frames = _straight_frames()
    offsets = [0.0, 1.0, 2.0]
    moved = offset_polyline(frames, offsets)
    assert [round(p[1], 6) for p in moved] == offsets


def test_offset_length_mismatch_raises() -> None:
    frames = _straight_frames()
    with pytest.raises(GeometryError):
        offset_polyline(frames, [1.0, 2.0])


def test_lane_boundary_returns_inner_outer() -> None:
    frames = _straight_frames()
    inner, outer = lane_boundary(frames, [0.0, 0.0, 0.0], [3.5, 3.5, 3.5])
    assert all(p[1] == pytest.approx(0.0) for p in inner)
    assert all(p[1] == pytest.approx(3.5) for p in outer)
