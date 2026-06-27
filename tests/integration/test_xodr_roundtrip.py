"""Integration: write the showcase model, read it back, compare topology + userData end-to-end.

The showcase exercises every plan-view primitive the writer supports (line / arc / spiral /
paramPoly3), all lane types, double/broken/solid marks, and a width taper. This is the canonical
proof that the Stage-2 read path is the inverse of the Stage-1 write path.
"""
from pathlib import Path

from examples.showcase import build_showcase_model
from roadup.common.types import GeometryType
from roadup.opendrive.eval.sampler import Sampler
from roadup.opendrive.io.reader import LxmlFallbackReader
from roadup.opendrive.io.writer import ScenarioGenerationWriter


def _roundtrip(tmp_path: Path):
    out = tmp_path / "showcase.xodr"
    ScenarioGenerationWriter().write(build_showcase_model(), str(out))
    return build_showcase_model(), LxmlFallbackReader().parse(str(out))


def test_all_roads_and_lane_topology_survive(tmp_path: Path) -> None:
    original, restored = _roundtrip(tmp_path)
    assert list(restored.roads) == list(original.roads)
    for road_id, road in original.roads.items():
        got = restored.roads[road_id]
        for sec_o, sec_r in zip(road.lane_sections, got.lane_sections, strict=True):
            assert sec_r.lane_ids() == sec_o.lane_ids()
            for lane in sec_o._all_lanes():
                assert sec_r.lane(lane.id).type == lane.type


def test_every_geometry_primitive_roundtrips(tmp_path: Path) -> None:
    _, restored = _roundtrip(tmp_path)
    seen = {g.type for road in restored.roads.values() for g in road.geometry}
    assert {GeometryType.LINE, GeometryType.ARC, GeometryType.SPIRAL,
            GeometryType.PARAM_POLY3} <= seen


def test_userdata_survives_roundtrip(tmp_path: Path) -> None:
    original, restored = _roundtrip(tmp_path)
    for road_id, road in original.roads.items():
        assert restored.roads[road_id].user_data == road.user_data


def test_elevation_and_banking_survive_roundtrip(tmp_path: Path) -> None:
    """The climbing, banked curve keeps its vertical + lateral profiles; flat roads stay flat."""
    original, restored = _roundtrip(tmp_path)
    banked = restored.roads["road_006"]
    assert banked.elevation == original.roads["road_006"].elevation
    assert banked.superelevation == original.roads["road_006"].superelevation
    assert banked.elevation and banked.superelevation                 # non-trivial profiles
    # A flat road emits no profile records at all (byte-identical to the pre-4.5 output).
    assert restored.roads["road_001"].elevation == []
    assert restored.roads["road_001"].superelevation == []


def test_restored_model_is_samplable(tmp_path: Path) -> None:
    """The read-back model feeds the sampler — frames advance and lane boundaries exist."""
    _, restored = _roundtrip(tmp_path)
    sampler = Sampler(restored, step=2.0)
    frames = sampler.reference_frames("road_002")          # the arc
    assert len(frames) > 1
    assert frames[-1].s > frames[0].s
    boundaries = sampler.lane_boundaries("road_002", 0.0, frames[-1].s)
    assert {b.lane_id for b in boundaries} == {1, -1, -2}
