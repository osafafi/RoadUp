"""Road-type preset *schema* + loader. Values live in external YAML, not here. CODE_REFERENCE.md S7.

The editable values are in ``presets/road_types.yaml`` (see ``presets/README.md``); this module only
defines the dataclasses and loads them. Initial values target UAE/GCC and are provisional pending
official validation — see the ``road-design-standards`` skill.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
    raise NotImplementedError


def get_road_type_preset(
    road_type: RoadType,
    presets_dir: str | Path | None = None,
) -> RoadTypePreset:
    raise NotImplementedError
