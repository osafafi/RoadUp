"""Manipulator (control-point) model the UI renders. CODE_REFERENCE.md S11."""
from __future__ import annotations

from dataclasses import dataclass, field

from roadup.common.types import Vec3


@dataclass
class Handle:
    id: str           # control-point id or node id
    position: Vec3
    kind: str         # "node" | "spline_point" | "tangent"
    owner: str        # road_id, or junction_id+connection_id, the handle belongs to


@dataclass
class ManipulatorModel:
    """The set of control points the UI should currently draw."""

    visible: list[Handle] = field(default_factory=list)
    selected: str | None = None
    hovered: str | None = None

    def set_handles(self, handles: list[Handle]) -> None:
        raise NotImplementedError
