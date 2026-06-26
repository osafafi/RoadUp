"""Unit tests for roadup.common.ids."""
import pytest

from roadup.common.errors import ValidationError
from roadup.common.ids import IdAllocator, make_id, parse_id


def test_make_id_zero_pads() -> None:
    assert make_id("road", 1) == "road_001"
    assert make_id("junction", 7) == "junction_007"
    assert make_id("road", 123) == "road_123"
    assert make_id("road", 1234) == "road_1234"  # widens past the pad


def test_make_id_negative_keeps_sign_outside_pad() -> None:
    assert make_id("lane", -2) == "lane_-002"


def test_make_id_custom_width() -> None:
    assert make_id("cp", 3, width=2) == "cp_03"


def test_make_id_rejects_bad_prefix() -> None:
    with pytest.raises(ValidationError):
        make_id("", 1)
    with pytest.raises(ValidationError):
        make_id("road_x", 1)


def test_parse_id_roundtrip() -> None:
    for prefix, n in [("road", 1), ("lane", -2), ("junction", 42)]:
        assert parse_id(make_id(prefix, n)) == (prefix, n)


def test_parse_id_rejects_malformed() -> None:
    with pytest.raises(ValidationError):
        parse_id("road")
    with pytest.raises(ValidationError):
        parse_id("road_abc")


def test_allocator_is_monotonic_per_prefix() -> None:
    alloc = IdAllocator()
    assert alloc.next("road") == "road_001"
    assert alloc.next("road") == "road_002"
    assert alloc.next("junction") == "junction_001"  # independent counter
    assert alloc.next("road") == "road_003"


def test_allocator_reserve_prevents_reuse() -> None:
    alloc = IdAllocator()
    alloc.reserve("road_005")
    assert alloc.next("road") == "road_006"
    # reserving a lower id does not move the counter backwards
    alloc.reserve("road_002")
    assert alloc.next("road") == "road_007"
