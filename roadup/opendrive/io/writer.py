"""model -> .xodr via scenariogeneration (sole owner of those imports). CODE_REFERENCE.md S4."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from roadup.common.errors import OpenDriveIOError
from roadup.common.ids import parse_id
from roadup.common.types import GeometryType
from roadup.opendrive.io.userdata import USERDATA_NS, encode

if TYPE_CHECKING:
    from roadup.opendrive.model.network import OpenDriveModel
    from roadup.opendrive.model.road import Lane, LaneSection, Road, RoadMark

# RoadUp RoadMark.type strings -> scenariogeneration RoadMarkType member names.
_ROADMARK_TYPE = {
    "solid": "solid",
    "broken": "broken",
    "solid solid": "solid_solid",
    "double_solid": "solid_solid",
    "solid broken": "solid_broken",
    "broken solid": "broken_solid",
    "none": "none",
    "edge": "edge",
}


class ScenarioGenerationWriter:
    """Translate the model into ``scenariogeneration.xodr`` objects and write the file.

    All editing intent that OpenDRIVE cannot express is attached as ``<userData>`` (see
    :mod:`roadup.opendrive.io.userdata`). This is the only module that imports
    ``scenariogeneration``.
    """

    def write(self, model: OpenDriveModel, xodr_path: str) -> None:
        from scenariogeneration import xodr

        major, _, minor = model.header.version.partition(".")
        odr = xodr.OpenDrive(
            model.header.name,
            revMajor=major or "1",
            revMinor=minor or "7",
            geo_reference=model.header.geo_reference,
        )
        for road in model.roads.values():
            sg_road = self._build_road(xodr, road)
            sg_road.planview.adjust_geometries()
            odr.add_road(sg_road)
        try:
            odr.write_xml(xodr_path)
        except Exception as exc:  # scenariogeneration raises plain exceptions
            raise OpenDriveIOError(f"failed to write {xodr_path}: {exc}") from exc

    # --- translation ------------------------------------------------------------------
    def _build_road(self, xodr: Any, road: Road) -> Any:
        planview = self._build_planview(xodr, road)
        lanes = self._build_lanes(xodr, road)
        sg_road = xodr.Road(self._road_int_id(road.id), planview, lanes, name=road.id)
        self._attach_userdata(xodr, sg_road, road.user_data)
        return sg_road

    def _build_planview(self, xodr: Any, road: Road) -> Any:
        if not road.geometry:
            raise OpenDriveIOError(f"road {road.id!r} has no plan-view geometry")
        first = road.geometry[0]
        planview = xodr.PlanView(first.x, first.y, first.hdg)
        for geom in road.geometry:
            planview.add_geometry(self._build_geometry(xodr, geom))
        return planview

    def _build_geometry(self, xodr: Any, geom: Any) -> Any:
        if geom.type == GeometryType.LINE:
            return xodr.Line(geom.length)
        if geom.type == GeometryType.ARC:
            return xodr.Arc(geom.params["curvature"], length=geom.length)
        if geom.type == GeometryType.SPIRAL:
            return xodr.Spiral(
                geom.params["curvStart"], geom.params["curvEnd"], length=geom.length
            )
        if geom.type == GeometryType.PARAM_POLY3:
            p = geom.params
            return xodr.ParamPoly3(
                p["aU"], p["bU"], p["cU"], p["dU"],
                p["aV"], p["bV"], p["cV"], p["dV"],
                length=geom.length,
            )
        raise OpenDriveIOError(
            f"geometry type {geom.type!r} not supported by the writer yet"
        )

    def _build_lanes(self, xodr: Any, road: Road) -> Any:
        lanes = xodr.Lanes()
        for section in road.lane_sections:
            lanes.add_lanesection(self._build_lane_section(xodr, section))
        return lanes

    def _build_lane_section(self, xodr: Any, section: LaneSection) -> Any:
        center_model = section.center
        center = self._build_lane(xodr, center_model) if center_model else xodr.standard_lane()
        sg_section = xodr.LaneSection(section.s, center)
        for lane in section.left:
            sg_section.add_left_lane(self._build_lane(xodr, lane))
        for lane in section.right:
            sg_section.add_right_lane(self._build_lane(xodr, lane))
        return sg_section

    def _build_lane(self, xodr: Any, lane: Lane) -> Any:
        lane_type = getattr(xodr.LaneType, lane.type.value)
        widths = lane.widths
        if widths:
            first = widths[0]
            sg_lane = xodr.Lane(
                lane_type=lane_type,
                a=first.a, b=first.b, c=first.c, d=first.d, soffset=first.s_offset,
            )
            for w in widths[1:]:
                sg_lane.add_lane_width(a=w.a, b=w.b, c=w.c, d=w.d, soffset=w.s_offset)
        else:
            sg_lane = xodr.Lane(lane_type=lane_type)
        for mark in lane.road_marks:
            sg_lane.add_roadmark(self._build_roadmark(xodr, mark))
        self._attach_userdata(xodr, sg_lane, lane.user_data)
        return sg_lane

    def _build_roadmark(self, xodr: Any, mark: RoadMark) -> Any:
        type_name = _ROADMARK_TYPE.get(mark.type, "solid")
        return xodr.RoadMark(
            getattr(xodr.RoadMarkType, type_name),
            width=mark.width,
            length=mark.dash_length,
            space=mark.gap_length,
            soffset=mark.s_offset,
            color=getattr(xodr.RoadMarkColor, mark.color, xodr.RoadMarkColor.standard),
            marking_weight=getattr(
                xodr.RoadMarkWeight, mark.weight, xodr.RoadMarkWeight.standard
            ),
        )

    def _attach_userdata(self, xodr: Any, sg_obj: Any, user_data: dict) -> None:
        if user_data:
            sg_obj.add_userdata(xodr.UserData(USERDATA_NS, encode(user_data)))

    def _road_int_id(self, road_id: str) -> int:
        try:
            return parse_id(road_id)[1]
        except Exception:
            # Accept already-numeric ids too.
            return int(road_id)
