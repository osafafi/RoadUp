"""Integration: write the showcase model and assert it exercises the writer's full variety.

The same model backs ``examples/generate_xodr_samples.py`` — run that script to drop the .xodr
files into ``examples/out/`` for opening in an OpenDRIVE visualizer.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

from examples.showcase import build_showcase_model
from roadup.opendrive.io.writer import ScenarioGenerationWriter


def _showcase_root(tmp_path: Path) -> ET.Element:
    model = build_showcase_model()
    assert model.validate() == []
    out = tmp_path / "showcase.xodr"
    ScenarioGenerationWriter().write(model, str(out))
    return ET.parse(out).getroot()


def test_showcase_covers_all_geometry_primitives(tmp_path: Path) -> None:
    root = _showcase_root(tmp_path)
    primitives = {g.tag for g in root.findall(".//planView/geometry/*")}
    assert {"line", "arc", "spiral", "paramPoly3"} <= primitives


def test_showcase_covers_lane_and_marking_variety(tmp_path: Path) -> None:
    root = _showcase_root(tmp_path)

    lane_types = {ln.get("type") for ln in root.findall(".//lane")}
    assert {"driving", "shoulder", "sidewalk", "biking"} <= lane_types

    mark_colors = {m.get("color") for m in root.findall(".//roadMark")}
    assert {"white", "yellow"} <= mark_colors

    mark_types = {m.get("type") for m in root.findall(".//roadMark")}
    # single + dashed + double all present (double serializes as "solid solid").
    assert {"solid", "broken", "solid solid"} <= mark_types


def test_showcase_has_a_width_taper(tmp_path: Path) -> None:
    root = _showcase_root(tmp_path)
    tapered = [w for w in root.findall(".//width") if float(w.get("b")) != 0.0]
    assert tapered, "expected at least one lane with a non-constant width law"


def test_showcase_header_is_opendrive_17(tmp_path: Path) -> None:
    root = _showcase_root(tmp_path)
    header = root.find("header")
    assert header is not None
    assert (header.get("revMajor"), header.get("revMinor")) == ("1", "7")
