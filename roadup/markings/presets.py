"""Marking preset *schema* + loader. Values live in external YAML, not here. CODE_REFERENCE.md S8.

The editable values are in ``presets/markings.yaml`` (see ``presets/README.md``); this module only
defines the dataclasses and loads them. Initial values target UAE/GCC and are provisional pending
official validation — see the ``road-design-standards`` skill.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

#: Filename within the resolved presets directory (roadup.common.config.resolve_presets_dir).
PRESET_FILE = "markings.yaml"


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


def load_marking_presets(presets_dir: str | Path | None = None) -> dict[str, MarkingPreset]:
    """Load and parse ``presets/markings.yaml`` into :class:`MarkingPreset` objects.

    ``presets_dir`` defaults to :func:`roadup.common.config.resolve_presets_dir`.
    """
    raise NotImplementedError


def get_preset(preset_id: str, presets_dir: str | Path | None = None) -> MarkingPreset:
    raise NotImplementedError
