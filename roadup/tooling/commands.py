"""Undoable commands; each mutates the model then triggers scoped regen. CODE_REFERENCE.md S11.

Each concrete command edits the OpenDRIVE model (the source of truth) and, on ``do``/``undo``,
invokes an optional ``on_change(road_id)`` so the controller can regenerate only the affected
road's USD prims. Headless — no ``omni.*``.
"""
from __future__ import annotations

import copy
from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

from roadup.common.errors import ValidationError
from roadup.common.ids import make_id
from roadup.geometry.splines import ControlPoint, Spline
from roadup.markings.presets import get_preset
from roadup.markings.roadmark import to_road_mark
from roadup.segments.builder import SegmentBuilder, bake_reference_line

if TYPE_CHECKING:
    from roadup.common.types import RoadType, Vec3
    from roadup.opendrive.model.network import OpenDriveModel
    from roadup.opendrive.model.road import RoadLink
    from roadup.segments.lane_width import WidthLaw

OnChange = Callable[[str], None] | None


class Command(Protocol):
    def do(self) -> None: ...
    def undo(self) -> None: ...


class CommandStack:
    """Linear undo/redo stack."""

    def __init__(self) -> None:
        self._undo: list[Command] = []
        self._redo: list[Command] = []

    def execute(self, cmd: Command) -> None:
        cmd.do()
        self._undo.append(cmd)
        self._redo.clear()

    def undo(self) -> None:
        if not self._undo:
            return
        cmd = self._undo.pop()
        cmd.undo()
        self._redo.append(cmd)

    def redo(self) -> None:
        if not self._redo:
            return
        cmd = self._redo.pop()
        cmd.do()
        self._undo.append(cmd)

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)


# --- shared helpers -------------------------------------------------------------------
def _rebake_road(road) -> None:
    """Re-bake a road's plan-view geometry from its ``<userData>`` reference-line control points."""
    ud = road.user_data
    kind = ud.get("splineKind", "catmullRom")
    if kind == "arc":
        raise ValidationError("cannot rebake an arc reference line from control points")
    points = [ControlPoint(position=tuple(cp["pos"]), id=cp["id"]) for cp in ud["controlPoints"]]
    spline = Spline(points=points, kind=kind)
    road.geometry = bake_reference_line(spline)
    road.length = sum(g.length for g in road.geometry)


def _notify(on_change: OnChange, road_id: str) -> None:
    if on_change is not None:
        on_change(road_id)


# --- concrete commands ----------------------------------------------------------------
class CreateRoad:
    """Author a brand-new road from drawn reference-line points + a road-type preset.

    The points are the world positions clicked in the viewport (DRAW_ROAD mode). They become a
    ``catmullRom`` reference-line :class:`Spline`; :class:`SegmentBuilder` bakes plan-view geometry,
    lanes, width records and road marks from the preset. ``undo`` removes the road again.
    """

    def __init__(
        self,
        model: OpenDriveModel,
        road_id: str,
        points: list[Vec3],
        road_type: RoadType,
        on_change: OnChange = None,
    ) -> None:
        if len(points) < 2:
            raise ValidationError("a road needs at least two reference-line points")
        self._model = model
        self._road_id = road_id
        self._points: list[Vec3] = [(float(p[0]), float(p[1]), float(p[2])) for p in points]
        self._road_type = road_type
        self._on_change = on_change

    def do(self) -> None:
        control = [
            ControlPoint(position=p, id=make_id("cp", i + 1))
            for i, p in enumerate(self._points)
        ]
        spline = Spline(points=control, kind="catmullRom")
        road = SegmentBuilder(self._road_type).with_reference_line(spline).build(self._road_id)
        self._model.add_road(road)
        _notify(self._on_change, self._road_id)

    def undo(self) -> None:
        self._model.remove_road(self._road_id)
        _notify(self._on_change, self._road_id)


class MoveControlPoint:
    """Move one reference-line control point and re-bake the road geometry."""

    def __init__(
        self,
        model: OpenDriveModel,
        road_id: str,
        cp_id: str,
        new_pos: Vec3,
        on_change: OnChange = None,
    ) -> None:
        self._model = model
        self._road_id = road_id
        self._cp_id = cp_id
        self._new = tuple(new_pos)
        self._old: tuple | None = None
        self._on_change = on_change

    def _set(self, pos: tuple) -> None:
        road = self._model.get_road(self._road_id)
        for cp in road.user_data["controlPoints"]:
            if cp["id"] == self._cp_id:
                cp["pos"] = list(pos)
                break
        else:
            raise ValidationError(f"no control point {self._cp_id!r} on road {self._road_id!r}")
        _rebake_road(road)
        _notify(self._on_change, self._road_id)

    def do(self) -> None:
        road = self._model.get_road(self._road_id)
        for cp in road.user_data["controlPoints"]:
            if cp["id"] == self._cp_id:
                self._old = tuple(cp["pos"])
                break
        self._set(self._new)

    def undo(self) -> None:
        if self._old is not None:
            self._set(self._old)


class AddControlPoint:
    """Insert a control point into the reference line at parameter ``t`` and re-bake."""

    def __init__(
        self,
        model: OpenDriveModel,
        road_id: str,
        t: float,
        on_change: OnChange = None,
    ) -> None:
        self._model = model
        self._road_id = road_id
        self._t = t
        self._added_id: str | None = None
        self._on_change = on_change

    def _spline(self):
        road = self._model.get_road(self._road_id)
        ud = road.user_data
        points = [
            ControlPoint(position=tuple(cp["pos"]), id=cp["id"]) for cp in ud["controlPoints"]
        ]
        return road, Spline(points=points, kind=ud.get("splineKind", "catmullRom"))

    def do(self) -> None:
        road, spline = self._spline()
        cp = spline.insert_control_point(self._t)
        self._added_id = cp.id
        road.user_data["controlPoints"] = [
            {"id": p.id, "pos": list(p.position)} for p in spline.points
        ]
        _rebake_road(road)
        _notify(self._on_change, self._road_id)

    def undo(self) -> None:
        road = self._model.get_road(self._road_id)
        road.user_data["controlPoints"] = [
            cp for cp in road.user_data["controlPoints"] if cp["id"] != self._added_id
        ]
        _rebake_road(road)
        _notify(self._on_change, self._road_id)


class SetLaneMarking:
    """Change a lane's marking preset (updates ``road_marks`` + ``<userData>``)."""

    def __init__(
        self,
        model: OpenDriveModel,
        road_id: str,
        lane_id: int,
        preset_id: str,
        on_change: OnChange = None,
    ) -> None:
        self._model = model
        self._road_id = road_id
        self._lane_id = lane_id
        self._preset_id = preset_id
        self._old_marks: list | None = None
        self._old_preset: str | None = None
        self._on_change = on_change

    def _lane(self):
        road = self._model.get_road(self._road_id)
        return road.lane_section_at(0.0).lane(self._lane_id)

    def _apply(self, preset_id: str) -> None:
        lane = self._lane()
        lane.user_data["markingPreset"] = preset_id
        lane.road_marks = [to_road_mark(get_preset(preset_id))] if preset_id else []
        _notify(self._on_change, self._road_id)

    def do(self) -> None:
        lane = self._lane()
        self._old_marks = list(lane.road_marks)
        self._old_preset = lane.user_data.get("markingPreset", "")
        self._apply(self._preset_id)

    def undo(self) -> None:
        lane = self._lane()
        lane.road_marks = list(self._old_marks or [])
        lane.user_data["markingPreset"] = self._old_preset or ""
        _notify(self._on_change, self._road_id)


class SetLaneWidthLaw:
    """Replace a lane's width law (re-bakes ``<width>`` records + ``<userData>``)."""

    def __init__(
        self,
        model: OpenDriveModel,
        road_id: str,
        lane_id: int,
        law: WidthLaw,
        on_change: OnChange = None,
    ) -> None:
        self._model = model
        self._road_id = road_id
        self._lane_id = lane_id
        self._law = law
        self._old_widths: list | None = None
        self._old_ud: dict | None = None
        self._on_change = on_change

    def _lane(self):
        road = self._model.get_road(self._road_id)
        return road.lane_section_at(0.0).lane(self._lane_id)

    def do(self) -> None:
        lane = self._lane()
        self._old_widths = list(lane.widths)
        self._old_ud = lane.user_data.get("widthLaw")
        lane.widths = self._law.bake_records()
        lane.user_data["widthLaw"] = {
            "kind": self._law.kind,
            "control": [list(c) for c in self._law.control],
        }
        _notify(self._on_change, self._road_id)

    def undo(self) -> None:
        lane = self._lane()
        lane.widths = list(self._old_widths or [])
        if self._old_ud is None:
            lane.user_data.pop("widthLaw", None)
        else:
            lane.user_data["widthLaw"] = self._old_ud
        _notify(self._on_change, self._road_id)


class SetLaneCount:
    """Set the lane count on one side of the first section (repeats the outermost lane)."""

    def __init__(
        self,
        model: OpenDriveModel,
        road_id: str,
        side: str,
        count: int,
        on_change: OnChange = None,
    ) -> None:
        if side not in ("left", "right"):
            raise ValidationError(f"side must be 'left' or 'right', got {side!r}")
        if count < 0:
            raise ValidationError("lane count cannot be negative")
        self._model = model
        self._road_id = road_id
        self._side = side
        self._count = count
        self._old: list | None = None
        self._on_change = on_change

    def _section(self):
        return self._model.get_road(self._road_id).lane_section_at(0.0)

    def do(self) -> None:
        section = self._section()
        lanes = section.left if self._side == "left" else section.right
        self._old = list(lanes)
        sign = 1 if self._side == "left" else -1
        new = list(lanes[: self._count])
        while len(new) < self._count:
            if not new and not lanes:
                raise ValidationError("cannot grow lane count with no template lane")
            template = new[-1] if new else lanes[-1]
            new.append(copy.deepcopy(template))
        for i, lane in enumerate(new):
            lane.id = sign * (i + 1)
        if self._side == "left":
            section.left = new
        else:
            section.right = new
        _notify(self._on_change, self._road_id)

    def undo(self) -> None:
        section = self._section()
        if self._side == "left":
            section.left = list(self._old or [])
        else:
            section.right = list(self._old or [])
        _notify(self._on_change, self._road_id)


class ConnectSegments:
    """Link two roads end-to-end (road + lane ``<link>``) via the network LinkResolver."""

    def __init__(
        self,
        model: OpenDriveModel,
        road_a: str,
        contact_a: str,
        road_b: str,
        contact_b: str,
        on_change: OnChange = None,
    ) -> None:
        self._model = model
        self._road_a = road_a
        self._contact_a = contact_a
        self._road_b = road_b
        self._contact_b = contact_b
        self._old_a: RoadLink | None = None
        self._old_b: RoadLink | None = None
        self._on_change = on_change

    def do(self) -> None:
        from roadup.network.linkage import LinkResolver

        a = self._model.get_road(self._road_a)
        b = self._model.get_road(self._road_b)
        self._old_a = copy.deepcopy(a.link)
        self._old_b = copy.deepcopy(b.link)
        LinkResolver(self._model).connect_roads(
            self._road_a, self._contact_a, self._road_b, self._contact_b
        )
        _notify(self._on_change, self._road_a)
        _notify(self._on_change, self._road_b)

    def undo(self) -> None:
        if self._old_a is not None:
            self._model.get_road(self._road_a).link = self._old_a
        if self._old_b is not None:
            self._model.get_road(self._road_b).link = self._old_b
        _notify(self._on_change, self._road_a)
        _notify(self._on_change, self._road_b)
