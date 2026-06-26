"""Unit tests for roadup.common.errors."""
from roadup.common.errors import (
    GeometryError,
    IntersectionError,
    OpenDriveIOError,
    RoadError,
    TopologyError,
    USDError,
    ValidationError,
)


def test_all_errors_subclass_road_error() -> None:
    for exc in (
        ValidationError,
        GeometryError,
        TopologyError,
        OpenDriveIOError,
        IntersectionError,
        USDError,
    ):
        assert issubclass(exc, RoadError)


def test_road_error_is_exception() -> None:
    assert issubclass(RoadError, Exception)
