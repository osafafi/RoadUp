"""Integration: generate the USD stage from the showcase model and verify the scene contract.

Asserts the generated layer is sublayer-ready: stable id-keyed prim paths, ``roadup:*`` tags on
every prim, guide-curve rails for scene scatter/array, and that a ``*.scene.usda`` can sublayer it
and reference a rail path that still resolves after the road is regenerated. (needs pxr)
"""
from __future__ import annotations

import pytest

pytest.importorskip("pxr")

from examples.showcase import build_showcase_model  # noqa: E402
from roadup.opendrive.eval.sampler import Sampler  # noqa: E402
from roadup.tooling.commands import _rebake_road  # noqa: E402
from roadup.usd import mapping  # noqa: E402
from roadup.usd.stage import StageGenerator  # noqa: E402


@pytest.fixture
def generated():
    model = build_showcase_model()
    gen = StageGenerator(model, Sampler(model))
    gen.build_all()
    return model, gen


def test_every_road_and_junction_prim_is_tagged(generated) -> None:
    model, gen = generated
    for road_id in model.roads:
        prim = gen._stage.GetPrimAtPath(mapping.road_prim_path(road_id))
        assert prim and prim.GetAttribute(mapping.ATTR_ROAD_ID).Get() == road_id
    for junction_id in model.junctions:
        prim = gen._stage.GetPrimAtPath(mapping.junction_prim_path(junction_id))
        assert prim and prim.GetAttribute(mapping.ATTR_JUNCTION_ID).Get() == junction_id


def test_rails_are_guide_basis_curves(generated) -> None:
    from pxr import UsdGeom

    model, gen = generated
    guide_rails = [
        p
        for p in gen._stage.Traverse()
        if p.IsA(UsdGeom.BasisCurves)
        and UsdGeom.Imageable(p).GetPurposeAttr().Get() == UsdGeom.Tokens.guide
    ]
    assert guide_rails, "expected guide-curve rails for scene scatter"
    # at least one centerline + one lane edge across the network
    names = {p.GetName() for p in guide_rails}
    assert "Centerline" in names
    assert any(n.endswith("_Edge") for n in names)


def test_junction_surface_present_and_tagged(generated) -> None:
    model, gen = generated
    assert model.junctions, "showcase has junctions"
    for junction_id in model.junctions:
        surface = gen._stage.GetPrimAtPath(mapping.junction_surface_path(junction_id))
        assert surface and surface.GetAttribute(mapping.ATTR_JUNCTION_ID).Get() == junction_id


def test_scene_layer_sublayers_generated_and_references_a_rail(generated, tmp_path) -> None:
    from pxr import Sdf, Usd, UsdGeom

    model, gen = generated
    generated_path = tmp_path / "showcase.generated.usda"
    gen.export(str(generated_path))

    rail = mapping.centerline_rail_path("road_001")
    scene_path = tmp_path / "showcase.scene.usda"
    scene = Usd.Stage.CreateNew(str(scene_path))
    scene.GetRootLayer().subLayerPaths.append("./showcase.generated.usda")
    scatter = scene.DefinePrim("/World/Scatter")
    scatter.CreateRelationship("roadup:followCurve").AddTarget(Sdf.Path(rail))
    scene.GetRootLayer().Save()
    # composed rail resolves through the sublayer
    assert UsdGeom.BasisCurves(scene.GetPrimAtPath(rail))

    # regenerate the road; the scene's referenced rail path must still resolve
    road = model.get_road("road_001")
    road.user_data["controlPoints"][1]["pos"] = [70.0, 0.0, 0.0]
    _rebake_road(road)
    gen.update_road("road_001")
    gen.export(str(generated_path))
    reopened = Usd.Stage.Open(str(scene_path))
    assert reopened.GetPrimAtPath(rail), "rail path must survive road regeneration"
