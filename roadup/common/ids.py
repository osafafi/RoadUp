"""Zero-padded, type-prefixed id allocation. CODE_REFERENCE.md S1."""
from __future__ import annotations

from roadup.common.errors import ValidationError


def make_id(prefix: str, n: int, width: int = 3) -> str:
    """Zero-padded, type-prefixed id, e.g. ``make_id('road', 1) -> 'road_001'``.

    Negative ``n`` (used for OpenDRIVE right-side lane ids) keeps the sign outside the
    zero padding: ``make_id('lane', -2) -> 'lane_-002'``.
    """
    if not prefix:
        raise ValidationError("id prefix must be non-empty")
    if "_" in prefix:
        raise ValidationError(f"id prefix must not contain '_': {prefix!r}")
    sign = "-" if n < 0 else ""
    return f"{prefix}_{sign}{abs(n):0{width}d}"


def parse_id(id_: str) -> tuple[str, int]:
    """Inverse of :func:`make_id`, e.g. ``'road_001' -> ('road', 1)``."""
    prefix, sep, num = id_.rpartition("_")
    if not sep or not prefix:
        raise ValidationError(f"malformed id (expected 'prefix_NNN'): {id_!r}")
    try:
        return prefix, int(num)
    except ValueError as exc:
        raise ValidationError(f"malformed id (numeric part): {id_!r}") from exc


class IdAllocator:
    """Monotonic per-prefix id allocation for a session/model."""

    def __init__(self) -> None:
        # Highest integer handed out (or reserved) per prefix.
        self._counters: dict[str, int] = {}

    def next(self, prefix: str) -> str:
        n = self._counters.get(prefix, 0) + 1
        self._counters[prefix] = n
        return make_id(prefix, n)

    def reserve(self, id_: str) -> None:
        """Mark an externally-supplied id as used so it is never re-allocated."""
        prefix, n = parse_id(id_)
        current = self._counters.get(prefix)
        if current is None or n > current:
            self._counters[prefix] = n
