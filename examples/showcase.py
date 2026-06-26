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
"""
from __future__ import annotations

from roadup.common.types import GeometryType, LaneType, RoadType
from roadup.geometry.splines import ControlPoint, Spline
from roadup.network.linkage import LinkResolver
from roadup.opendrive.model.network import Header, OpenDriveModel
from roadup.opendrive.model.road import Geometry, Lane, LaneSection, Road, RoadMark, WidthRecord
from roadup.segments.builder import SegmentBuilder
from roadup.segments.lane_width import WidthLaw


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


def showcase_roads() -> list[Road]:
    """The showcase roads in id order."""
    return [_highway(), _arc_connector(), _spiral(), _freeform_bike(), _pedestrian()]


def build_showcase_model() -> OpenDriveModel:
    """Assemble all showcase roads into one model (the combined golden file), with a link."""
    model = OpenDriveModel(header=Header(name="RoadUp Showcase", version="1.7"))
    for road in showcase_roads():
        model.add_road(road)
    # Topology: the highway flows into the arc connector (road + lane links).
    LinkResolver(model).connect_roads("road_001", "end", "road_002", "start")
    return model
