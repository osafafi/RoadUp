"""Build/cache UsdShade materials from marking presets. Owns pxr imports. CODE_REFERENCE.md S10.

``pxr`` is imported lazily inside methods so the module is importable without USD installed
(unit tests that need a stage call :func:`importorskip`).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from roadup.markings.material import material_key
from roadup.markings.presets import MaterialParams
from roadup.usd.mapping import MATERIALS_SCOPE

if TYPE_CHECKING:
    from roadup.markings.presets import MaterialParams as _MaterialParams  # noqa: F401

#: Default road-surface (asphalt) appearance — provisional, not marking-derived.
ASPHALT_PARAMS = MaterialParams(color=(0.08, 0.08, 0.08), roughness=0.9, metallic=0.0, emissive=0.0)


def _safe_name(key: str) -> str:
    """Make a material_key usable as a USD prim name (no ``.``/``-``)."""
    return "Mat_" + "".join(c if c.isalnum() else "_" for c in key)


class MaterialLibrary:
    """Create and dedup USD materials (keyed by :func:`roadup.markings.material.material_key`)."""

    def __init__(self, stage: Any, scope_path: str = MATERIALS_SCOPE) -> None:
        self._stage = stage
        self._scope = scope_path
        self._cache: dict[str, Any] = {}

    def get_or_create(self, params: MaterialParams) -> Any:  # -> UsdShade.Material
        from pxr import Gf, Sdf, UsdGeom, UsdShade

        key = material_key(params)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        UsdGeom.Scope.Define(self._stage, self._scope)
        path = f"{self._scope}/{_safe_name(key)}"
        material = UsdShade.Material.Define(self._stage, path)
        shader = UsdShade.Shader.Define(self._stage, f"{path}/Shader")
        shader.CreateIdAttr("UsdPreviewSurface")
        r, g, b = params.color
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(r, g, b))
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(params.roughness))
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(params.metallic))
        if params.emissive > 0.0:
            e = float(params.emissive)
            shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(
                Gf.Vec3f(r * e, g * e, b * e)
            )
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")

        self._cache[key] = material
        return material

    def asphalt(self) -> Any:  # -> UsdShade.Material
        """The shared default road-surface material."""
        return self.get_or_create(ASPHALT_PARAMS)
