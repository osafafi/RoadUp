"""Prim <-> OpenDRIVE id mapping for viewport picking/hover. CODE_REFERENCE.md S10.

Pure-Python: these are path/string helpers and a tag reader. No ``pxr`` import here so the
mapping stays testable without USD installed (the rest of ``usd/`` imports ``pxr`` lazily).

Prim paths are **derived from ids and stable** — they are the cross-layer contract a scene
layer references (a ``*.scene.usda`` that sublayers the generated layer relies on these paths
surviving regeneration). See ARCHITECTURE.md S9 (scene coexistence).
"""
from __future__ import annotations

from typing import Any

# Custom USD attribute names tagging generated prims with their OpenDRIVE source ids.
ATTR_ROAD_ID = "roadup:roadId"
ATTR_LANE_ID = "roadup:laneId"
ATTR_JUNCTION_ID = "roadup:junctionId"
ATTR_CONTROL_POINT_ID = "roadup:controlPointId"

ROOT_SCOPE = "/RoadNetwork"
ROADS_SCOPE = ROOT_SCOPE + "/Roads"
JUNCTIONS_SCOPE = ROOT_SCOPE + "/Junctions"
MATERIALS_SCOPE = ROOT_SCOPE + "/Materials"


def _pascal_id(id_: str) -> str:
    """``road_001`` -> ``Road_001`` (capitalise the type prefix, keep the padded number)."""
    prefix, sep, num = id_.partition("_")
    if not sep:
        return id_[:1].upper() + id_[1:]
    return f"{prefix[:1].upper()}{prefix[1:]}_{num}"


def lane_token(lane_id: int) -> str:
    """A valid prim-name token for a signed lane id (``-1`` -> ``LaneN1``; ``2`` -> ``LaneP2``).

    ``N``/``P`` encode the OpenDRIVE sign (negative = right side, positive = left) since USD prim
    names cannot contain ``-``.
    """
    sign = "N" if lane_id < 0 else "P"
    return f"Lane{sign}{abs(lane_id)}"


def road_prim_path(road_id: str) -> str:
    """e.g. ``road_001`` -> ``/RoadNetwork/Roads/Road_001``."""
    return f"{ROADS_SCOPE}/{_pascal_id(road_id)}"


def junction_prim_path(junction_id: str) -> str:
    """e.g. ``junction_001`` -> ``/RoadNetwork/Junctions/Junction_001``."""
    return f"{JUNCTIONS_SCOPE}/{_pascal_id(junction_id)}"


def road_surface_path(road_id: str) -> str:
    return f"{road_prim_path(road_id)}/Surface"


def junction_surface_path(junction_id: str) -> str:
    return f"{junction_prim_path(junction_id)}/Surface"


def lane_marking_prim_path(road_id: str, lane_id: int, index: int = 0) -> str:
    """Marking strip prim for ``lane_id`` of ``road_id`` (``index`` disambiguates stacked marks)."""
    base = f"{road_prim_path(road_id)}/Markings/{lane_token(lane_id)}"
    return base if index == 0 else f"{base}_{index}"


def rails_scope_path(road_id: str) -> str:
    return f"{road_prim_path(road_id)}/Rails"


def centerline_rail_path(road_id: str) -> str:
    """Guide curve along the reference line — scene scatter/array rides this."""
    return f"{rails_scope_path(road_id)}/Centerline"


def lane_rail_path(road_id: str, lane_id: int) -> str:
    """Guide curve along a lane's outer edge (per-lane scatter rail)."""
    return f"{rails_scope_path(road_id)}/{lane_token(lane_id)}_Edge"


def _read_attr(prim: Any, name: str) -> Any:
    """Read a custom attribute off a prim, tolerating absent/invalid attributes.

    Works on a real ``pxr`` ``Usd.Prim`` and on any duck-typed stand-in exposing
    ``GetAttribute(name)`` -> attribute with ``IsValid()``/``Get()``.
    """
    getter = getattr(prim, "GetAttribute", None)
    if getter is None:
        return None
    attr = getter(name)
    if attr is None:
        return None
    is_valid = getattr(attr, "IsValid", None)
    if is_valid is not None and not is_valid():
        return None
    return attr.Get()


def resolve_prim(prim: Any) -> dict:
    """Read the ``roadup:*`` tags off a hit prim -> ``{kind, id, ...}`` for the tooling layer.

    ``kind`` is one of ``junction`` | ``lane`` | ``road``; ``id`` is the owning road/junction id.
    A lane hit also carries ``lane_id``; a handle hit carries ``control_point_id``.
    """
    junction_id = _read_attr(prim, ATTR_JUNCTION_ID)
    if junction_id is not None:
        return {"kind": "junction", "id": junction_id}

    road_id = _read_attr(prim, ATTR_ROAD_ID)
    lane_id = _read_attr(prim, ATTR_LANE_ID)
    control_point_id = _read_attr(prim, ATTR_CONTROL_POINT_ID)
    if road_id is None:
        return {"kind": "unknown", "id": None}

    result: dict = {"kind": "road", "id": road_id}
    if lane_id is not None:
        result["kind"] = "lane"
        result["lane_id"] = int(lane_id)
    if control_point_id is not None:
        result["control_point_id"] = control_point_id
    return result
