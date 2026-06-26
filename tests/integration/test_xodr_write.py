"""Integration: author a straight road from the model and write a valid OpenDRIVE 1.7 .xodr.

This is the Stage 1 vertical slice — it proves the model → io (scenariogeneration) path end to
end. The reader/round-trip lives in Stage 2 (see test_xodr_roundtrip.py, still skipped).
"""
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


def build_straight_2lane(road_id: str = "road_001", length: float = 50.0) -> OpenDriveModel:
    """One straight road: a LINE reference line + 2 driving lanes with edge/center markings."""
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
                road_marks=[RoadMark(s_offset=0.0, type="broken", color="white", width=0.12)],
                user_data={"kind": "lane", "markingPreset": "white_dashed"},
            ),
            Lane(
                id=-2,
                type=LaneType.DRIVING,
                widths=[WidthRecord(s_offset=0.0, a=3.5)],
                road_marks=[RoadMark(s_offset=0.0, type="solid", color="white", width=0.15)],
                user_data={"kind": "lane", "markingPreset": "white_solid"},
            ),
        ],
    )
    road = Road(
        id=road_id,
        length=length,
        geometry=[Geometry(s=0.0, x=0.0, y=0.0, hdg=0.0, length=length, type=GeometryType.LINE)],
        lane_sections=[section],
        user_data={"kind": "referenceLine", "splineKind": "line"},
    )
    model = OpenDriveModel(header=Header(name="RoadUp", version="1.7"))
    model.add_road(road)
    return model


def test_author_and_write_straight_road(tmp_path: Path) -> None:
    model = build_straight_2lane()
    assert model.validate() == []

    out = tmp_path / "straight_2lane.xodr"
    ScenarioGenerationWriter().write(model, str(out))

    text = out.read_text(encoding="utf-8")
    # Show the generated .xodr for audit (visible with `pytest -s`).
    print("\n----- straight_2lane.xodr -----\n" + text)

    root = ET.fromstring(text)
    assert root.tag == "OpenDRIVE"

    header = root.find("header")
    assert header is not None
    assert header.get("revMajor") == "1"
    assert header.get("revMinor") == "7"  # OpenDRIVE 1.7 target

    # Reference-line geometry is a single straight line of the road length.
    line = root.find(".//planView/geometry/line")
    assert line is not None
    road = root.find("road")
    assert road is not None and road.get("length") == "50.0"

    # Two driving lanes on the right, each with a width law and a road mark.
    right_lanes = root.findall(".//laneSection/right/lane")
    assert len(right_lanes) == 2
    assert all(ln.get("type") == "driving" for ln in right_lanes)
    assert len(root.findall(".//laneSection/right/lane/width")) == 2
    assert len(root.findall(".//lane/roadMark")) >= 3

    # Editing intent round-trips through <userData code="roadup">.
    payloads = [decode(ud.get("value") or "") for ud in root.findall(".//userData[@code='roadup']")]
    assert {"kind": "referenceLine", "splineKind": "line"} in payloads
    assert {"kind": "lane", "markingPreset": "white_solid"} in payloads
