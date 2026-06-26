"""Editable lane width-along-length law, baked to OpenDRIVE <width> records. CODE_REFERENCE.md S7."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from roadup.opendrive.model.road import WidthRecord


@dataclass
class WidthLaw:
    """Width as a function of arc length, authored as control points and baked to cubics."""

    kind: str = "constant"   # "constant" | "linear" | "spline"
    control: list[tuple[float, float]] = field(default_factory=list)  # [(s, width), ...]

    def width_at(self, s: float) -> float:
        raise NotImplementedError

    def bake_records(self) -> list["WidthRecord"]:
        """Produce piecewise-cubic ``<width>`` records covering the lane length."""
        raise NotImplementedError

    @classmethod
    def constant(cls, width: float) -> "WidthLaw":
        raise NotImplementedError

    @classmethod
    def taper(cls, s0: float, w0: float, s1: float, w1: float) -> "WidthLaw":
        raise NotImplementedError
