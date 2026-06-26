"""Zero-padded, type-prefixed id allocation. CODE_REFERENCE.md S1."""
from __future__ import annotations


def make_id(prefix: str, n: int, width: int = 3) -> str:
    """Zero-padded, type-prefixed id, e.g. ``make_id('road', 1) -> 'road_001'``."""
    raise NotImplementedError


def parse_id(id_: str) -> tuple[str, int]:
    """Inverse of :func:`make_id`, e.g. ``'road_001' -> ('road', 1)``."""
    raise NotImplementedError


class IdAllocator:
    """Monotonic per-prefix id allocation for a session/model."""

    def next(self, prefix: str) -> str:
        raise NotImplementedError

    def reserve(self, id_: str) -> None:
        """Mark an externally-supplied id as used so it is never re-allocated."""
        raise NotImplementedError
