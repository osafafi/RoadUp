"""Unit helpers and constants. CODE_REFERENCE.md S1."""
from __future__ import annotations

import math

M_PER_KM = 1000.0
SECONDS_PER_HOUR = 3600.0


def kmh_to_ms(kmh: float) -> float:
    """Kilometres/hour to metres/second."""
    return kmh * M_PER_KM / SECONDS_PER_HOUR


def deg_to_rad(deg: float) -> float:
    return math.radians(deg)


def grade_percent(rise: float, run: float) -> float:
    """Slope as a percentage: ``rise / run * 100``."""
    if run == 0.0:
        raise ZeroDivisionError("grade_percent: run must be non-zero")
    return rise / run * 100.0
