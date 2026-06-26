"""Snap queries for road placement. CODE_REFERENCE.md S6."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from roadup.common.types import Vec3

if TYPE_CHECKING:
    from roadup.network.spatial import SpatialIndex


class SnapKind(str, Enum):
    NODE = "node"
    EDGE = "edge"
    GRID = "grid"
    NONE = "none"


@dataclass
class SnapResult:
    kind: SnapKind
    point: Vec3
    road_id: str | None = None
    s: float | None = None


class SnapEngine:
    SNAP_DISTANCE = 5.0  # meters

    def __init__(self, index: "SpatialIndex") -> None:
        self._index = index

    def find_snap(self, point: Vec3) -> SnapResult:
        raise NotImplementedError
