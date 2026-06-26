"""A 'kitchen-sink' OpenDRIVE model exercising the variety the Stage-1 writer supports.

Each road is standalone and offset in +y so they sit side-by-side in a viewer. The set covers:

* **Geometry primitives:** straight ``line``, circular ``arc``, ``spiral`` (clothoid transition),
  and freeform ``paramPoly3`` (an S-curve — the form a baked bezier/freeform spline lowers to).
* **Lane variety:** driving / shoulder / sidewalk / biking lanes, left+right, varying widths and a
  width **taper** (a non-zero ``b`` width coefficient).
* **Marking variety:** solid / broken / double-solid, white + yellow, standard + bold widths.

NOTE (Stage 1): geometry records here are authored directly. Building them by drawing a
``geometry.Spline`` and *baking* it (spline → plan-view records + width laws from presets) arrives
with ``segments.SegmentBuilder`` in Phase 3 — at which point this showcase grows into the full
"max variations" golden file. Spirals/freeform are included now via explicit records.
"""
from __future__ import annotations

from roadup.common.types import GeometryType, LaneType
from roadup.opendrive.model.network import Header, OpenDriveModel
from roadup.opendrive.model.road import (
    Geometry,
    Lane,
    LaneSection,
    Road,
    RoadMark,
    WidthRecord,
)


# --- small builders to keep the road definitions readable -----------------------------
def _mark(
    type: str = "solid",
    color: str = "white",
    weight: str = "standard",
    width: float = 0.15,
    dash_length: float | None = None,
    gap_length: float | None = None,
) -> RoadMark:
    return RoadMark(
        s_offset=0.0,
        type=type,
        color=color,
        weight=weight,
        width=width,
        dash_length=dash_length,
        gap_length=gap_length,
    )


def _broken(color: str = "white", width: float = 0.15) -> RoadMark:
    return _mark("broken", color=color, width=width, dash_length=3.0, gap_length=9.0)


def _lane(
    lane_id: int,
    lane_type: LaneType,
    widths: list[WidthRecord],
    mark: RoadMark | None = None,
    preset: str = "",
) -> Lane:
    return Lane(
        id=lane_id,
        type=lane_type,
        widths=widths,
        road_marks=[mark] if mark else [],
        user_data={"kind": "lane", "markingPreset": preset} if preset else {},
    )


def _w(a: float, b: float = 0.0) -> list[WidthRecord]:
    return [WidthRecord(s_offset=0.0, a=a, b=b)]


def _road(road_id: str, geom: Geometry, section: LaneSection, note: str) -> Road:
    return Road(
        id=road_id,
        length=geom.length,
        geometry=[geom],
        lane_sections=[section],
        user_data={"kind": "referenceLine", "note": note},
    )


# --- the showcase roads ---------------------------------------------------------------
def _straight() -> Road:
    geom = Geometry(s=0.0, x=0.0, y=0.0, hdg=0.0, length=60.0, type=GeometryType.LINE)
    section = LaneSection(
        s=0.0,
        center=_lane(0, LaneType.NONE, [], _broken("white", 0.15)),
        right=[
            _lane(-1, LaneType.DRIVING, _w(3.5), _broken("white"), "white_dashed"),
            _lane(-2, LaneType.DRIVING, _w(3.5), _mark("solid", "white"), "white_solid"),
        ],
    )
    return _road("road_001", geom, section, "straight / line")


def _arc() -> Road:
    geom = Geometry(
        s=0.0, x=0.0, y=30.0, hdg=0.0, length=62.0,
        type=GeometryType.ARC, params={"curvature": 1.0 / 80.0},  # gentle left turn
    )
    section = LaneSection(
        s=0.0,
        center=_lane(0, LaneType.NONE, [], _mark("solid solid", "yellow", width=0.2)),
        left=[_lane(1, LaneType.DRIVING, _w(3.5), _mark("solid", "white"), "white_solid")],
        right=[
            _lane(-1, LaneType.DRIVING, _w(3.5), _broken("white"), "white_dashed"),
            _lane(-2, LaneType.DRIVING, _w(3.5), _mark("solid", "white"), "white_solid"),
        ],
    )
    return _road("road_002", geom, section, "circular arc")


def _spiral() -> Road:
    geom = Geometry(
        s=0.0, x=0.0, y=80.0, hdg=0.0, length=50.0,
        type=GeometryType.SPIRAL, params={"curvStart": 0.0, "curvEnd": 1.0 / 40.0},
    )
    section = LaneSection(
        s=0.0,
        center=_lane(0, LaneType.NONE, [], _broken("white")),
        right=[
            _lane(-1, LaneType.DRIVING, _w(3.5), _mark("solid", "white"), "white_solid"),
            _lane(-2, LaneType.SHOULDER, _w(2.5), _mark("solid", "white", "bold", 0.25)),
        ],
    )
    return _road("road_003", geom, section, "spiral / clothoid transition")


def _freeform() -> Road:
    # paramPoly3 S-curve: u(p) = length*p ; v(p) = h*(3p^2 - 2p^3) (smooth lateral shift).
    h = 8.0
    length = 60.0
    geom = Geometry(
        s=0.0, x=0.0, y=120.0, hdg=0.0, length=length,
        type=GeometryType.PARAM_POLY3,
        params={
            "aU": 0.0, "bU": length, "cU": 0.0, "dU": 0.0,
            "aV": 0.0, "bV": 0.0, "cV": 3.0 * h, "dV": -2.0 * h,
        },
    )
    section = LaneSection(
        s=0.0,
        center=_lane(0, LaneType.NONE, [], _broken("yellow")),
        left=[
            _lane(1, LaneType.DRIVING, _w(3.5), _mark("solid", "white"), "white_solid"),
            _lane(2, LaneType.SIDEWALK, _w(2.0), _mark("solid", "white", "bold", 0.25)),
        ],
        right=[
            _lane(-1, LaneType.DRIVING, _w(3.5), _broken("white"), "white_dashed"),
            _lane(-2, LaneType.BIKING, _w(1.5), _mark("solid", "white"), "white_solid"),
            _lane(-3, LaneType.SIDEWALK, _w(2.0), _mark("solid", "white", "bold", 0.25)),
        ],
    )
    return _road("road_004", geom, section, "freeform / paramPoly3 S-curve")


def _tapered() -> Road:
    # Straight road whose right lane widens along its length (width law with non-zero b),
    # plus a piecewise second width record — exercises lane-width variation.
    geom = Geometry(s=0.0, x=0.0, y=170.0, hdg=0.0, length=50.0, type=GeometryType.LINE)
    widening = [
        WidthRecord(s_offset=0.0, a=3.0, b=0.04),    # 3.0 m widening at 4 cm/m
        WidthRecord(s_offset=25.0, a=4.0, b=0.0),     # then constant 4.0 m
    ]
    section = LaneSection(
        s=0.0,
        center=_lane(0, LaneType.NONE, [], _mark("solid solid", "yellow", width=0.2)),
        right=[
            _lane(-1, LaneType.DRIVING, widening, _broken("white"), "white_dashed"),
            _lane(-2, LaneType.DRIVING, _w(3.5), _mark("solid", "white"), "white_solid"),
            _lane(-3, LaneType.PARKING, _w(2.5), _mark("broken", "white")),
        ],
    )
    return _road("road_005", geom, section, "lane width taper / piecewise width")


def showcase_roads() -> list[Road]:
    """The showcase roads in id order."""
    return [_straight(), _arc(), _spiral(), _freeform(), _tapered()]


def build_showcase_model() -> OpenDriveModel:
    """Assemble all showcase roads into one model (the combined golden file)."""
    model = OpenDriveModel(header=Header(name="RoadUp Showcase", version="1.7"))
    for road in showcase_roads():
        model.add_road(road)
    return model
