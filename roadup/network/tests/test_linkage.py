"""Unit tests for roadup.network.linkage."""
import pytest

from roadup.common.errors import TopologyError
from roadup.common.types import LaneType
from roadup.network.linkage import LinkResolver
from roadup.opendrive.model.network import OpenDriveModel
from roadup.opendrive.model.road import Lane, LaneSection, Road


def _road(road_id: str) -> Road:
    section = LaneSection(
        s=0.0,
        left=[Lane(id=1, type=LaneType.DRIVING)],
        center=Lane(id=0, type=LaneType.NONE),
        right=[Lane(id=-1, type=LaneType.DRIVING), Lane(id=-2, type=LaneType.DRIVING)],
    )
    return Road(id=road_id, length=10.0, lane_sections=[section])


def _model() -> OpenDriveModel:
    model = OpenDriveModel()
    model.add_road(_road("road_001"))
    model.add_road(_road("road_002"))
    return model


def test_connect_sets_road_links_by_contact() -> None:
    model = _model()
    LinkResolver(model).connect_roads("road_001", "end", "road_002", "start")
    a = model.get_road("road_001")
    b = model.get_road("road_002")
    assert a.link.successor == ("road", "road_002")
    assert b.link.predecessor == ("road", "road_001")
    assert a.link.predecessor is None and b.link.successor is None


def test_default_lane_map_pairs_driving_lanes() -> None:
    model = _model()
    mapping = LinkResolver(model).default_lane_map("road_001", "road_002")
    assert mapping == {1: 1, -1: -1, -2: -2}  # center (0) excluded


def test_connect_sets_lane_links() -> None:
    model = _model()
    LinkResolver(model).connect_roads("road_001", "end", "road_002", "start")
    a = model.get_road("road_001").lane_sections[0]
    b = model.get_road("road_002").lane_sections[0]
    assert a.lane(-1).link.successor == -1
    assert b.lane(-1).link.predecessor == -1


def test_explicit_lane_map_validated_before_mutation() -> None:
    from roadup.common.errors import ValidationError

    model = _model()
    with pytest.raises(ValidationError):
        LinkResolver(model).connect_roads(
            "road_001", "end", "road_002", "start", lane_map={-1: 99}
        )
    # Nothing should have been mutated (atomic).
    assert model.get_road("road_001").link.successor is None


def test_disconnect_clears_links() -> None:
    model = _model()
    resolver = LinkResolver(model)
    resolver.connect_roads("road_001", "end", "road_002", "start")
    resolver.disconnect("road_001", "road_002")
    a = model.get_road("road_001")
    assert a.link.successor is None
    assert a.lane_sections[0].lane(-1).link.successor is None


def test_revalidate_flags_missing_target_lane() -> None:
    model = _model()
    resolver = LinkResolver(model)
    resolver.connect_roads("road_001", "end", "road_002", "start")
    # Remove a lane from road_002 so road_001's lane link is now unsatisfiable.
    sec = model.get_road("road_002").lane_sections[0]
    sec.right = [ln for ln in sec.right if ln.id != -1]
    warnings = resolver.revalidate("road_001")
    assert any("-1" in w for w in warnings)


def test_bad_contact_raises() -> None:
    model = _model()
    with pytest.raises(TopologyError):
        LinkResolver(model).connect_roads("road_001", "middle", "road_002", "start")
