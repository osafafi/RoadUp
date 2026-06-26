"""Expand marking presets into OpenDRIVE road marks + geometry offsets. CODE_REFERENCE.md S8."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from roadup.markings.presets import MarkingPreset
    from roadup.opendrive.model.road import RoadMark


def to_road_mark(preset: "MarkingPreset", s_offset: float = 0.0) -> "RoadMark":
    """Expand a preset into an OpenDRIVE :class:`RoadMark` (preset id retained for user_data)."""
    raise NotImplementedError


def marking_geometry_offsets(preset: "MarkingPreset") -> list[float]:
    """Lateral ``t`` offsets of each painted line relative to the lane edge.

    One value for a single line, two for a double marking.
    """
    raise NotImplementedError
