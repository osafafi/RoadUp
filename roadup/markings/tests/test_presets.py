"""Unit tests for roadup.markings.presets."""
import pytest

from roadup.common.errors import ValidationError
from roadup.markings.presets import get_preset, load_marking_presets


def test_loads_seeded_presets() -> None:
    presets = load_marking_presets()
    assert {"white_solid", "white_dashed", "yellow_double"} <= set(presets)


def test_white_dashed_has_dash_dimensions() -> None:
    p = get_preset("white_dashed")
    assert p.pattern == "broken"
    assert p.dash_length == pytest.approx(3.0)
    assert p.gap_length == pytest.approx(9.0)


def test_double_has_separation_and_color() -> None:
    p = get_preset("yellow_double")
    assert p.pattern == "double_solid"
    assert p.separation == pytest.approx(0.15)
    assert p.color == "yellow"


def test_material_color_is_a_tuple() -> None:
    p = get_preset("yellow_solid")
    assert isinstance(p.material.color, tuple)
    assert p.material.color == pytest.approx((1.0, 0.85, 0.0))


def test_unknown_preset_raises() -> None:
    with pytest.raises(ValidationError):
        get_preset("does_not_exist")
