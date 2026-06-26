"""Unit helpers and constants. CODE_REFERENCE.md S1."""
from __future__ import annotations

M_PER_KM = 1000.0
SECONDS_PER_HOUR = 3600.0


def kmh_to_ms(kmh: float) -> float:
    """Kilometres/hour to metres/second."""
    raise NotImplementedError


def deg_to_rad(deg: float) -> float:
    raise NotImplementedError


def grade_percent(rise: float, run: float) -> float:
    """Slope as a percentage: ``rise / run * 100``."""
    raise NotImplementedError
