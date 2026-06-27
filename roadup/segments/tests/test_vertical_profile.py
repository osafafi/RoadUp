"""Unit tests for roadup.segments.vertical_profile (elevation + superelevation laws)."""
import math

import pytest

from roadup.common.errors import ValidationError
from roadup.opendrive.eval.elevation import eval_elevation, eval_superelevation
from roadup.segments.vertical_profile import ElevationLaw, SuperelevationLaw


def test_constant_elevation_bakes_one_record() -> None:
    recs = ElevationLaw.constant(2.5).bake_records()
    assert len(recs) == 1
    assert recs[0].s == 0.0 and recs[0].a == 2.5 and recs[0].b == 0.0


def test_grade_is_linear_and_round_trips_through_eval() -> None:
    law = ElevationLaw.grade(length=100.0, slope=0.03)      # 3% grade
    recs = law.bake_records()
    assert math.isclose(eval_elevation(recs, 0.0), 0.0, abs_tol=1e-9)
    assert math.isclose(eval_elevation(recs, 50.0), 0.03 * 50.0, abs_tol=1e-9)
    assert math.isclose(law.elevation_at(100.0), 0.03 * 100.0, abs_tol=1e-9)


def test_spline_crest_is_smooth_and_hits_control_points() -> None:
    law = ElevationLaw.crest(0.0, 0.0, 50.0, 4.0, 100.0, 0.0)
    recs = law.bake_records()
    # Catmull-Rom interpolation passes through the control points.
    assert math.isclose(eval_elevation(recs, 0.0), 0.0, abs_tol=1e-9)
    assert math.isclose(eval_elevation(recs, 50.0), 4.0, abs_tol=1e-6)
    assert math.isclose(eval_elevation(recs, 100.0), 0.0, abs_tol=1e-6)


def test_superelevation_ramp_round_trips() -> None:
    law = SuperelevationLaw.ramp(0.0, 0.0, 30.0, math.radians(6.0))
    recs = law.bake_records()
    assert math.isclose(eval_superelevation(recs, 0.0), 0.0, abs_tol=1e-9)
    assert math.isclose(eval_superelevation(recs, 30.0), math.radians(6.0), abs_tol=1e-9)
    assert math.isclose(law.angle_at(15.0), math.radians(3.0), abs_tol=1e-9)


def test_empty_law_raises() -> None:
    with pytest.raises(ValidationError):
        ElevationLaw().bake_records()
