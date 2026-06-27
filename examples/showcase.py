"""The author-side 'max variations' golden file — roads **drawn and baked**, not hand-authored.

Each road is built by drawing a :class:`~roadup.geometry.splines.Spline` reference line and baking
it through :class:`~roadup.segments.builder.SegmentBuilder` + the external presets
(``presets/*.yaml``). The set still covers the full variety the writer supports:

* **Geometry primitives:** ``line`` (straight highway), ``arc`` (circular_arc connector),
  ``paramPoly3`` (a baked catmullRom S-curve), and ``spiral`` — the clothoid is **kept explicitly
  authored**, since a transition spiral is not producible by cubic-spline baking (out of scope).
* **Lane variety:** driving / shoulder (highway), biking (bike), sidewalk (pedestrian), left+right,
  plus a width **taper** applied via :meth:`SegmentBuilder.set_lane_width_law`.
* **Marking variety:** solid / broken / double-solid (``yellow_double``), white + yellow.
* **Topology:** the highway's successor is linked to the arc connector (road + lane ``<link>``).
* **Intersections (a stress-test gallery):** five ``<junction>``\\ s of increasing nastiness — a
  classic perpendicular 4-way, a *complex* 4-way (skewed angles, unequal lane counts, mismatched
  lane widths), a 2-road bend, a skewed 3-way, and a 5-road star. Each gets geometry-aware default
  movements + connection splines (line / arc / Bézier). See ``roadup.intersections``.
"""
from __future__ import annotations

import math

from roadup.common.ids import IdAllocator
from roadup.common.types import GeometryType, LaneType, RoadType
from roadup.geometry.splines import ControlPoint, Spline
from roadup.intersections.connectivity import ConnectivitySolver
from roadup.intersections.junction_builder import JunctionBuilder
from roadup.network.linkage import LinkResolver
from roadup.opendrive.model.network import Header, OpenDriveModel
from roadup.opendrive.model.road import Geometry, Lane, LaneSection, Road, RoadMark, WidthRecord
from roadup.segments.builder import SegmentBuilder
from roadup.segments.lane_width import WidthLaw
from roadup.segments.vertical_profile import ElevationLaw, SuperelevationLaw

Vec2 = tuple[float, float]


def _line_spline(start: tuple[float, float, float], end: tuple[float, float, float]) -> Spline:
    return Spline(
        points=[ControlPoint(position=start, id="cp_001"),
                ControlPoint(position=end, id="cp_002")],
        kind="line",
    )


# --- builder-authored roads -----------------------------------------------------------
def _highway() -> Road:
    """Straight highway -> line records, driving + shoulder lanes, a width taper on lane -1."""
    spline = _line_spline((0.0, 0.0, 0.0), (60.0, 0.0, 0.0))
    return (
        SegmentBuilder(RoadType.HIGHWAY)
        .with_reference_line(spline)
        .set_lane_width_law(-1, WidthLaw.taper(0.0, 3.65, 25.0, 4.5))
        .build("road_001")
    )


def _arc_connector() -> Road:
    """Circular-arc continuation off the highway's end -> arc record, lanes {1, -1, -2}."""
    arc = Spline.circular_arc(
        start=(60.0, 0.0, 0.0), start_tangent=(1.0, 0.0, 0.0),
        end=(100.0, 40.0, 0.0), end_tangent=(0.0, 1.0, 0.0),
    )
    return (
        SegmentBuilder(RoadType.ARTERIAL)
        .with_reference_line(arc)
        .with_lane_count(left=1, right=2)
        .build("road_002")
    )


def _freeform_bike() -> Road:
    """A drawn catmullRom S-curve -> paramPoly3 records, biking lanes."""
    spline = Spline(
        points=[
            ControlPoint(position=(0.0, 120.0, 0.0), id="cp_001"),
            ControlPoint(position=(20.0, 128.0, 0.0), id="cp_002"),
            ControlPoint(position=(40.0, 120.0, 0.0), id="cp_003"),
            ControlPoint(position=(60.0, 114.0, 0.0), id="cp_004"),
        ],
        kind="catmullRom",
    )
    return SegmentBuilder(RoadType.BIKE).with_reference_line(spline).build("road_004")


def _pedestrian() -> Road:
    """Straight pedestrian way -> sidewalk lane."""
    spline = _line_spline((0.0, 170.0, 0.0), (50.0, 170.0, 0.0))
    return SegmentBuilder(RoadType.PEDESTRIAN).with_reference_line(spline).build("road_005")


def _elevated_banked_curve() -> Road:
    """A climbing, banked circular curve — the Stage 4.5 vertical + lateral profile showpiece.

    Exercises an ``<elevationProfile>`` (a steady 3% grade) and a ``<lateralProfile>`` (the bank
    ramps up to 6° into the turn) on top of an ``arc`` reference line, so the curvature-adaptive
    sampler densifies the bend while the climb/bank keep it from collapsing. The editing intent
    (both laws) round-trips through ``<userData>``.
    """
    arc = Spline.circular_arc(
        start=(0.0, 250.0, 0.0), start_tangent=(1.0, 0.0, 0.0),
        end=(60.0, 310.0, 0.0), end_tangent=(0.0, 1.0, 0.0),
    )
    length = arc.length()
    return (
        SegmentBuilder(RoadType.ARTERIAL)
        .with_reference_line(arc)
        .with_lane_count(left=1, right=1)
        .with_elevation(ElevationLaw.grade(length=length, slope=0.03))
        .with_superelevation(SuperelevationLaw.ramp(0.0, 0.0, length, math.radians(6.0)))
        .build("road_006")
    )


# --- explicitly-authored clothoid (not producible by cubic-spline baking) -------------
def _spiral() -> Road:
    geom = Geometry(
        s=0.0, x=0.0, y=80.0, hdg=0.0, length=50.0,
        type=GeometryType.SPIRAL, params={"curvStart": 0.0, "curvEnd": 1.0 / 40.0},
    )
    section = LaneSection(
        s=0.0,
        center=Lane(id=0, type=LaneType.NONE,
                    road_marks=[RoadMark(s_offset=0.0, type="broken", color="white",
                                         dash_length=3.0, gap_length=9.0)]),
        right=[
            Lane(id=-1, type=LaneType.DRIVING, widths=[WidthRecord(s_offset=0.0, a=3.5)],
                 road_marks=[RoadMark(s_offset=0.0, type="solid", color="white")]),
            Lane(id=-2, type=LaneType.SHOULDER, widths=[WidthRecord(s_offset=0.0, a=2.5)],
                 road_marks=[RoadMark(s_offset=0.0, type="solid", color="white",
                                      weight="bold", width=0.25)]),
        ],
    )
    return Road(id="road_003", length=geom.length, geometry=[geom], lane_sections=[section],
                user_data={"kind": "referenceLine", "note": "spiral / clothoid transition"})


# --- junctions (drawn-and-built, default connection splines) --------------------------
# An arm spec: (heading degrees from the junction centre, #left lanes, #right lanes,
# {lane_id: width} overrides). Defaults give a plain 3.5 m 2-way arterial arm.
class _Arm:
    def __init__(self, angle_deg: float, left: int = 1, right: int = 1,
                 widths: dict[int, float] | None = None) -> None:
        self.angle_deg = angle_deg
        self.left = left
        self.right = right
        self.widths = widths or {}


def _arm_road(road_id: str, center: Vec2, arm: _Arm, near: float, far: float) -> Road:
    """One incoming road radiating from the junction centre at ``arm.angle_deg``."""
    a = math.radians(arm.angle_deg)
    dx, dy = math.cos(a), math.sin(a)
    cx, cy = center
    spline = _line_spline((cx + dx * near, cy + dy * near, 0.0),
                          (cx + dx * far, cy + dy * far, 0.0))
    builder = (
        SegmentBuilder(RoadType.ARTERIAL)
        .with_lane_count(left=arm.left, right=arm.right)
        .with_reference_line(spline)
    )
    for lane_id, width in arm.widths.items():
        builder.set_lane_width_law(lane_id, WidthLaw.constant(width))
    return builder.build(road_id)


def _add_junction(model: OpenDriveModel, junction_id: str, center: Vec2,
                  arms: list[_Arm], near: float = 11.0, far: float = 56.0) -> None:
    """Author the arm roads + a junction with default connection splines, onto ``model``.

    Arm-road ids are allocated above whatever roads already exist, so junctions stack without
    id collisions (each :class:`JunctionBuilder` then allocates its connecting roads above those).
    """
    alloc = IdAllocator()
    for road_id in model.roads:
        alloc.reserve(road_id)
    arm_ids: list[str] = []
    for arm in arms:
        road_id = alloc.next("road")
        model.add_road(_arm_road(road_id, center, arm, near, far))
        arm_ids.append(road_id)
    movements = ConnectivitySolver(model).movements_at(arm_ids)
    JunctionBuilder(model).build(junction_id, movements)


def showcase_roads() -> list[Road]:
    """The baseline showcase roads in id order (junctions are added in the combined model)."""
    return [_highway(), _arc_connector(), _spiral(), _freeform_bike(), _pedestrian(),
            _elevated_banked_curve()]


def build_showcase_model() -> OpenDriveModel:
    """Assemble the baseline roads + the junction stress-test gallery into one golden-file model."""
    model = OpenDriveModel(header=Header(name="RoadUp Showcase", version="1.7"))
    for road in showcase_roads():
        model.add_road(road)
    # Topology: the highway flows into the arc connector (road + lane links).
    LinkResolver(model).connect_roads("road_001", "end", "road_002", "start")

    # junction_001 — classic perpendicular 4-way (the baseline sanity case).
    _add_junction(model, "junction_001", (200.0, 0.0),
                  [_Arm(0), _Arm(90), _Arm(180), _Arm(270)])

    # junction_002 — COMPLEX: skewed (non-perpendicular) angles, unequal lane counts per arm, and
    # mismatched lane widths (a wide 4.5 m arm meets a narrow 3.0 m arm -> tapered connectors).
    _add_junction(model, "junction_002", (200.0, 200.0), [
        _Arm(5,   left=2, right=2, widths={-1: 4.5, -2: 4.5}),  # wide arm
        _Arm(80,  left=1, right=1),
        _Arm(200, left=1, right=3, widths={-1: 3.0}),           # narrow + extra lanes
        _Arm(290, left=2, right=1),
    ], near=14.0, far=60.0)

    # junction_003 — minimal 2-road junction (a bend).
    _add_junction(model, "junction_003", (380.0, 0.0), [_Arm(0), _Arm(210)])

    # junction_004 — skewed 3-way (Y) with unequal lane counts.
    _add_junction(model, "junction_004", (380.0, 200.0),
                  [_Arm(0, left=1, right=2), _Arm(110), _Arm(235, left=2, right=1)])

    # junction_005 — 5-road star.
    _add_junction(model, "junction_005", (560.0, 0.0),
                  [_Arm(a) for a in (0, 72, 144, 216, 288)])

    return model
