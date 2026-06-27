""".xodr -> model. libOpenDRIVE adapter + pure-Python fallback. CODE_REFERENCE.md S4.

The pure-Python :class:`LxmlFallbackReader` is the default (CI-safe, no native dependency) and the
inverse of :class:`~roadup.opendrive.io.writer.ScenarioGenerationWriter`: it mirrors that writer's
tag/attribute choices (road id in ``@name``, ``<userData code="roadup" value="{json}">``, broken
road-mark dashes in a child ``<type><line>``). A native libOpenDRIVE backend can slot in behind
:class:`~roadup.opendrive.io.backend.ReaderBackend` without touching callers; it is deferred until
a binding is pinned (see ARCHITECTURE.md, decision 4).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from lxml import etree

from roadup.common.errors import OpenDriveIOError
from roadup.common.ids import make_id
from roadup.common.types import GeometryType, LaneType
from roadup.opendrive.io.userdata import USERDATA_NS, decode
from roadup.opendrive.model.junction import Connection, Junction, LaneLinkPair
from roadup.opendrive.model.network import Header, OpenDriveModel
from roadup.opendrive.model.road import (
    Geometry,
    Lane,
    LaneLink,
    LaneSection,
    Road,
    RoadLink,
    RoadMark,
    WidthRecord,
)

if TYPE_CHECKING:
    from roadup.opendrive.io.backend import ReaderBackend


class LibOpenDriveReader:
    """.xodr -> model using libOpenDRIVE bindings. Owns all libOpenDRIVE imports.

    Deferred: no concrete binding is pinned yet (pure-Python path is the default). See
    ARCHITECTURE.md decision 4.
    """

    def parse(self, xodr_path: str) -> OpenDriveModel:
        raise NotImplementedError


class LxmlFallbackReader:
    """Pure-Python reader (no native dependency) - the default, used in CI/tests."""

    def parse(self, xodr_path: str) -> OpenDriveModel:
        try:
            tree = etree.parse(xodr_path)
        except (OSError, etree.XMLSyntaxError) as exc:
            raise OpenDriveIOError(f"failed to read {xodr_path}: {exc}") from exc
        root = tree.getroot()
        if root.tag != "OpenDRIVE":
            raise OpenDriveIOError(
                f"{xodr_path}: root element is {root.tag!r}, expected 'OpenDRIVE'"
            )

        model = OpenDriveModel(header=self._parse_header(root.find("header")))
        # Connections refer to roads by integer id; remember the mapping back to our string ids.
        int_to_road_id: dict[int, str] = {}
        for road_el in root.findall("road"):
            road = self._parse_road(road_el)
            model.add_road(road)
            int_to_road_id[int(road_el.get("id", "0"))] = road.id
        for junction_el in root.findall("junction"):
            model.add_junction(self._parse_junction(junction_el, int_to_road_id))
        return model

    # --- header -----------------------------------------------------------------------
    def _parse_header(self, el: etree._Element | None) -> Header:
        if el is None:
            return Header()
        major = el.get("revMajor", "1")
        minor = el.get("revMinor", "7")
        geo_el = el.find("geoReference")
        geo = geo_el.text.strip() if geo_el is not None and geo_el.text else None
        return Header(version=f"{major}.{minor}", name=el.get("name", "RoadUp"), geo_reference=geo)

    # --- road -------------------------------------------------------------------------
    def _parse_road(self, el: etree._Element) -> Road:
        road = Road(
            id=self._road_id(el),
            length=float(el.get("length", "0.0")),
            geometry=self._parse_geometry(el),
            lane_sections=self._parse_lane_sections(el),
            link=self._parse_road_link(el.find("link")),
            junction=self._junction_id(el.get("junction", "-1")),
            user_data=self._userdata(el),
        )
        return road

    def _road_id(self, el: etree._Element) -> str:
        name = el.get("name")
        if name:
            return name
        return make_id("road", int(el.get("id", "0")))

    def _junction_id(self, raw: str) -> str | None:
        return None if raw in ("", "-1") else make_id("junction", int(raw))

    def _parse_road_link(self, el: etree._Element | None) -> RoadLink:
        if el is None:
            return RoadLink()
        return RoadLink(
            predecessor=self._parse_link_end(el.find("predecessor")),
            successor=self._parse_link_end(el.find("successor")),
        )

    def _parse_link_end(self, el: etree._Element | None) -> tuple[str, str] | None:
        if el is None:
            return None
        elem_type = el.get("elementType", "road")
        raw_id = el.get("elementId", "0")
        prefix = "junction" if elem_type == "junction" else "road"
        try:
            elem_id = make_id(prefix, int(raw_id))
        except (TypeError, ValueError):
            elem_id = raw_id
        return (elem_type, elem_id)

    # --- junctions --------------------------------------------------------------------
    def _parse_junction(
        self, el: etree._Element, int_to_road_id: dict[int, str]
    ) -> Junction:
        junction = Junction(
            id=make_id("junction", int(el.get("id", "0"))),
            name=el.get("name", ""),
            user_data=self._userdata(el),
        )
        for conn_el in el.findall("connection"):
            junction.connections.append(self._parse_connection(conn_el, int_to_road_id))
        return junction

    def _parse_connection(
        self, el: etree._Element, int_to_road_id: dict[int, str]
    ) -> Connection:
        def road_ref(raw: str | None) -> str:
            return int_to_road_id.get(int(raw), make_id("road", int(raw))) if raw else ""

        return Connection(
            id=make_id("connection", int(el.get("id", "0"))),
            incoming_road=road_ref(el.get("incomingRoad")),
            connecting_road=road_ref(el.get("connectingRoad")),
            contact_point=el.get("contactPoint", "start"),
            lane_links=[
                LaneLinkPair(
                    from_lane=int(ll.get("from", "0")),
                    to_lane=int(ll.get("to", "0")),
                )
                for ll in el.findall("laneLink")
            ],
        )

    # --- geometry ---------------------------------------------------------------------
    def _parse_geometry(self, road_el: etree._Element) -> list[Geometry]:
        records: list[Geometry] = []
        for g in road_el.findall("planView/geometry"):
            child = next((c for c in g if isinstance(c.tag, str)), None)
            if child is None:
                raise OpenDriveIOError("planView/geometry has no shape child element")
            records.append(
                Geometry(
                    s=float(g.get("s", "0.0")),
                    x=float(g.get("x", "0.0")),
                    y=float(g.get("y", "0.0")),
                    hdg=float(g.get("hdg", "0.0")),
                    length=float(g.get("length", "0.0")),
                    type=GeometryType(child.tag),
                    params=self._geometry_params(child),
                )
            )
        return records

    def _geometry_params(self, child: etree._Element) -> dict[str, float]:
        if child.tag == GeometryType.ARC.value:
            return {"curvature": float(child.get("curvature", "0.0"))}
        if child.tag == GeometryType.SPIRAL.value:
            return {
                "curvStart": float(child.get("curvStart", "0.0")),
                "curvEnd": float(child.get("curvEnd", "0.0")),
            }
        if child.tag == GeometryType.PARAM_POLY3.value:
            params = {k: float(child.get(k, "0.0")) for k in
                      ("aU", "bU", "cU", "dU", "aV", "bV", "cV", "dV")}
            if child.get("pRange", "normalized") == "arcLength":
                params["pRangeArcLength"] = 1.0
            return params
        return {}

    # --- lanes ------------------------------------------------------------------------
    def _parse_lane_sections(self, road_el: etree._Element) -> list[LaneSection]:
        sections: list[LaneSection] = []
        for sec_el in road_el.findall("lanes/laneSection"):
            section = LaneSection(s=float(sec_el.get("s", "0.0")))
            left = sec_el.find("left")
            center = sec_el.find("center")
            right = sec_el.find("right")
            if left is not None:
                section.left = [self._parse_lane(ln) for ln in left.findall("lane")]
            if center is not None:
                center_lane = center.find("lane")
                section.center = self._parse_lane(center_lane) if center_lane is not None else None
            if right is not None:
                section.right = [self._parse_lane(ln) for ln in right.findall("lane")]
            sections.append(section)
        return sections

    def _parse_lane(self, el: etree._Element) -> Lane:
        return Lane(
            id=int(el.get("id", "0")),
            type=LaneType(el.get("type", "driving")),
            widths=[self._parse_width(w) for w in el.findall("width")],
            road_marks=[self._parse_roadmark(m) for m in el.findall("roadMark")],
            link=self._parse_lane_link(el.find("link")),
            user_data=self._userdata(el),
        )

    def _parse_width(self, el: etree._Element) -> WidthRecord:
        return WidthRecord(
            s_offset=float(el.get("sOffset", "0.0")),
            a=float(el.get("a", "0.0")),
            b=float(el.get("b", "0.0")),
            c=float(el.get("c", "0.0")),
            d=float(el.get("d", "0.0")),
        )

    def _parse_roadmark(self, el: etree._Element) -> RoadMark:
        dash = gap = None
        line = el.find("type/line")
        if line is not None:
            dash = float(line.get("length", "0.0"))
            gap = float(line.get("space", "0.0"))
        return RoadMark(
            s_offset=float(el.get("sOffset", "0.0")),
            type=el.get("type", "solid"),
            weight=el.get("weight", "standard"),
            color=el.get("color", "white"),
            width=float(el.get("width", "0.15")),
            dash_length=dash,
            gap_length=gap,
        )

    def _parse_lane_link(self, el: etree._Element | None) -> LaneLink:
        if el is None:
            return LaneLink()
        pred = el.find("predecessor")
        succ = el.find("successor")
        return LaneLink(
            predecessor=int(pred.get("id")) if pred is not None and pred.get("id") else None,
            successor=int(succ.get("id")) if succ is not None and succ.get("id") else None,
        )

    # --- userData ---------------------------------------------------------------------
    def _userdata(self, el: etree._Element) -> dict:
        for ud in el.findall("userData"):
            if ud.get("code") == USERDATA_NS:
                return decode(ud.get("value") or "")
        return {}


def default_reader() -> ReaderBackend:
    """Return :class:`LibOpenDriveReader` if a binding imports, else :class:`LxmlFallbackReader`.

    No libOpenDRIVE binding is pinned yet, so this resolves to the pure-Python fallback in practice.
    """
    try:  # pragma: no cover - exercised only once a native binding is pinned
        import libopendrive  # type: ignore  # noqa: F401
    except ImportError:
        return LxmlFallbackReader()
    return LibOpenDriveReader()
