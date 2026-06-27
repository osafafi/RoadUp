"""Unit tests for roadup.usd.mapping — pure-Python path helpers + tag reading (no pxr)."""
from __future__ import annotations

from roadup.usd import mapping


def test_road_and_junction_paths_are_pascal_id() -> None:
    assert mapping.road_prim_path("road_001") == "/RoadNetwork/Roads/Road_001"
    assert mapping.junction_prim_path("junction_007") == "/RoadNetwork/Junctions/Junction_007"
    assert mapping.road_surface_path("road_002") == "/RoadNetwork/Roads/Road_002/Surface"


def test_lane_token_encodes_sign() -> None:
    assert mapping.lane_token(1) == "LaneP1"
    assert mapping.lane_token(-2) == "LaneN2"
    assert mapping.lane_token(0) == "LaneP0"
    # No characters USD prohibits in a prim name.
    for lid in (-3, -1, 0, 1, 4):
        assert "-" not in mapping.lane_token(lid)


def test_marking_and_rail_paths() -> None:
    road = "/RoadNetwork/Roads/Road_001"
    assert mapping.lane_marking_prim_path("road_001", 2) == f"{road}/Markings/LaneP2"
    assert mapping.lane_marking_prim_path("road_001", 2, index=1) == f"{road}/Markings/LaneP2_1"
    assert mapping.centerline_rail_path("road_001") == f"{road}/Rails/Centerline"
    assert mapping.lane_rail_path("road_001", -1) == f"{road}/Rails/LaneN1_Edge"


# --- resolve_prim against a duck-typed prim -------------------------------------------
class _Attr:
    def __init__(self, value: object) -> None:
        self._value = value

    def IsValid(self) -> bool:
        return self._value is not None

    def Get(self) -> object:
        return self._value


class _Prim:
    def __init__(self, **attrs: object) -> None:
        self._attrs = attrs

    def GetAttribute(self, name: str) -> _Attr:
        return _Attr(self._attrs.get(name))


def test_resolve_junction() -> None:
    prim = _Prim(**{mapping.ATTR_JUNCTION_ID: "junction_001"})
    assert mapping.resolve_prim(prim) == {"kind": "junction", "id": "junction_001"}


def test_resolve_road() -> None:
    prim = _Prim(**{mapping.ATTR_ROAD_ID: "road_001"})
    assert mapping.resolve_prim(prim) == {"kind": "road", "id": "road_001"}


def test_resolve_lane_includes_lane_id() -> None:
    prim = _Prim(**{mapping.ATTR_ROAD_ID: "road_001", mapping.ATTR_LANE_ID: -2})
    assert mapping.resolve_prim(prim) == {"kind": "lane", "id": "road_001", "lane_id": -2}


def test_resolve_handle_carries_control_point() -> None:
    prim = _Prim(**{mapping.ATTR_ROAD_ID: "road_001", mapping.ATTR_CONTROL_POINT_ID: "cp_003"})
    resolved = mapping.resolve_prim(prim)
    assert resolved["control_point_id"] == "cp_003"


def test_resolve_untagged_prim_is_unknown() -> None:
    assert mapping.resolve_prim(_Prim()) == {"kind": "unknown", "id": None}
