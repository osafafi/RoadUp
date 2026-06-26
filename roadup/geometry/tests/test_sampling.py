"""Unit tests for roadup.geometry.sampling."""
import pytest

from roadup.common.errors import GeometryError
from roadup.geometry.sampling import resample_by_arclength, sample_frames


def test_resample_preserves_endpoints_and_spacing() -> None:
    pts = resample_by_arclength([(0.0, 0.0, 0.0), (10.0, 0.0, 0.0)], step=2.0)
    assert pts[0] == pytest.approx((0.0, 0.0, 0.0))
    assert pts[-1] == pytest.approx((10.0, 0.0, 0.0))
    assert len(pts) == 6
    assert pts[1] == pytest.approx((2.0, 0.0, 0.0))


def test_resample_rejects_bad_input() -> None:
    with pytest.raises(GeometryError):
        resample_by_arclength([(0.0, 0.0, 0.0)], step=1.0)
    with pytest.raises(GeometryError):
        resample_by_arclength([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)], step=0.0)


def test_sample_frames_straight_line_normal_is_left() -> None:
    frames = sample_frames([(0.0, 0.0, 0.0), (10.0, 0.0, 0.0)], step=5.0)
    assert frames[0].s == pytest.approx(0.0)
    assert frames[-1].s == pytest.approx(10.0)
    for f in frames:
        assert f.tangent == pytest.approx((1.0, 0.0, 0.0))
        # +t (left of +x heading) is +y.
        assert f.normal == pytest.approx((0.0, 1.0, 0.0))


def test_sample_frames_s_is_monotonic() -> None:
    frames = sample_frames([(0.0, 0.0, 0.0), (3.0, 4.0, 0.0)], step=1.0)
    s_values = [f.s for f in frames]
    assert s_values == sorted(s_values)
    assert s_values[-1] == pytest.approx(5.0)
