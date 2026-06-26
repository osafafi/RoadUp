"""Unit tests for roadup.segments.lane_width."""
import pytest

from roadup.segments.lane_width import WidthLaw


def test_constant_bakes_single_record() -> None:
    records = WidthLaw.constant(3.5).bake_records()
    assert len(records) == 1
    assert records[0].a == pytest.approx(3.5)
    assert records[0].b == 0.0


def test_constant_width_at_any_s() -> None:
    law = WidthLaw.constant(3.25)
    assert law.width_at(0.0) == pytest.approx(3.25)
    assert law.width_at(100.0) == pytest.approx(3.25)


def test_taper_bakes_linear_record() -> None:
    law = WidthLaw.taper(0.0, 3.0, 25.0, 4.0)
    records = law.bake_records()
    # One sloped record at s=0 then a constant tail at s=25.
    assert records[0].s_offset == pytest.approx(0.0)
    assert records[0].a == pytest.approx(3.0)
    assert records[0].b == pytest.approx(0.04)  # (4-3)/25
    assert records[-1].s_offset == pytest.approx(25.0)
    assert records[-1].a == pytest.approx(4.0)


def test_taper_width_at_endpoints_and_mid() -> None:
    law = WidthLaw.taper(0.0, 3.0, 25.0, 4.0)
    assert law.width_at(0.0) == pytest.approx(3.0)
    assert law.width_at(12.5) == pytest.approx(3.5)
    assert law.width_at(25.0) == pytest.approx(4.0)


def test_spline_is_c1_and_hits_control_points() -> None:
    law = WidthLaw(kind="spline", control=[(0.0, 3.0), (10.0, 4.0), (20.0, 3.5)])
    assert law.width_at(0.0) == pytest.approx(3.0)
    assert law.width_at(10.0) == pytest.approx(4.0, abs=1e-6)
    assert law.width_at(20.0) == pytest.approx(3.5)


def test_empty_control_raises() -> None:
    from roadup.common.errors import ValidationError

    with pytest.raises(ValidationError):
        WidthLaw(kind="constant", control=[]).bake_records()
