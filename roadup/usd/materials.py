"""Build/cache UsdShade materials from marking presets. Owns pxr imports. CODE_REFERENCE.md S10."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from roadup.markings.presets import MaterialParams


class MaterialLibrary:
    """Create and dedup USD materials (keyed by :func:`roadup.markings.material.material_key`)."""

    def __init__(self, stage: Any) -> None:
        self._stage = stage

    def get_or_create(self, params: "MaterialParams") -> Any:  # -> UsdShade.Material
        raise NotImplementedError

    def asphalt(self) -> Any:  # -> UsdShade.Material
        raise NotImplementedError
