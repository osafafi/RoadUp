"""Road-marking presets: pattern, dimensions, material params. CODE_REFERENCE.md S8."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MaterialParams:
    """Consumed by the USD layer to build/bind a material; persisted via <userData>."""

    color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    roughness: float = 0.7
    metallic: float = 0.0
    emissive: float = 0.0


@dataclass(frozen=True)
class MarkingPreset:
    id: str
    pattern: str            # "solid" | "broken" | "double_solid" | "solid_broken" | "broken_solid"
    line_width: float       # meters
    dash_length: float = 0.0   # 0 for solid
    gap_length: float = 0.0
    separation: float = 0.0    # gap between the two lines of a double marking
    color: str = "white"       # "white" | "yellow"
    material: MaterialParams = field(default_factory=MaterialParams)


MARKING_PRESETS: dict[str, MarkingPreset] = {
    "white_solid": MarkingPreset("white_solid", "solid", 0.15, color="white"),
    "white_dashed": MarkingPreset("white_dashed", "broken", 0.15, 3.0, 3.0, color="white"),
    "yellow_solid": MarkingPreset("yellow_solid", "solid", 0.15, color="yellow",
                                  material=MaterialParams(color=(1.0, 0.85, 0.0))),
    "yellow_double": MarkingPreset("yellow_double", "double_solid", 0.15, separation=0.15,
                                   color="yellow", material=MaterialParams(color=(1.0, 0.85, 0.0))),
    "white_edge_bold": MarkingPreset("white_edge_bold", "solid", 0.25, color="white"),
    # Presets only for v2; add more during the build session.
}


def get_preset(preset_id: str) -> MarkingPreset:
    raise NotImplementedError
