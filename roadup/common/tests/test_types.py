"""Unit tests for roadup.common.types."""
from roadup.common.types import (
    GeometryType,
    LaneSide,
    LaneType,
    RoadType,
    TurnType,
)


def test_enums_are_str_valued() -> None:
    # str-Enum members compare equal to their string value (used at YAML/USD boundaries).
    assert RoadType.HIGHWAY == "highway"
    assert LaneType.DRIVING == "driving"
    assert GeometryType.PARAM_POLY3 == "paramPoly3"
    assert TurnType.U_TURN == "uTurn"


def test_lane_side_members() -> None:
    assert {s.value for s in LaneSide} == {"left", "center", "right"}


def test_geometry_type_covers_opendrive_kinds() -> None:
    assert {g.value for g in GeometryType} == {
        "line",
        "arc",
        "spiral",
        "poly3",
        "paramPoly3",
    }
