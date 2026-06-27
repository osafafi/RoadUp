"""Unit tests for roadup.opendrive.eval.planview (pure-Python plan-view evaluation)."""
import math
from collections.abc import Callable

import numpy as np

from roadup.common.types import GeometryType
from roadup.geometry.sampling import Frame
from roadup.opendrive.eval.planview import (
    eval_record,
    sample_planview,
    sample_planview_adaptive,
)
from roadup.opendrive.model.road import Geometry


def _adaptive(
    geometry: list[Geometry], vertical_angle: Callable[[float], float] | None = None
) -> list[Frame]:
    """sample_planview_adaptive with the default showcase thresholds."""
    return sample_planview_adaptive(
        geometry, max_angle=math.radians(5.0), max_chord_error=0.02,
        min_step=0.5, max_step=1.0e6, vertical_angle=vertical_angle,
    )


def test_line_is_exact() -> None:
    geom = Geometry(s=0.0, x=1.0, y=2.0, hdg=math.pi / 2, length=10.0, type=GeometryType.LINE)
    x, y, hdg = eval_record(geom, 4.0)
    assert math.isclose(x, 1.0, abs_tol=1e-9)
    assert math.isclose(y, 6.0, abs_tol=1e-9)
    assert math.isclose(hdg, math.pi / 2, abs_tol=1e-9)


def test_arc_closed_form() -> None:
    k = 1.0 / 80.0
    geom = Geometry(s=0.0, x=0.0, y=30.0, hdg=0.0, length=62.0,
                    type=GeometryType.ARC, params={"curvature": k})
    x, y, hdg = eval_record(geom, geom.length)
    assert math.isclose(hdg, k * geom.length, abs_tol=1e-12)               # 0.775 rad
    assert math.isclose(x, math.sin(hdg) / k, abs_tol=1e-9)
    assert math.isclose(y, 30.0 - (math.cos(hdg) - 1.0) / k, abs_tol=1e-9)


def test_arc_zero_curvature_degrades_to_line() -> None:
    geom = Geometry(s=0.0, x=0.0, y=0.0, hdg=0.0, length=5.0,
                    type=GeometryType.ARC, params={"curvature": 0.0})
    x, y, _ = eval_record(geom, 5.0)
    assert math.isclose(x, 5.0, abs_tol=1e-9) and math.isclose(y, 0.0, abs_tol=1e-9)


def test_parampoly3_endpoints_and_heading() -> None:
    # S-curve: u(p)=60p, v(p)=h(3p^2-2p^3); p normalized in [0,1].
    h, length = 8.0, 60.0
    geom = Geometry(
        s=0.0, x=0.0, y=120.0, hdg=0.0, length=length, type=GeometryType.PARAM_POLY3,
        params={"aU": 0.0, "bU": length, "cU": 0.0, "dU": 0.0,
                "aV": 0.0, "bV": 0.0, "cV": 3.0 * h, "dV": -2.0 * h},
    )
    x0, y0, hdg0 = eval_record(geom, 0.0)
    assert (x0, y0) == (0.0, 120.0)
    assert math.isclose(hdg0, 0.0, abs_tol=1e-6)        # v'(0)=0 -> tangent along +u
    # The parametric end (p=1) sits at the curve's true arc length, which exceeds the authored
    # `length` for an S-curve; sample_planview spans true arc length, so its last frame is the end.
    end = sample_planview([geom], step=1.0)[-1]
    assert math.isclose(end.position[0], 60.0, abs_tol=1e-2)        # u(1)=60
    assert math.isclose(end.position[1], 120.0 + h, abs_tol=1e-2)   # v(1)=h
    assert math.isclose(math.atan2(end.tangent[1], end.tangent[0]), 0.0, abs_tol=1e-6)


def test_spiral_heading_is_quadratic_and_position_matches_fine_integration() -> None:
    c0, c1, length = 0.0, 1.0 / 40.0, 50.0
    geom = Geometry(s=0.0, x=0.0, y=80.0, hdg=0.0, length=length,
                    type=GeometryType.SPIRAL, params={"curvStart": c0, "curvEnd": c1})
    # heading(L) = c0*L + 0.5*(c1-c0)/L * L^2 = 0.5*(c0+c1)*L
    _, _, hdg = eval_record(geom, length)
    assert math.isclose(hdg, 0.5 * (c0 + c1) * length, abs_tol=1e-9)       # 0.625 rad

    # Independent dense reference integration of the clothoid.
    n = 20001
    s = np.linspace(0.0, length, n)
    dk = (c1 - c0) / length
    head = c0 * s + 0.5 * dk * s * s
    x_ref = float(np.trapezoid(np.cos(head), s))
    y_ref = 80.0 + float(np.trapezoid(np.sin(head), s))
    x, y, _ = eval_record(geom, length)
    assert math.isclose(x, x_ref, abs_tol=1e-2)
    assert math.isclose(y, y_ref, abs_tol=1e-2)


def test_adaptive_straight_is_two_endpoints() -> None:
    geom = Geometry(s=0.0, x=0.0, y=0.0, hdg=0.0, length=120.0, type=GeometryType.LINE)
    frames = _adaptive([geom])
    assert len(frames) == 2                                   # 1 quad -> 2 triangles
    assert math.isclose(frames[0].s, 0.0) and math.isclose(frames[-1].s, 120.0)


def test_adaptive_arc_density_tracks_angle_threshold() -> None:
    # Heading sweeps k*length rad; a 5-degree budget needs ~sweep/5deg interior segments. Chord
    # error refines further on a fairly tight radius, so assert a sensible lower bound + accuracy.
    k = 1.0 / 50.0
    length = 50.0                                            # sweep = 1.0 rad ~= 57.3 deg
    geom = Geometry(s=0.0, x=0.0, y=0.0, hdg=0.0, length=length,
                    type=GeometryType.ARC, params={"curvature": k})
    frames = _adaptive([geom])
    sweep_deg = math.degrees(k * length)
    assert len(frames) >= math.ceil(sweep_deg / 5.0)         # at least the angle budget
    # Every interior frame lies on the true circle of radius 1/k centred at (0, 1/k).
    r = 1.0 / k
    for f in frames:
        assert math.isclose(math.hypot(f.position[0], f.position[1] - r), r, abs_tol=0.05)


def test_adaptive_denser_than_straight_on_curves() -> None:
    arc = Geometry(s=0.0, x=0.0, y=0.0, hdg=0.0, length=50.0,
                   type=GeometryType.ARC, params={"curvature": 1.0 / 50.0})
    line = Geometry(s=0.0, x=0.0, y=0.0, hdg=0.0, length=50.0, type=GeometryType.LINE)
    assert len(_adaptive([arc])) > len(_adaptive([line]))


def test_adaptive_vertical_angle_refines_a_flat_straight() -> None:
    # A straight plan-view that nonetheless pitches/banks must not collapse to 2 samples.
    geom = Geometry(s=0.0, x=0.0, y=0.0, hdg=0.0, length=100.0, type=GeometryType.LINE)
    flat = _adaptive([geom])
    # A vertical angle that ramps 0 -> ~0.5 rad over the road forces several stations.
    ramped = _adaptive([geom], vertical_angle=lambda s: 0.5 * (s / 100.0))
    assert len(flat) == 2
    assert len(ramped) > 2


def test_sample_planview_chains_records_without_duplicate_joints() -> None:
    g1 = Geometry(s=0.0, x=0.0, y=0.0, hdg=0.0, length=10.0, type=GeometryType.LINE)
    g2 = Geometry(s=10.0, x=10.0, y=0.0, hdg=0.0, length=10.0, type=GeometryType.LINE)
    frames = sample_planview([g1, g2], step=2.0)
    s_values = [f.s for f in frames]
    assert s_values == sorted(s_values)                # monotonic, ascending
    assert len(s_values) == len(set(round(v, 6) for v in s_values))  # no duplicated joint
    assert math.isclose(frames[0].s, 0.0) and math.isclose(frames[-1].s, 20.0)
    # tangent unit + normal is left of tangent (+t)
    f = frames[0]
    assert math.isclose(math.hypot(*f.tangent[:2]), 1.0, abs_tol=1e-9)
    assert math.isclose(f.normal[0], -f.tangent[1], abs_tol=1e-9)
    assert math.isclose(f.normal[1], f.tangent[0], abs_tol=1e-9)
