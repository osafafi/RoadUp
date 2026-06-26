"""Unit tests for roadup.opendrive.io.reader (pure-Python LxmlFallbackReader)."""
from pathlib import Path

from roadup.common.types import GeometryType, LaneType
from roadup.opendrive.io.reader import LxmlFallbackReader, default_reader
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
    section = LaneSection(
        s=0.0,
        center=Lane(id=0, type=LaneType.NONE,
                    road_marks=[RoadMark(s_offset=0.0, type="broken", color="white",
                                         dash_length=3.0, gap_length=9.0)]),
        right=[
            Lane(id=-1, type=LaneType.DRIVING,
                 widths=[WidthRecord(s_offset=0.0, a=3.0, b=0.04),
                         WidthRecord(s_offset=25.0, a=4.0)],
                 road_marks=[RoadMark(s_offset=0.0, type="solid", color="white", width=0.15)],
                 user_data={"kind": "lane", "markingPreset": "white_solid"}),
            Lane(id=-2, type=LaneType.SHOULDER, widths=[WidthRecord(s_offset=0.0, a=2.5)],
                 road_marks=[RoadMark(s_offset=0.0, type="solid", weight="bold", width=0.25)]),
        ],
    )
    road = Road(
        id="road_001", length=50.0,
        geometry=[Geometry(s=0.0, x=0.0, y=0.0, hdg=0.0, length=50.0, type=GeometryType.LINE)],
        lane_sections=[section],
        user_data={"kind": "referenceLine", "splineKind": "line"},
    )
    model = OpenDriveModel(header=Header(name="RoadUp", version="1.7"))
    model.add_road(road)
    return model


def _write_and_read(tmp_path: Path) -> OpenDriveModel:
    out = tmp_path / "r.xodr"
    ScenarioGenerationWriter().write(_model(), str(out))
    return LxmlFallbackReader().parse(str(out))


def test_default_reader_falls_back_to_pure_python() -> None:
    assert isinstance(default_reader(), LxmlFallbackReader)


def test_reads_header_and_road(tmp_path: Path) -> None:
    model = _write_and_read(tmp_path)
    assert model.header.version == "1.7"
    assert list(model.roads) == ["road_001"]
    road = model.roads["road_001"]
    assert road.length == 50.0
    assert road.junction is None
    assert road.user_data == {"kind": "referenceLine", "splineKind": "line"}


def test_reads_geometry_record(tmp_path: Path) -> None:
    road = _write_and_read(tmp_path).roads["road_001"]
    assert len(road.geometry) == 1
    assert road.geometry[0].type == GeometryType.LINE
    assert road.geometry[0].length == 50.0


def test_reads_lanes_widths_and_userdata(tmp_path: Path) -> None:
    section = _write_and_read(tmp_path).roads["road_001"].lane_sections[0]
    assert section.center is not None and section.center.id == 0
    assert [ln.id for ln in section.right] == [-1, -2]
    assert section.right[0].type == LaneType.DRIVING
    assert section.right[1].type == LaneType.SHOULDER

    lane = section.right[0]
    assert lane.user_data == {"kind": "lane", "markingPreset": "white_solid"}
    assert [(w.s_offset, w.a, w.b) for w in lane.widths] == [(0.0, 3.0, 0.04), (25.0, 4.0, 0.0)]


def test_reads_roadmark_dash_dimensions(tmp_path: Path) -> None:
    section = _write_and_read(tmp_path).roads["road_001"].lane_sections[0]
    assert section.center is not None
    broken = section.center.road_marks[0]
    assert broken.type == "broken"
    assert broken.dash_length == 3.0
    assert broken.gap_length == 9.0
    # A solid mark has no dash child -> dash/gap stay None.
    solid = section.right[0].road_marks[0]
    assert solid.type == "solid"
    assert solid.dash_length is None and solid.gap_length is None
