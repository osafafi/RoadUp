"""Marking preset *schema* + loader. Values live in external YAML, not here. CODE_REFERENCE.md S8.

The editable values are in ``presets/markings.yaml`` (see ``presets/README.md``); this module only
defines the dataclasses and loads them. Initial values target UAE/GCC and are provisional pending
official validation — see the ``road-design-standards`` skill.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import yaml

from roadup.common.config import resolve_presets_dir
from roadup.common.errors import ValidationError

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
    return _load_cached(str(resolve_presets_dir(presets_dir)))


def get_preset(preset_id: str, presets_dir: str | Path | None = None) -> MarkingPreset:
    presets = load_marking_presets(presets_dir)
    try:
        return presets[preset_id]
    except KeyError:
        raise ValidationError(
            f"unknown marking preset {preset_id!r} (have: {sorted(presets)})"
        ) from None


@cache
def _load_cached(presets_dir: str) -> dict[str, MarkingPreset]:
    path = Path(presets_dir) / PRESET_FILE
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise ValidationError(f"cannot read marking presets at {path}: {exc}") from exc
    presets: dict[str, MarkingPreset] = {}
    for preset_id, spec in (raw.get("markings") or {}).items():
        presets[preset_id] = _parse_preset(preset_id, spec)
    return presets


def _parse_preset(preset_id: str, spec: dict) -> MarkingPreset:
    mat = spec.get("material") or {}
    color = mat.get("color", (1.0, 1.0, 1.0))
    material = MaterialParams(
        color=tuple(float(c) for c in color),  # type: ignore[arg-type]
        roughness=float(mat.get("roughness", 0.7)),
        metallic=float(mat.get("metallic", 0.0)),
        emissive=float(mat.get("emissive", 0.0)),
    )
    return MarkingPreset(
        id=preset_id,
        pattern=spec["pattern"],
        line_width=float(spec["line_width"]),
        dash_length=float(spec.get("dash_length", 0.0)),
        gap_length=float(spec.get("gap_length", 0.0)),
        separation=float(spec.get("separation", 0.0)),
        color=spec.get("color", "white"),
        material=material,
    )
