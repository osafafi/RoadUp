"""Road-type preset *schema* + loader. Values live in external YAML, not here. CODE_REFERENCE.md S7.

The editable values are in ``presets/road_types.yaml`` (see ``presets/README.md``); this module only
defines the dataclasses and loads them. Initial values target UAE/GCC and are provisional pending
official validation — see the ``road-design-standards`` skill.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

from roadup.common.config import resolve_presets_dir
from roadup.common.errors import ValidationError
from roadup.common.types import LaneType, RoadType

#: Filename within the resolved presets directory (roadup.common.config.resolve_presets_dir).
PRESET_FILE = "road_types.yaml"


@dataclass(frozen=True)
class LaneSpec:
    type: LaneType
    width: float
    marking_preset: str = ""   # outer-edge marking preset id (must exist in markings.yaml)


@dataclass(frozen=True)
class RoadTypePreset:
    road_type: RoadType
    lane_specs_right: tuple[LaneSpec, ...]   # in id order -1, -2, ...
    lane_specs_left: tuple[LaneSpec, ...]    # in id order +1, +2, ...
    center_marking_preset: str
    design_speed_kmh: float
    default_fillet_radius: float


def load_road_type_presets(
    presets_dir: str | Path | None = None,
) -> dict[RoadType, RoadTypePreset]:
    """Load and parse ``presets/road_types.yaml`` into :class:`RoadTypePreset` objects.

    ``presets_dir`` defaults to :func:`roadup.common.config.resolve_presets_dir`.
    """
    return _load_cached(str(resolve_presets_dir(presets_dir)))


def get_road_type_preset(
    road_type: RoadType,
    presets_dir: str | Path | None = None,
) -> RoadTypePreset:
    presets = load_road_type_presets(presets_dir)
    try:
        return presets[road_type]
    except KeyError:
        raise ValidationError(
            f"no preset for road type {road_type.value!r} (have: "
            f"{sorted(rt.value for rt in presets)})"
        ) from None


@cache
def _load_cached(presets_dir: str) -> dict[RoadType, RoadTypePreset]:
    path = Path(presets_dir) / PRESET_FILE
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise ValidationError(f"cannot read road-type presets at {path}: {exc}") from exc
    presets: dict[RoadType, RoadTypePreset] = {}
    for key, spec in (raw.get("road_types") or {}).items():
        road_type = RoadType(key)
        presets[road_type] = RoadTypePreset(
            road_type=road_type,
            lane_specs_right=_parse_lane_specs(spec.get("lane_specs_right")),
            lane_specs_left=_parse_lane_specs(spec.get("lane_specs_left")),
            center_marking_preset=spec.get("center_marking_preset", ""),
            design_speed_kmh=float(spec.get("design_speed_kmh", 0.0)),
            default_fillet_radius=float(spec.get("default_fillet_radius", 0.0)),
        )
    return presets


def _parse_lane_specs(specs: list | None) -> tuple[LaneSpec, ...]:
    return tuple(
        LaneSpec(
            type=LaneType(s["type"]),
            width=float(s["width"]),
            marking_preset=s.get("marking_preset", ""),
        )
        for s in (specs or [])
    )
