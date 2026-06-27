"""Lightweight preview geometry for in-progress edits. CODE_REFERENCE.md S11.

A separate, low-res USD layer drawn above committed data while an edit is in flight (e.g. the
reference-line centerline as a curve while dragging). ``pxr`` is imported lazily so the module
imports without USD installed.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from roadup.geometry.splines import ControlPoint, Spline

if TYPE_CHECKING:
    from roadup.opendrive.model.road import Road


class PreviewGenerator:
    """Low-res preview on a separate USD layer above committed data."""

    def __init__(self, step: float = 5.0) -> None:
        self._step = step
        self._stage: Any = None

    def road_preview(self, road: Road) -> Any:  # -> Usd.Stage
        """A throwaway stage with the road's reference-line centerline as a guide curve."""
        from pxr import Gf, Usd, UsdGeom, Vt

        ud = road.user_data
        points = [
            ControlPoint(position=tuple(cp["pos"]), id=cp["id"])
            for cp in ud.get("controlPoints", [])
        ]
        if len(points) < 2:
            return None
        spline = Spline(points=points, kind=ud.get("splineKind", "catmullRom"))
        samples = spline.sample(self._step)

        self._stage = Usd.Stage.CreateInMemory()
        UsdGeom.SetStageMetersPerUnit(self._stage, 1.0)
        UsdGeom.SetStageUpAxis(self._stage, UsdGeom.Tokens.z)
        curve = UsdGeom.BasisCurves.Define(self._stage, "/Preview/Centerline")
        curve.CreateTypeAttr(UsdGeom.Tokens.linear)
        curve.CreateWrapAttr(UsdGeom.Tokens.nonperiodic)
        curve.CreateCurveVertexCountsAttr(Vt.IntArray([len(samples)]))
        curve.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*p) for p in samples]))
        curve.CreatePurposeAttr(UsdGeom.Tokens.guide)
        return self._stage

    def clear(self) -> None:
        self._stage = None
