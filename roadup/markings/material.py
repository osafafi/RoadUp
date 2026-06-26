"""Material-key helpers so identical marking materials are shared. CODE_REFERENCE.md S8."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from roadup.markings.presets import MaterialParams


def material_key(params: "MaterialParams") -> str:
    """Stable key for a set of material parameters (dedup in the USD material library)."""
    raise NotImplementedError
