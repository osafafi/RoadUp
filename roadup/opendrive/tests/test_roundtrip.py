"""Round-trip tests: model -> write (.xodr) -> read -> compare topology + userData."""
from pathlib import Path

from roadup.common.types import GeometryType, LaneType
from roadup.opendrive.io.reader import LxmlFallbackReader
from roadup.opendrive.io.writer import ScenarioGenerationWriter
from roadup.opendrive.model.network import Header, OpenDriveModel
from roadup.opendrive.model.road import (
    Geometry,
    Lane,
    LaneSection,
    Road,
    RoadMark,
    WidthRecord,
)


def _model() -> OpenDriveModel:
    line = Road(
        id="road_001", length=50.0,
        geometry=[Geometry(s=0.0, x=0.0, y=0.0, hdg=0.0, length=50.0, type=GeometryType.LINE)],
        lane_sections=[LaneSection(
            s=0.0,
            center=Lane(id=0, type=LaneType.NONE,
                        road_marks=[RoadMark(s_offset=0.0, type="broken", color="white",
                                             dash_length=3.0, gap_length=9.0)]),
            right=[Lane(id=-1, type=LaneType.DRIVING, widths=[WidthRecord(s_offset=0.0, a=3.5)],
                        road_marks=[RoadMark(s_offset=0.0, type="solid", color="white")],
                        user_data={"kind": "lane", "markingPreset": "white_solid"})],
        )],
        user_data={"kind": "referenceLine", "splineKind": "line"},
    )
    arc = Road(
        id="road_002", length=40.0,
        geometry=[Geometry(s=0.0, x=0.0, y=20.0, hdg=0.0, length=40.0,
                           type=GeometryType.ARC, params={"curvature": 0.02})],
        lane_sections=[LaneSection(
            s=0.0,
            center=Lane(id=0, type=LaneType.NONE),
            left=[Lane(id=1, type=LaneType.DRIVING, widths=[WidthRecord(s_offset=0.0, a=3.25)])],
        )],
    )
    model = OpenDriveModel(header=Header(name="RoadUp", version="1.7"))
    model.add_road(line)
    model.add_road(arc)
    return model


def _roundtrip(tmp_path: Path) -> OpenDriveModel:
    out = tmp_path / "rt.xodr"
    ScenarioGenerationWriter().write(_model(), str(out))
    return LxmlFallbackReader().parse(str(out))


def test_topology_roundtrips(tmp_path: Path) -> None:
    original, restored = _model(), _roundtrip(tmp_path)
    assert list(restored.roads) == list(original.roads)
    for road_id, road in original.roads.items():
        got = restored.roads[road_id]
        assert got.length == road.length
        # lane sections: same count, same signed lane ids per section
        assert len(got.lane_sections) == len(road.lane_sections)
        for sec_o, sec_r in zip(road.lane_sections, got.lane_sections, strict=True):
            assert sec_r.lane_ids() == sec_o.lane_ids()
            for lane_o in sec_o._all_lanes():
                lane_r = sec_r.lane(lane_o.id)
                assert lane_r.type == lane_o.type
                assert [(w.a, w.b, w.c, w.d) for w in lane_r.widths] == \
                    [(w.a, w.b, w.c, w.d) for w in lane_o.widths]


def test_geometry_types_roundtrip(tmp_path: Path) -> None:
    restored = _roundtrip(tmp_path)
    assert [g.type for g in restored.roads["road_001"].geometry] == [GeometryType.LINE]
    assert [g.type for g in restored.roads["road_002"].geometry] == [GeometryType.ARC]
    assert restored.roads["road_002"].geometry[0].params["curvature"] == 0.02


def test_userdata_roundtrips(tmp_path: Path) -> None:
    restored = _roundtrip(tmp_path)
    assert restored.roads["road_001"].user_data == {"kind": "referenceLine", "splineKind": "line"}
    lane = restored.roads["road_001"].lane_sections[0].right[0]
    assert lane.user_data == {"kind": "lane", "markingPreset": "white_solid"}


def test_roadmark_dash_dimensions_roundtrip(tmp_path: Path) -> None:
    restored = _roundtrip(tmp_path)
    center = restored.roads["road_001"].lane_sections[0].center
    assert center is not None
    mark = center.road_marks[0]
    assert (mark.type, mark.dash_length, mark.gap_length) == ("broken", 3.0, 9.0)
