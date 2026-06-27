"""Unit tests for roadup.usd.materials (needs pxr)."""
from __future__ import annotations

import pytest

pytest.importorskip("pxr")

from roadup.markings.presets import MaterialParams  # noqa: E402
from roadup.usd.materials import MaterialLibrary  # noqa: E402


def _stage():
    from pxr import Usd

    return Usd.Stage.CreateInMemory()


def test_get_or_create_dedups_identical_params() -> None:
    lib = MaterialLibrary(_stage())
    p = MaterialParams(color=(1.0, 1.0, 1.0), roughness=0.7)
    a = lib.get_or_create(p)
    b = lib.get_or_create(MaterialParams(color=(1.0, 1.0, 1.0), roughness=0.7))
    assert a.GetPath() == b.GetPath()


def test_distinct_params_make_distinct_materials() -> None:
    lib = MaterialLibrary(_stage())
    white = lib.get_or_create(MaterialParams(color=(1.0, 1.0, 1.0)))
    yellow = lib.get_or_create(MaterialParams(color=(1.0, 0.8, 0.0)))
    assert white.GetPath() != yellow.GetPath()


def test_asphalt_has_preview_surface_shader() -> None:
    from pxr import UsdShade

    lib = MaterialLibrary(_stage())
    mat = lib.asphalt()
    shader = UsdShade.Shader(mat.GetPrim().GetStage().GetPrimAtPath(f"{mat.GetPath()}/Shader"))
    assert shader.GetIdAttr().Get() == "UsdPreviewSurface"
