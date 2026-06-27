"""Unit tests for roadup.usd.stage (needs pxr)."""
from __future__ import annotations

import pytest

pytest.importorskip("pxr")

from roadup.opendrive.eval.sampler import Sampler  # noqa: E402
from roadup.tooling.commands import _rebake_road  # noqa: E402
from roadup.usd import mapping  # noqa: E402
from roadup.usd.stage import StageGenerator  # noqa: E402


def _build(model):
    gen = StageGenerator(model, Sampler(model))
    gen.build_all()
    return gen


def test_stage_metadata_is_meters_zup(simple_model) -> None:
    from pxr import UsdGeom

    gen = _build(simple_model)
    stage = gen._stage
    assert UsdGeom.GetStageMetersPerUnit(stage) == 1.0
    assert UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z
    assert stage.GetDefaultPrim().GetPath().pathString == mapping.ROOT_SCOPE


def test_road_surface_is_tagged(simple_model) -> None:
    gen = _build(simple_model)
    surface = gen._stage.GetPrimAtPath(mapping.road_surface_path("road_001"))
    assert surface and surface.GetAttribute(mapping.ATTR_ROAD_ID).Get() == "road_001"


def test_centerline_rail_is_guide_curve(simple_model) -> None:
    from pxr import UsdGeom

    gen = _build(simple_model)
    prim = gen._stage.GetPrimAtPath(mapping.centerline_rail_path("road_001"))
    curve = UsdGeom.BasisCurves(prim)
    assert curve
    assert curve.GetPurposeAttr().Get() == UsdGeom.Tokens.guide
    assert curve.GetTypeAttr().Get() == UsdGeom.Tokens.linear
    assert prim.GetAttribute(mapping.ATTR_ROAD_ID).Get() == "road_001"


def test_lane_rail_carries_lane_id(simple_model) -> None:
    gen = _build(simple_model)
    prim = gen._stage.GetPrimAtPath(mapping.lane_rail_path("road_001", -1))
    assert prim and prim.GetAttribute(mapping.ATTR_LANE_ID).Get() == -1


def test_marking_strip_tagged_and_bound(simple_model) -> None:
    from pxr import UsdShade

    gen = _build(simple_model)
    # road_001 lane +1 has a lane-divider marking from the highway preset.
    prim = gen._stage.GetPrimAtPath(mapping.lane_marking_prim_path("road_001", 1))
    assert prim and prim.GetAttribute(mapping.ATTR_LANE_ID).Get() == 1
    assert UsdShade.MaterialBindingAPI(prim).GetDirectBinding().GetMaterial()


def test_update_road_keeps_paths_stable(simple_model) -> None:
    gen = _build(simple_model)
    before = sorted(p.GetPath().pathString for p in gen._stage.Traverse())
    road = simple_model.get_road("road_002")
    road.user_data["controlPoints"][1]["pos"] = [20.0, 80.0, 0.0]
    _rebake_road(road)
    gen.update_road("road_002")
    after = sorted(p.GetPath().pathString for p in gen._stage.Traverse())
    assert before == after


def test_export_roundtrips_through_disk(simple_model, tmp_path) -> None:
    from pxr import Usd

    gen = _build(simple_model)
    out = tmp_path / "generated.usda"
    gen.export(str(out))
    reopened = Usd.Stage.Open(str(out))
    assert reopened.GetPrimAtPath(mapping.centerline_rail_path("road_001"))
