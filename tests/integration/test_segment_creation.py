"""Integration: author roads with SegmentBuilder, then prove the bake round-trips and samples true.

This is the author-side counterpart to test_xodr_roundtrip: instead of hand-authored records, the
roads are *drawn* (a Spline) and *baked* (SegmentBuilder + presets), then written, read back, and
sampled. The sampling check is the bake-correctness gate — the baked plan-view geometry must trace
the same curve the spline drew.
"""
from pathlib import Path

import numpy as np

from roadup.common.types import GeometryType, LaneType, RoadType
from roadup.geometry.splines import ControlPoint, Spline
from roadup.network.linkage import LinkResolver
from roadup.opendrive.eval.planview import sample_planview
from roadup.opendrive.io.reader import LxmlFallbackReader
from roadup.opendrive.io.writer import ScenarioGenerationWriter
from roadup.opendrive.model.network import OpenDriveModel
from roadup.segments.builder import SegmentBuilder


def _catmull_spline() -> Spline:
    return Spline(
        points=[
            ControlPoint(position=(0.0, 0.0, 0.0), id="cp_001"),
            ControlPoint(position=(20.0, 8.0, 0.0), id="cp_002"),
            ControlPoint(position=(40.0, 0.0, 0.0), id="cp_003"),
            ControlPoint(position=(60.0, -6.0, 0.0), id="cp_004"),
        ],
        kind="catmullRom",
    )


def test_builder_produces_valid_model_with_variety() -> None:
    model = OpenDriveModel()
    model.add_road(SegmentBuilder(RoadType.HIGHWAY)
                   .with_reference_line(_catmull_spline()).build("road_001"))
    assert model.validate() == []

    road = model.get_road("road_001")
    lane_types = {ln.type for ln in road.lane_sections[0]._all_lanes()}
    assert {LaneType.DRIVING, LaneType.SHOULDER} <= lane_types
    # Freeform catmullRom reference line bakes to paramPoly3 records (one per segment).
    assert {g.type for g in road.geometry} == {GeometryType.PARAM_POLY3}
    assert len(road.geometry) == 3


def test_baked_geometry_traces_the_drawn_spline() -> None:
    """The bake-correctness gate: sampled plan-view geometry matches the analytic spline curve."""
    spline = _catmull_spline()
    road = SegmentBuilder(RoadType.HIGHWAY).with_reference_line(spline).build("road_001")

    baked = np.array([f.position[:2] for f in sample_planview(road.geometry, step=1.0)])
    exact = np.array([spline.evaluate(float(t))[:2] for t in np.linspace(0.0, 1.0, 2000)])
    # Each baked station must lie on the drawn curve (planview numeric tolerance ~cm).
    deviation = np.sqrt(((baked[:, None, :] - exact[None, :, :]) ** 2).sum(-1)).min(1).max()
    assert deviation < 0.05

    # Endpoints land exactly on the first/last control points.
    assert np.allclose(baked[0], (0.0, 0.0), atol=1e-6)
    assert np.allclose(baked[-1], (60.0, -6.0), atol=1e-6)


def test_author_write_read_roundtrip_preserves_links_and_userdata(tmp_path: Path) -> None:
    model = OpenDriveModel()
    model.add_road(SegmentBuilder(RoadType.HIGHWAY)
                   .with_reference_line(_catmull_spline()).build("road_001"))
    model.add_road(SegmentBuilder(RoadType.ARTERIAL).with_lane_count(left=1, right=2)
                   .with_reference_line(
                       Spline(points=[ControlPoint(position=(60.0, -6.0, 0.0), id="cp_001"),
                                      ControlPoint(position=(110.0, -6.0, 0.0), id="cp_002")],
                              kind="line")).build("road_002"))
    LinkResolver(model).connect_roads("road_001", "end", "road_002", "start")

    out = tmp_path / "authored.xodr"
    ScenarioGenerationWriter().write(model, str(out))
    restored = LxmlFallbackReader().parse(str(out))

    assert list(restored.roads) == ["road_001", "road_002"]
    a, b = restored.get_road("road_001"), restored.get_road("road_002")
    assert a.link.successor == ("road", "road_002")
    assert b.link.predecessor == ("road", "road_001")
    # Lane links survive: shared driving lanes (1, -1, -2) are mapped.
    assert a.lane_sections[0].lane(-1).link.successor == -1
    assert b.lane_sections[0].lane(-1).link.predecessor == -1
    # Editing intent (spline kind + control points, width law) round-trips via <userData>.
    assert restored.get_road("road_001").user_data == model.get_road("road_001").user_data
