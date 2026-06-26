"""Material-key helpers so identical marking materials are shared. CODE_REFERENCE.md S8."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from roadup.markings.presets import MaterialParams


def material_key(params: MaterialParams) -> str:
    """Stable key for a set of material parameters (dedup in the USD material library).

    Rounded to avoid float jitter splitting otherwise-identical materials.
    """
    r, g, b = (round(c, 4) for c in params.color)
    return (
        f"mat_{r}_{g}_{b}"
        f"_r{round(params.roughness, 4)}"
        f"_m{round(params.metallic, 4)}"
        f"_e{round(params.emissive, 4)}"
    )
