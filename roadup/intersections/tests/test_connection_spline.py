"""Unit tests for roadup.intersections.connection_spline."""
from __future__ import annotations

import numpy as np

from roadup.common.types import GeometryType
from roadup.intersections.connection_spline import ConnectionSpline


def test_default_arc_bakes_single_arc_record() -> None:
    cs = ConnectionSpline.default_arc(
        start=(0.0, 0.0, 0.0), start_tangent=(1.0, 0.0, 0.0),
        end=(10.0, 10.0, 0.0), end_tangent=(0.0, 1.0, 0.0),
    )
    assert cs.is_default_arc
    records = cs.to_geometry_records()
    assert [g.type for g in records] == [GeometryType.ARC]


def test_collinear_default_degrades_to_line() -> None:
    cs = ConnectionSpline.default_arc(
        start=(8.0, 0.0, 0.0), start_tangent=(-1.0, 0.0, 0.0),
        end=(-8.0, 0.0, 0.0), end_tangent=(-1.0, 0.0, 0.0),
    )
    assert cs.is_default_arc
    assert [g.type for g in cs.to_geometry_records()] == [GeometryType.LINE]


def test_minimal_arc_not_the_reflex_one() -> None:
    """A 90° turn must bake a ~90° arc, never the 270° way round (the old sign-of-radius bug)."""
    cs = ConnectionSpline.default_arc(
        start=(8.0, 0.0, 0.0), start_tangent=(-1.0, 0.0, 0.0),   # heading west into the node
        end=(0.0, 8.0, 0.0), end_tangent=(0.0, 1.0, 0.0),        # leaving north
    )
    [record] = cs.to_geometry_records()
    assert record.type == GeometryType.ARC
    sweep_deg = np.degrees(abs(record.params["curvature"]) * record.length)
    assert sweep_deg < 180.0


def test_skewed_pose_falls_back_to_tangent_matched_bezier() -> None:
    """When no single arc honours both tangents, the default is a tangent-matched Bézier."""
    start, st = (0.0, 0.0, 0.0), (1.0, 0.0, 0.0)
    end, et = (20.0, 6.0, 0.0), (1.0, 2.0, 0.0)  # asymmetric -> arc can't honour both ends
    cs = ConnectionSpline.default_arc(start, st, end, et)
    assert {g.type for g in cs.to_geometry_records()} == {GeometryType.PARAM_POLY3}
    # End tangents of the baked curve match the requested poses.
    start_tan = np.array(cs.spline.tangent(0.0)[:2])
    end_tan = np.array(cs.spline.tangent(1.0)[:2])
    assert np.allclose(start_tan / np.linalg.norm(start_tan), (1.0, 0.0), atol=1e-3)
    want_end = np.array(et[:2]) / np.linalg.norm(et[:2])
    assert np.allclose(end_tan / np.linalg.norm(end_tan), want_end, atol=1e-3)


def test_add_control_point_upgrades_to_param_poly3() -> None:
    cs = ConnectionSpline.default_arc(
        start=(0.0, 0.0, 0.0), start_tangent=(1.0, 0.0, 0.0),
        end=(10.0, 10.0, 0.0), end_tangent=(0.0, 1.0, 0.0),
    )
    start_pos = cs.spline.evaluate(0.0)
    end_pos = cs.spline.evaluate(1.0)

    cp_id = cs.add_control_point(0.5)

    assert cp_id
    assert not cs.is_default_arc
    records = cs.to_geometry_records()
    assert {g.type for g in records} == {GeometryType.PARAM_POLY3}
    # Endpoints are preserved through the upgrade.
    assert np.allclose(cs.spline.evaluate(0.0)[:2], start_pos[:2], atol=1e-6)
    assert np.allclose(cs.spline.evaluate(1.0)[:2], end_pos[:2], atol=1e-6)


def test_userdata_round_trip_payload() -> None:
    cs = ConnectionSpline.default_arc(
        start=(0.0, 0.0, 0.0), start_tangent=(1.0, 0.0, 0.0),
        end=(10.0, 10.0, 0.0), end_tangent=(0.0, 1.0, 0.0),
    )
    assert cs.userdata()["kind"] == "connectionSpline"
    assert cs.userdata()["isDefaultArc"] is True
    cs.add_control_point(0.5)
    payload = cs.userdata()
    assert payload["isDefaultArc"] is False
    assert len(payload["controlPoints"]) == len(cs.spline.points)
