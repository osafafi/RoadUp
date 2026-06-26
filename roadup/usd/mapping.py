"""Prim <-> OpenDRIVE id mapping for viewport picking/hover. CODE_REFERENCE.md S10."""
from __future__ import annotations

from typing import Any

# Custom USD attribute names tagging generated prims with their OpenDRIVE source ids.
ATTR_ROAD_ID = "roadup:roadId"
ATTR_LANE_ID = "roadup:laneId"
ATTR_JUNCTION_ID = "roadup:junctionId"
ATTR_CONTROL_POINT_ID = "roadup:controlPointId"

ROOT_SCOPE = "/RoadNetwork"


def road_prim_path(road_id: str) -> str:
    """e.g. ``road_001`` -> ``/RoadNetwork/Roads/Road_001``."""
    raise NotImplementedError


def junction_prim_path(junction_id: str) -> str:
    raise NotImplementedError


def resolve_prim(prim: Any) -> dict:
    """Read the ``roadup:*`` tags off a hit prim -> ``{kind, id}`` for the tooling layer."""
    raise NotImplementedError
