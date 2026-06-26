"""Sample the model into frames and lane boundaries (libOpenDRIVE). CODE_REFERENCE.md S5."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from roadup.common.types import Vec3

if TYPE_CHECKING:
    from roadup.geometry.sampling import Frame
    from roadup.opendrive.model.network import OpenDriveModel


@dataclass
class LaneBoundaries:
    lane_id: int
    inner: list[Vec3] = field(default_factory=list)  # boundary toward the reference line
    outer: list[Vec3] = field(default_factory=list)  # boundary away from the reference line


class Sampler:
    """Wraps libOpenDRIVE evaluation; falls back to :mod:`roadup.geometry` for the pure path."""

    def __init__(self, model: "OpenDriveModel", step: float = 1.0) -> None:
        self._model = model
        self._step = step

    def reference_frames(self, road_id: str) -> list["Frame"]:
        raise NotImplementedError

    def lane_boundaries(self, road_id: str, s0: float, s1: float) -> list[LaneBoundaries]:
        raise NotImplementedError

    def road_surface_polylines(self, road_id: str) -> tuple[list[Vec3], list[Vec3]]:
        """Outermost left/right drivable edges for the surface ribbon."""
        raise NotImplementedError
