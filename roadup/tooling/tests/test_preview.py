"""Unit tests for roadup.tooling.preview (needs pxr for the stage)."""
from __future__ import annotations

import pytest

pytest.importorskip("pxr")

from roadup.tooling.preview import PreviewGenerator  # noqa: E402


def test_road_preview_emits_a_guide_centerline(simple_model) -> None:
    from pxr import UsdGeom

    road = simple_model.get_road("road_002")
    gen = PreviewGenerator()
    stage = gen.road_preview(road)
    curve = UsdGeom.BasisCurves(stage.GetPrimAtPath("/Preview/Centerline"))
    assert curve
    assert curve.GetPurposeAttr().Get() == UsdGeom.Tokens.guide
    assert len(curve.GetPointsAttr().Get()) >= 2


def test_clear_drops_the_stage(simple_model) -> None:
    gen = PreviewGenerator()
    gen.road_preview(simple_model.get_road("road_002"))
    gen.clear()
    assert gen._stage is None
