"""Unit tests for roadup.opendrive.model (road methods + network container)."""
import pytest

from roadup.common.errors import ValidationError
from roadup.common.types import GeometryType, LaneType
from roadup.opendrive.model.junction import Connection, Junction, LaneLinkPair
from roadup.opendrive.model.network import Header, OpenDriveModel
from roadup.opendrive.model.road import (
    Geometry,
    Lane,
    LaneSection,
    Road,
    RoadLink,
    WidthRecord,
)


def _two_lane_section(s: float = 0.0) -> LaneSection:
    return LaneSection(
        s=s,
        left=[Lane(id=1, type=LaneType.DRIVING)],
        center=Lane(id=0, type=LaneType.NONE),
        right=[Lane(id=-1, type=LaneType.DRIVING)],
    )


def test_lane_section_lookup() -> None:
    section = _two_lane_section()
    assert section.lane(0).type == LaneType.NONE
    assert section.lane(-1).type == LaneType.DRIVING
    assert section.lane_ids() == [1, 0, -1]


def test_lane_section_unknown_lane_raises() -> None:
    with pytest.raises(ValidationError):
        _two_lane_section().lane(99)


def test_road_lane_section_at() -> None:
    road = Road(
        id="road_001",
        length=100.0,
        lane_sections=[_two_lane_section(0.0), _two_lane_section(50.0)],
    )
    assert road.lane_section_at(0.0).s == 0.0
    assert road.lane_section_at(25.0).s == 0.0
    assert road.lane_section_at(50.0).s == 50.0
    assert road.lane_section_at(80.0).s == 50.0


def test_road_lane_section_at_empty_raises() -> None:
    with pytest.raises(ValidationError):
        Road(id="road_002").lane_section_at(0.0)


def _straight_road(road_id: str = "road_001") -> Road:
    return Road(
        id=road_id,
        length=10.0,
        geometry=[Geometry(s=0.0, x=0.0, y=0.0, hdg=0.0, length=10.0, type=GeometryType.LINE)],
        lane_sections=[
            LaneSection(
                s=0.0,
                center=Lane(id=0),
                right=[Lane(id=-1, widths=[WidthRecord(s_offset=0.0, a=3.5)])],
            )
        ],
    )


def test_add_get_remove_road() -> None:
    model = OpenDriveModel()
    road = _straight_road()
    model.add_road(road)
    assert model.get_road("road_001") is road
    model.remove_road("road_001")
    assert "road_001" not in model.roads


def test_add_duplicate_road_raises() -> None:
    model = OpenDriveModel()
    model.add_road(_straight_road())
    with pytest.raises(ValidationError):
        model.add_road(_straight_road())


def test_get_missing_road_raises() -> None:
    with pytest.raises(ValidationError):
        OpenDriveModel().get_road("road_999")


def test_validate_clean_model() -> None:
    model = OpenDriveModel(header=Header(version="1.7"))
    model.add_road(_straight_road())
    assert model.validate() == []


def test_validate_flags_dangling_link() -> None:
    model = OpenDriveModel()
    road = _straight_road()
    road.link = RoadLink(successor=("road", "road_404"))
    model.add_road(road)
    messages = model.validate()
    assert any("road_404" in m for m in messages)


def test_remove_road_cascades_to_junction_connections() -> None:
    model = OpenDriveModel()
    model.add_road(_straight_road("road_001"))
    model.add_road(_straight_road("road_002"))
    junction = Junction(
        id="junction_001",
        connections=[
            Connection(
                id="c0",
                incoming_road="road_001",
                connecting_road="road_002",
                lane_links=[LaneLinkPair(from_lane=-1, to_lane=-1)],
            )
        ],
    )
    model.add_junction(junction)
    model.remove_road("road_001")
    assert model.junctions["junction_001"].connections == []
