"""UI-agnostic interaction controller (the Kit extension drives it). CODE_REFERENCE.md S11.

Headless: no ``omni.*``. The app forwards already-hit-tested input (ids resolved via
``usd.mapping.resolve_prim``) and renders the returned :class:`ManipulatorModel`.

**Edit context (the "enter road editing tool" seam).** ``EDIT_CONTEXTS`` partitions authoring
into ``ROAD`` (edit the OpenDRIVE network -> regenerate the generated USD layer) and ``SCENE``
(author the scene layer that sublayers it). Road handles/manipulators only appear in ``ROAD``.
``SCENE`` is a reserved no-op here — the scatter/array tooling and toggle UI land in Kit (6+).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from roadup.common.errors import ValidationError
from roadup.common.ids import IdAllocator
from roadup.common.types import RoadType, Vec3
from roadup.tooling.commands import CommandStack, CreateRoad, MoveControlPoint
from roadup.tooling.hover import HoverModel
from roadup.tooling.manipulators import ManipulatorModel

if TYPE_CHECKING:
    from roadup.opendrive.model.network import OpenDriveModel
    from roadup.usd.stage import StageGenerator


class RoadToolController:
    """Headless controller. No ``omni.*`` imports - the app binds input/render to this."""

    EDIT_CONTEXTS = ("ROAD", "SCENE")
    TOOL_MODES = ("DRAW_ROAD", "EDIT_SPLINE", "EDIT_INTERSECTION", "EDIT_LANES", "INSPECT")

    def __init__(
        self,
        model: OpenDriveModel,
        stage: StageGenerator | None = None,
        road_type: RoadType = RoadType.LOCAL,
    ) -> None:
        self._model = model
        self._stage = stage
        self._road_type = road_type
        self._context = "ROAD"
        self._mode = "INSPECT"
        self._hover = HoverModel(model)
        self._manip = ManipulatorModel()
        self._commands = CommandStack()
        self._drag_id: str | None = None
        self._drag_owner: str | None = None
        # DRAW_ROAD: reference-line points accumulated until finish_draw().
        self._draft: list[Vec3] = []
        self._ids = IdAllocator()
        for road_id in model.roads:
            self._ids.reserve(road_id)

    # --- context / mode ----------------------------------------------------------------
    @property
    def context(self) -> str:
        return self._context

    @property
    def mode(self) -> str:
        return self._mode

    def set_context(self, context: str) -> None:
        if context not in self.EDIT_CONTEXTS:
            raise ValidationError(f"unknown edit context {context!r}")
        self._context = context
        # Leaving ROAD clears road handles; the app renders nothing road-related in SCENE.
        if context != "ROAD":
            self._manip.set_handles([])

    def set_mode(self, mode: str) -> None:
        if mode not in self.TOOL_MODES:
            raise ValidationError(f"unknown tool mode {mode!r}")
        self._mode = mode

    # --- input (already hit-tested by the app; ids resolved via usd.mapping) -----------
    def on_hover(self, hit: dict | None) -> ManipulatorModel:
        """``hit`` = ``{kind, id, point}`` or ``None``. Returns the manipulator state to render."""
        if self._context != "ROAD" or hit is None:
            self._manip.set_handles(self._hover.on_hover_clear())
            self._manip.hovered = None
            return self._manip
        handles = self._hover.on_hover_element(hit["kind"], hit["id"])
        self._manip.set_handles(handles)
        hit_id = hit.get("id")
        self._manip.hovered = hit_id if hit_id and self._manip.handle(hit_id) else None
        return self._manip

    def on_click(self, hit: dict, modifiers: dict) -> None:
        if self._context != "ROAD":
            return
        hit_id = hit.get("id") if hit else None
        handle = self._manip.handle(hit_id) if hit_id else None
        if handle is not None:
            self._manip.selected = handle.id
            self._hover.set_pinned([handle])
            self._drag_id = handle.id
            self._drag_owner = handle.owner
        else:
            self._manip.selected = None
            self._hover.set_pinned([])
            self._drag_id = None
            self._drag_owner = None

    def on_drag(self, world_point: Vec3, modifiers: dict) -> None:
        """Live-move the selected handle for preview; the edit is committed on release."""
        if self._context != "ROAD" or self._drag_id is None:
            return
        handle = self._manip.handle(self._drag_id)
        if handle is not None:
            handle.position = tuple(world_point)  # type: ignore[assignment]

    def on_release(self, world_point: Vec3, modifiers: dict) -> None:
        """Commit the drag as one undoable :class:`MoveControlPoint`."""
        if self._context != "ROAD" or self._drag_id is None or self._drag_owner is None:
            return
        cmd = MoveControlPoint(
            self._model, self._drag_owner, self._drag_id, world_point, on_change=self._regen
        )
        self._commands.execute(cmd)
        self._drag_id = None
        self._drag_owner = None

    # --- draw (DRAW_ROAD mode) ---------------------------------------------------------
    def add_draft_point(self, world_point: Vec3) -> None:
        """Append a clicked ground point to the in-progress reference line (DRAW_ROAD only)."""
        if self._context != "ROAD" or self._mode != "DRAW_ROAD":
            return
        self._draft.append(tuple(world_point))  # type: ignore[arg-type]

    def draft_points(self) -> list[Vec3]:
        """The in-progress draw points, for the app to render a preview polyline."""
        return list(self._draft)

    def finish_draw(self) -> str | None:
        """Bake the drafted points into a new road (≥2 points) and return its id; else ``None``."""
        if self._context != "ROAD" or self._mode != "DRAW_ROAD" or len(self._draft) < 2:
            self._draft = []
            return None
        road_id = self._ids.next("road")
        cmd = CreateRoad(
            self._model, road_id, self._draft, self._road_type, on_change=self._regen
        )
        self._commands.execute(cmd)
        self._draft = []
        return road_id

    def cancel_draw(self) -> None:
        """Discard the in-progress draw points."""
        self._draft = []

    # --- undo/redo ---------------------------------------------------------------------
    def execute(self, command: Any) -> None:
        """Run a tooling command through the undo stack (panels issue these)."""
        self._commands.execute(command)

    def undo(self) -> None:
        self._commands.undo()

    def redo(self) -> None:
        self._commands.redo()

    # --- render state ------------------------------------------------------------------
    def manipulators(self) -> ManipulatorModel:
        return self._manip

    def preview(self) -> Any:  # -> Usd.Stage | None
        return None

    # --- internals ---------------------------------------------------------------------
    def _regen(self, road_id: str) -> None:
        if self._stage is None:
            return
        # A road that no longer exists (deleted / CreateRoad undone) loses its prims instead.
        if road_id in self._model.roads:
            self._stage.update_road(road_id)
        else:
            self._stage.remove_road(road_id)
