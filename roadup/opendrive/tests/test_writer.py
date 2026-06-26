"""Unit tests for roadup.opendrive.io.writer (scenariogeneration backend)."""
import xml.etree.ElementTree as ET
from pathlib import Path

from roadup.common.types import GeometryType, LaneType
from roadup.opendrive.io.userdata import decode
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


def _straight_two_lane_model() -> OpenDriveModel:
    section = LaneSection(
        s=0.0,
        center=Lane(
            id=0,
            type=LaneType.NONE,
            road_marks=[RoadMark(s_offset=0.0, type="broken", color="white", width=0.15)],
        ),
        right=[
            Lane(
                id=-1,
                type=LaneType.DRIVING,
                widths=[WidthRecord(s_offset=0.0, a=3.5)],
                road_marks=[RoadMark(s_offset=0.0, type="solid", color="white", width=0.15)],
                user_data={"kind": "lane", "markingPreset": "white_solid"},
            ),
            Lane(
                id=-2,
                type=LaneType.DRIVING,
                widths=[WidthRecord(s_offset=0.0, a=3.5)],
                road_marks=[RoadMark(s_offset=0.0, type="solid", color="white", width=0.15)],
            ),
        ],
    )
    road = Road(
        id="road_001",
        length=50.0,
        geometry=[Geometry(s=0.0, x=0.0, y=0.0, hdg=0.0, length=50.0, type=GeometryType.LINE)],
        lane_sections=[section],
        user_data={"kind": "referenceLine", "splineKind": "line"},
    )
    model = OpenDriveModel(header=Header(name="RoadUp", version="1.7"))
    model.add_road(road)
    return model


def test_writer_produces_valid_xodr(tmp_path: Path) -> None:
    out = tmp_path / "straight.xodr"
    ScenarioGenerationWriter().write(_straight_two_lane_model(), str(out))
    assert out.is_file()

    root = ET.parse(out).getroot()
    assert root.tag == "OpenDRIVE"

    header = root.find("header")
    assert header is not None
    assert header.get("revMajor") == "1"
    assert header.get("revMinor") == "7"


def test_writer_emits_lanes_widths_and_roadmarks(tmp_path: Path) -> None:
    out = tmp_path / "straight.xodr"
    ScenarioGenerationWriter().write(_straight_two_lane_model(), str(out))
    root = ET.parse(out).getroot()

    road = root.find("road")
    assert road is not None
    assert road.get("length") == "50.0"
    assert road.find(".//planView/geometry/line") is not None

    right_lanes = root.findall(".//laneSection/right/lane")
    assert len(right_lanes) == 2
    widths = root.findall(".//laneSection/right/lane/width")
    assert len(widths) == 2
    assert all(w.get("a") is not None for w in widths)
    roadmarks = root.findall(".//lane/roadMark")
    assert len(roadmarks) >= 3  # center + two right lanes


def test_writer_roundtrips_userdata(tmp_path: Path) -> None:
    out = tmp_path / "straight.xodr"
    ScenarioGenerationWriter().write(_straight_two_lane_model(), str(out))
    root = ET.parse(out).getroot()

    userdatas = root.findall(".//userData[@code='roadup']")
    assert userdatas, "expected roadup userData payloads"
    payloads = [decode(ud.get("value") or "") for ud in userdatas]
    assert {"kind": "referenceLine", "splineKind": "line"} in payloads
    assert {"kind": "lane", "markingPreset": "white_solid"} in payloads
