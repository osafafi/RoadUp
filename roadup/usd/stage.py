"""Generate/update the USD viewport stage from the model. Owns pxr imports. CODE_REFERENCE.md S10.

The stage this builds is the **generated layer**: derived from the OpenDRIVE model, regenerated
(never hand-edited), with **stable id-keyed prim paths**. A scene layer (``*.scene.usda``)
sublayers it and authors everything OpenDRIVE cannot hold (scatter, props, env). The road/lane
**Rails** (``UsdGeom.BasisCurves``, ``purpose=guide``) are the rails that scene scatter/array tools
ride. See ARCHITECTURE.md S9 (scene coexistence) and the two-source model.

``pxr`` is imported lazily inside methods so the module imports without USD installed.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from roadup.geometry.mesh import MeshBuilder
from roadup.intersections.surface import IntersectionSurface
from roadup.markings.presets import MaterialParams, get_preset
from roadup.usd import mapping
from roadup.usd.materials import MaterialLibrary

if TYPE_CHECKING:
    from roadup.geometry.mesh import MeshData
    from roadup.opendrive.eval.sampler import Sampler
    from roadup.opendrive.model.network import OpenDriveModel
    from roadup.opendrive.model.road import LaneSection, Road


class StageGenerator:
    """Build/update the stage from model + sampler. Updates are incremental per road/junction."""

    def __init__(self, model: OpenDriveModel, sampler: Sampler, stage: Any = None) -> None:
        self._model = model
        self._sampler = sampler
        self._stage = stage
        self._materials: MaterialLibrary | None = None
        self._mesh = MeshBuilder()

    # --- stage lifecycle ---------------------------------------------------------------
    def _ensure_stage(self) -> Any:
        from pxr import Usd, UsdGeom

        if self._stage is None:
            self._stage = Usd.Stage.CreateInMemory()
        if self._materials is None:
            self._materials = MaterialLibrary(self._stage)
        UsdGeom.SetStageMetersPerUnit(self._stage, 1.0)
        UsdGeom.SetStageUpAxis(self._stage, UsdGeom.Tokens.z)
        return self._stage

    def build_all(self) -> Any:  # -> Usd.Stage
        from pxr import UsdGeom

        stage = self._ensure_stage()
        UsdGeom.Scope.Define(stage, mapping.ROOT_SCOPE)
        UsdGeom.Scope.Define(stage, mapping.ROADS_SCOPE)
        UsdGeom.Scope.Define(stage, mapping.JUNCTIONS_SCOPE)
        stage.SetDefaultPrim(stage.GetPrimAtPath(mapping.ROOT_SCOPE))
        for road_id in self._model.roads:
            self.update_road(road_id)
        for junction_id in self._model.junctions:
            self.update_junction(junction_id)
        return stage

    def export(self, path: str) -> None:
        """Write the generated layer to ``path`` (a file a scene layer can sublayer)."""
        if self._stage is None:
            raise RuntimeError("build_all() must run before export()")
        self._stage.GetRootLayer().Export(path)

    def to_usda(self) -> str:
        """The generated layer as a ``.usda`` string (for auditing/showing)."""
        if self._stage is None:
            raise RuntimeError("build_all() must run before to_usda()")
        return self._stage.GetRootLayer().ExportToString()

    # --- incremental regeneration ------------------------------------------------------
    def update_road(self, road_id: str) -> None:
        """Regenerate this road's prims (surface, marking strips, rails), preserving paths/ids."""
        from pxr import Sdf, UsdGeom

        stage = self._ensure_stage()
        assert self._materials is not None
        road = self._model.get_road(road_id)
        road_path = mapping.road_prim_path(road_id)
        # Non-destructive at the path level: drop the old subtree, rebuild under the same path.
        stage.RemovePrim(Sdf.Path(road_path))
        road_prim = UsdGeom.Xform.Define(stage, road_path).GetPrim()
        road_prim.CreateAttribute(mapping.ATTR_ROAD_ID, Sdf.ValueTypeNames.String).Set(road_id)

        # Road surface ribbon (outermost drivable edges).
        left, right = self._sampler.road_surface_polylines(road_id)
        if len(left) >= 2 and len(right) >= 2:
            surface = self._mesh.ribbon(left, right)
            mesh = self._write_mesh(mapping.road_surface_path(road_id), surface)
            self._tag(mesh.GetPrim(), road_id=road_id)
            self._bind(mesh, self._materials.asphalt())

        section = road.lane_section_at(0.0)
        s0, s1 = self._section_bounds(road, section)
        boundaries = {b.lane_id: b for b in self._sampler.lane_boundaries(road_id, s0, s1)}

        # Marking strips + per-lane edge rails.
        UsdGeom.Scope.Define(stage, f"{road_path}/Markings")
        UsdGeom.Scope.Define(stage, mapping.rails_scope_path(road_id))
        frames = self._sampler.reference_frames(road_id)
        centerline = [f.position for f in frames]
        if len(centerline) >= 2:
            self._write_rail(mapping.centerline_rail_path(road_id), centerline, road_id)

        for lane in self._section_lanes(section):
            boundary = boundaries.get(lane.id)
            edge = boundary.outer if boundary is not None else centerline
            if lane.id != 0 and len(edge) >= 2:
                self._write_rail(mapping.lane_rail_path(road_id, lane.id), edge, road_id, lane.id)
            if not lane.road_marks:
                continue
            mark = lane.road_marks[0]
            strip = self._marking_strip(edge, mark.width)
            if strip is None:
                continue
            preset_id = mark.preset_id or lane.user_data.get("markingPreset", "")
            self.write_marking_strip(strip, road_id, lane.id, preset_id)

    def update_junction(self, junction_id: str) -> None:
        from pxr import Sdf, UsdGeom

        stage = self._ensure_stage()
        assert self._materials is not None
        junction = self._model.junctions[junction_id]
        junction_path = mapping.junction_prim_path(junction_id)
        stage.RemovePrim(Sdf.Path(junction_path))
        prim = UsdGeom.Xform.Define(stage, junction_path).GetPrim()
        prim.CreateAttribute(mapping.ATTR_JUNCTION_ID, Sdf.ValueTypeNames.String).Set(junction_id)

        surface = IntersectionSurface(self._sampler).generate(junction)
        if surface.points:
            mesh = self._write_mesh(mapping.junction_surface_path(junction_id), surface)
            self._tag(mesh.GetPrim(), junction_id=junction_id)
            self._bind(mesh, self._materials.asphalt())

    def write_marking_strip(
        self,
        mesh: MeshData,
        road_id: str,
        lane_id: int,
        preset_id: str,
    ) -> None:
        """Write a marking strip mesh under the road, tagged + material-bound from ``preset_id``."""
        self._ensure_stage()
        assert self._materials is not None
        path = mapping.lane_marking_prim_path(road_id, lane_id)
        prim = self._write_mesh(path, mesh)
        self._tag(prim.GetPrim(), road_id=road_id, lane_id=lane_id)
        params = get_preset(preset_id).material if preset_id else MaterialParams()
        self._bind(prim, self._materials.get_or_create(params))

    # --- pxr writers -------------------------------------------------------------------
    def _write_mesh(self, path: str, mesh: MeshData) -> Any:
        from pxr import Gf, UsdGeom, Vt

        m = UsdGeom.Mesh.Define(self._stage, path)
        m.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*p) for p in mesh.points]))
        m.CreateFaceVertexCountsAttr(Vt.IntArray(list(mesh.face_vertex_counts)))
        m.CreateFaceVertexIndicesAttr(Vt.IntArray(list(mesh.face_vertex_indices)))
        m.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        return m

    def _write_rail(
        self, path: str, points: list, road_id: str, lane_id: int | None = None
    ) -> None:
        """A non-rendering guide BasisCurves the scene layer scatters/arrays along."""
        from pxr import Gf, Sdf, UsdGeom, Vt

        curve = UsdGeom.BasisCurves.Define(self._stage, path)
        curve.CreateTypeAttr(UsdGeom.Tokens.linear)
        curve.CreateWrapAttr(UsdGeom.Tokens.nonperiodic)
        curve.CreateCurveVertexCountsAttr(Vt.IntArray([len(points)]))
        curve.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*p) for p in points]))
        curve.CreatePurposeAttr(UsdGeom.Tokens.guide)
        prim = curve.GetPrim()
        prim.CreateAttribute(mapping.ATTR_ROAD_ID, Sdf.ValueTypeNames.String).Set(road_id)
        if lane_id is not None:
            prim.CreateAttribute(mapping.ATTR_LANE_ID, Sdf.ValueTypeNames.Int).Set(int(lane_id))

    def _tag(
        self,
        prim: Any,
        *,
        road_id: str | None = None,
        lane_id: int | None = None,
        junction_id: str | None = None,
    ) -> None:
        from pxr import Sdf

        if road_id is not None:
            prim.CreateAttribute(mapping.ATTR_ROAD_ID, Sdf.ValueTypeNames.String).Set(road_id)
        if lane_id is not None:
            prim.CreateAttribute(mapping.ATTR_LANE_ID, Sdf.ValueTypeNames.Int).Set(int(lane_id))
        if junction_id is not None:
            attr = prim.CreateAttribute(mapping.ATTR_JUNCTION_ID, Sdf.ValueTypeNames.String)
            attr.Set(junction_id)

    def _bind(self, imageable: Any, material: Any) -> None:
        from pxr import UsdShade

        UsdShade.MaterialBindingAPI(imageable.GetPrim()).Bind(material)

    # --- geometry helpers --------------------------------------------------------------
    def _marking_strip(self, polyline: list, width: float) -> MeshData | None:
        """Thin ribbon centred on ``polyline``, offset +/- ``width``/2 in the xy-perpendicular."""
        if len(polyline) < 2 or width <= 0.0:
            return None
        left: list = []
        right: list = []
        n = len(polyline)
        for i, p in enumerate(polyline):
            a = polyline[max(0, i - 1)]
            b = polyline[min(n - 1, i + 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            length = math.hypot(tx, ty)
            if length == 0.0:
                nx, ny = 0.0, 0.0
            else:
                nx, ny = -ty / length, tx / length
            hw = width / 2.0
            left.append((p[0] + nx * hw, p[1] + ny * hw, p[2]))
            right.append((p[0] - nx * hw, p[1] - ny * hw, p[2]))
        return self._mesh.ribbon(left, right)

    @staticmethod
    def _section_bounds(road: Road, section: LaneSection) -> tuple[float, float]:
        starts = sorted(ls.s for ls in road.lane_sections)
        idx = starts.index(section.s)
        s1 = starts[idx + 1] if idx + 1 < len(starts) else road.length
        return section.s, s1

    @staticmethod
    def _section_lanes(section: LaneSection) -> list:
        lanes = list(section.left) + list(section.right)
        if section.center is not None:
            lanes.append(section.center)
        return lanes
