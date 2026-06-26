"""Expand marking presets into OpenDRIVE road marks + geometry offsets. CODE_REFERENCE.md S8."""
from __future__ import annotations

from typing import TYPE_CHECKING

from roadup.opendrive.model.road import RoadMark

if TYPE_CHECKING:
    from roadup.markings.presets import MarkingPreset

#: Marking-preset ``pattern`` -> OpenDRIVE ``<roadMark>`` ``type`` string. The space-separated
#: forms ("solid solid", ...) match what the writer emits and the reader parses (see the writer's
#: ``_ROADMARK_TYPE`` map), so a preset round-trips losslessly.
_PATTERN_TO_TYPE = {
    "solid": "solid",
    "broken": "broken",
    "double_solid": "solid solid",
    "solid_broken": "solid broken",
    "broken_solid": "broken solid",
}

_BROKEN_PATTERNS = {"broken", "solid_broken", "broken_solid"}


def to_road_mark(preset: MarkingPreset, s_offset: float = 0.0) -> RoadMark:
    """Expand a preset into an OpenDRIVE :class:`RoadMark` (preset id retained for user_data)."""
    mark_type = _PATTERN_TO_TYPE.get(preset.pattern, "solid")
    has_dashes = preset.pattern in _BROKEN_PATTERNS
    return RoadMark(
        s_offset=s_offset,
        type=mark_type,
        color=preset.color,
        width=preset.line_width,
        dash_length=preset.dash_length if has_dashes else None,
        gap_length=preset.gap_length if has_dashes else None,
        preset_id=preset.id,
    )


def marking_geometry_offsets(preset: MarkingPreset) -> list[float]:
    """Lateral ``t`` offsets of each painted line relative to the lane edge.

    One value for a single line, two (symmetric about the edge) for a double marking.
    """
    if preset.pattern.startswith("double") or preset.separation > 0.0:
        half = preset.separation / 2.0
        return [-half, half]
    return [0.0]
