"""Unit tests for roadup.markings.roadmark."""
import pytest

from roadup.markings.presets import get_preset
from roadup.markings.roadmark import marking_geometry_offsets, to_road_mark


def test_solid_expands_without_dashes() -> None:
    mark = to_road_mark(get_preset("white_solid"))
    assert mark.type == "solid"
    assert mark.color == "white"
    assert mark.dash_length is None and mark.gap_length is None
    assert mark.preset_id == "white_solid"


def test_broken_carries_dash_dimensions() -> None:
    mark = to_road_mark(get_preset("white_dashed"))
    assert mark.type == "broken"
    assert mark.dash_length == pytest.approx(3.0)
    assert mark.gap_length == pytest.approx(9.0)


def test_double_solid_maps_to_space_separated_type() -> None:
    mark = to_road_mark(get_preset("yellow_double"))
    assert mark.type == "solid solid"


def test_s_offset_is_carried() -> None:
    mark = to_road_mark(get_preset("white_solid"), s_offset=12.5)
    assert mark.s_offset == pytest.approx(12.5)


def test_single_offset_is_centered() -> None:
    assert marking_geometry_offsets(get_preset("white_solid")) == [0.0]


def test_double_offsets_are_symmetric() -> None:
    offsets = marking_geometry_offsets(get_preset("yellow_double"))
    assert offsets == pytest.approx([-0.075, 0.075])
