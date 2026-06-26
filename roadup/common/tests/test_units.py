"""Unit tests for roadup.common.units."""
import math

import pytest

from roadup.common.units import deg_to_rad, grade_percent, kmh_to_ms


def test_kmh_to_ms() -> None:
    assert kmh_to_ms(36.0) == pytest.approx(10.0)
    assert kmh_to_ms(0.0) == 0.0
    assert kmh_to_ms(120.0) == pytest.approx(33.3333, abs=1e-3)


def test_deg_to_rad() -> None:
    assert deg_to_rad(180.0) == pytest.approx(math.pi)
    assert deg_to_rad(90.0) == pytest.approx(math.pi / 2)


def test_grade_percent() -> None:
    assert grade_percent(5.0, 100.0) == pytest.approx(5.0)
    assert grade_percent(-2.0, 100.0) == pytest.approx(-2.0)


def test_grade_percent_zero_run_raises() -> None:
    with pytest.raises(ZeroDivisionError):
        grade_percent(1.0, 0.0)
