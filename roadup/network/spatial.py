"""AABB spatial index for nearby/snap queries. CODE_REFERENCE.md S6."""
from __future__ import annotations

from roadup.common.types import Vec3


class SpatialIndex:
    """AABB index over sampled road geometry."""

    def insert(self, road_id: str, bounds: tuple[Vec3, Vec3]) -> None:
        raise NotImplementedError

    def query_radius(self, point: Vec3, radius: float) -> list[str]:
        raise NotImplementedError

    def nearest(self, point: Vec3, k: int = 1) -> list[str]:
        raise NotImplementedError
