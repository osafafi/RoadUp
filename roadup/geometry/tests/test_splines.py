"""Unit tests for roadup.geometry.splines."""
import math

import pytest

from roadup.geometry.splines import ControlPoint, Spline


def _line() -> Spline:
    return Spline(
        points=[
            ControlPoint(position=(0.0, 0.0, 0.0), id="cp_001"),
            ControlPoint(position=(10.0, 0.0, 0.0), id="cp_002"),
        ],
        kind="line",
    )


def test_line_evaluate_endpoints_and_midpoint() -> None:
    sp = _line()
    assert sp.evaluate(0.0) == pytest.approx((0.0, 0.0, 0.0))
    assert sp.evaluate(1.0) == pytest.approx((10.0, 0.0, 0.0))
    assert sp.evaluate(0.5) == pytest.approx((5.0, 0.0, 0.0))


def test_line_length_and_tangent() -> None:
    sp = _line()
    assert sp.length() == pytest.approx(10.0, abs=1e-6)
    assert sp.tangent(0.5) == pytest.approx((1.0, 0.0, 0.0))


def test_evaluate_clamps_parameter() -> None:
    sp = _line()
    assert sp.evaluate(-1.0) == pytest.approx((0.0, 0.0, 0.0))
    assert sp.evaluate(2.0) == pytest.approx((10.0, 0.0, 0.0))


def test_sample_spacing() -> None:
    sp = _line()
    pts = sp.sample(2.0)
    assert pts[0] == pytest.approx((0.0, 0.0, 0.0))
    assert pts[-1] == pytest.approx((10.0, 0.0, 0.0))
    # ~2 m spacing over a 10 m line -> 6 vertices.
    assert len(pts) == 6


def test_catmull_rom_passes_through_control_points() -> None:
    pts = [
        ControlPoint(position=(0.0, 0.0, 0.0)),
        ControlPoint(position=(10.0, 5.0, 0.0)),
        ControlPoint(position=(20.0, 0.0, 0.0)),
    ]
    sp = Spline(points=pts, kind="catmullRom")
    assert sp.evaluate(0.0) == pytest.approx((0.0, 0.0, 0.0))
    assert sp.evaluate(0.5) == pytest.approx((10.0, 5.0, 0.0))
    assert sp.evaluate(1.0) == pytest.approx((20.0, 0.0, 0.0))


def test_insert_move_remove_control_point() -> None:
    sp = Spline(
        points=[
            ControlPoint(position=(0.0, 0.0, 0.0), id="cp_001"),
            ControlPoint(position=(10.0, 0.0, 0.0), id="cp_002"),
        ],
        kind="line",
    )
    new_cp = sp.insert_control_point(0.5)
    assert len(sp.points) == 3
    assert new_cp.id
    assert sp.points[1].id == new_cp.id

    sp.move_control_point(new_cp.id, (5.0, 5.0, 0.0))
    assert sp.points[1].position == (5.0, 5.0, 0.0)

    sp.remove_control_point(new_cp.id)
    assert len(sp.points) == 2


def test_remove_below_minimum_raises() -> None:
    from roadup.common.errors import GeometryError

    sp = _line()
    with pytest.raises(GeometryError):
        sp.remove_control_point("cp_001")


def test_circular_arc_quarter_circle() -> None:
    # Start at origin heading +x, end at (R,R) heading +y -> quarter circle, center (0,R).
    r = 10.0
    sp = Spline.circular_arc(
        start=(0.0, 0.0, 0.0),
        start_tangent=(1.0, 0.0, 0.0),
        end=(r, r, 0.0),
        end_tangent=(0.0, 1.0, 0.0),
    )
    assert sp.kind == "arc"
    mid = sp.evaluate(0.5)
    # Midpoint of the quarter arc sits at angle 45° from center (0, R).
    expected = (r * math.sin(math.pi / 4), r - r * math.cos(math.pi / 4), 0.0)
    assert mid == pytest.approx(expected, abs=1e-6)
    assert sp.length() == pytest.approx(2 * math.pi * r / 4, abs=1e-3)
