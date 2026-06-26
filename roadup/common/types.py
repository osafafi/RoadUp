"""Shared type aliases and enums. CODE_REFERENCE.md S1."""
from __future__ import annotations

from enum import Enum

Vec2 = tuple[float, float]
Vec3 = tuple[float, float, float]


class RoadType(str, Enum):
    HIGHWAY = "highway"
    ARTERIAL = "arterial"
    LOCAL = "local"
    PEDESTRIAN = "pedestrian"
    BIKE = "bike"


class LaneType(str, Enum):
    """Subset of OpenDRIVE lane types we author."""

    DRIVING = "driving"
    SIDEWALK = "sidewalk"
    BIKING = "biking"
    PARKING = "parking"
    SHOULDER = "shoulder"
    MEDIAN = "median"
    NONE = "none"


class LaneSide(str, Enum):
    LEFT = "left"      # positive lane ids in OpenDRIVE
    CENTER = "center"  # lane id 0 (reference lane)
    RIGHT = "right"    # negative lane ids


class GeometryType(str, Enum):
    """OpenDRIVE <planView><geometry> record kinds."""

    LINE = "line"
    ARC = "arc"
    SPIRAL = "spiral"
    POLY3 = "poly3"
    PARAM_POLY3 = "paramPoly3"


class TurnType(str, Enum):
    STRAIGHT = "straight"
    LEFT = "left"
    RIGHT = "right"
    U_TURN = "uTurn"
    MERGE = "merge"
