"""Unit tests for roadup.network.graph."""
import pytest

from roadup.common.types import LaneType
from roadup.network.graph import RoadGraph
from roadup.network.linkage import LinkResolver
from roadup.opendrive.model.network import OpenDriveModel
from roadup.opendrive.model.road import Lane, LaneSection, Road


def _road(road_id: str, junction: str | None = None) -> Road:
    section = LaneSection(
        s=0.0,
        center=Lane(id=0, type=LaneType.NONE),
        right=[Lane(id=-1, type=LaneType.DRIVING)],
    )
    return Road(id=road_id, length=10.0, lane_sections=[section], junction=junction)


def test_neighbors_reflect_road_links() -> None:
    model = OpenDriveModel()
    model.add_road(_road("road_001"))
    model.add_road(_road("road_002"))
    model.add_road(_road("road_003"))
    LinkResolver(model).connect_roads("road_001", "end", "road_002", "start")
    graph = RoadGraph(model)
    assert graph.neighbors("road_001") == ["road_002"]
    assert graph.neighbors("road_002") == ["road_001"]
    assert graph.neighbors("road_003") == []


def test_junction_of() -> None:
    model = OpenDriveModel()
    model.add_road(_road("road_010", junction="junction_001"))
    graph = RoadGraph(model)
    assert graph.junction_of("road_010") == "junction_001"


def test_rebuild_picks_up_new_links() -> None:
    model = OpenDriveModel()
    model.add_road(_road("road_001"))
    model.add_road(_road("road_002"))
    graph = RoadGraph(model)
    assert graph.neighbors("road_001") == []
    LinkResolver(model).connect_roads("road_001", "end", "road_002", "start")
    graph.rebuild()
    assert graph.neighbors("road_001") == ["road_002"]


def test_unknown_road_raises() -> None:
    graph = RoadGraph(OpenDriveModel())
    with pytest.raises(KeyError):
        graph.neighbors("road_999")
