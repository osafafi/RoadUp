"""Junction surface generation from an editable boundary. CODE_REFERENCE.md S9.

The surface is the cap over a single clean boundary loop (no double-stacked edge vertices): each
node road's drivable end-cross-section, joined to its angular neighbour by an editable corner Bézier
fillet. See :mod:`roadup.intersections.boundary` for the boundary model and round-trip; heavy
concave/boolean cases are delegated to :class:`roadup.blender.processor.MeshProcessor` later
(Stage 7). This default suits the common star-convex junction.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from roadup.geometry.mesh import MeshBuilder, MeshData
from roadup.intersections.boundary import (
    JunctionBoundary,
    RoadExtremity,
    corner_id,
    default_corner,
)
from roadup.intersections.connectivity import ConnectivitySolver

if TYPE_CHECKING:
    from roadup.common.config import Config
    from roadup.intersections.connectivity import RoadEnd
    from roadup.opendrive.eval.sampler import Sampler
    from roadup.opendrive.model.junction import Junction

# Key under junction.user_data holding the editable-boundary override payload.
_BOUNDARY_KEY = "boundary"


class IntersectionSurface:
    """Generate (and round-trip the boundary of) a junction surface mesh."""

    def __init__(
        self, sampler: Sampler, *, config: Config | None = None, corner_step: float | None = None
    ) -> None:
        self._sampler = sampler
        self._mesh = MeshBuilder()
        cfg = config if config is not None else sampler.config
        self._config = cfg
        # Corner fillet sample step: explicit arg → config → the sampler's nominal step.
        self._corner_step = (
            corner_step
            if corner_step is not None
            else (cfg.junction_corner_sampling_step or sampler.step)
        )

    def generate(self, junction: Junction) -> MeshData:
        """Cap the junction's boundary loop into a single watertight surface mesh.

        Cap topology is config-driven: a positive ``junction_cap_interior_spacing`` fills the cap
        with a Delaunay mesh of interior points (near-isotropic triangles); ``<= 0`` falls back to
        the simple centroid fan.
        """
        boundary = self.boundary(junction)
        ring = boundary.ring(self._corner_step)
        if len(ring) < 3:
            return MeshData()
        spacing = self._config.junction_cap_interior_spacing
        if spacing and spacing > 0.0:
            return self._mesh.polygon_surface(
                ring,
                interior_spacing=spacing,
                boundary_max_edge=self._config.junction_cap_boundary_max_edge,
            )
        return self._mesh.polygon_surface(ring)

    def boundary(self, junction: Junction) -> JunctionBoundary:
        """The current editable boundary: default fillets + any stored handle overrides.

        Endpoints are always recomputed from current road geometry; edited handle offsets persisted
        under ``junction.user_data`` are re-applied on top so a read → edit → write cycle survives.
        """
        boundary = self._default_boundary(junction)
        boundary.apply_overrides(junction.user_data.get(_BOUNDARY_KEY, {}))
        return boundary

    def commit_boundary(self, junction: Junction, boundary: JunctionBoundary) -> None:
        """Persist edited corner handles into ``junction.user_data`` (drops the key when clean)."""
        overrides = boundary.overrides()
        if overrides:
            junction.user_data[_BOUNDARY_KEY] = overrides
        else:
            junction.user_data.pop(_BOUNDARY_KEY, None)

    # --- internals --------------------------------------------------------------------
    def _default_boundary(self, junction: Junction) -> JunctionBoundary:
        node_ids = self._node_road_ids(junction)
        if len(node_ids) < 2:
            return JunctionBoundary()
        ends = ConnectivitySolver(self._sampler.model).road_ends(node_ids)

        extremities: list[RoadExtremity] = []
        for rid in node_ids:
            ext = self._extremity(rid, ends[rid])
            if ext is not None:
                extremities.append(ext)
        if len(extremities) < 2:
            return JunctionBoundary()

        # CCW order around the junction by each road's outward direction.
        extremities.sort(key=lambda e: math.atan2(e.outward[1], e.outward[0]))
        corners = [
            default_corner(
                corner_id(a.road_id, b.road_id),
                a.road_id,
                b.road_id,
                a.ccw,
                b.cw,
                a.outward,
                b.outward,
            )
            for a, b in _ring_pairs(extremities)
        ]
        return JunctionBoundary(extremities=extremities, corners=corners)

    def _extremity(self, road_id: str, end: RoadEnd) -> RoadExtremity | None:
        """Drivable end-cross-section corners + outward direction for one node road."""
        left, right = self._sampler.road_surface_polylines(road_id)
        if len(left) < 2 or len(right) < 2:
            return None
        # `left` is the +t (left) edge, `right` the -t edge. At a "start" contact +s points outward
        # so +t is the CCW-side corner; at an "end" contact +s points inward so +t is the CW corner.
        if end.contact == "start":
            ccw, cw = left[0], right[0]
        else:
            ccw, cw = right[-1], left[-1]
        outward = -end.approach  # approach points into the node; outward points away
        return RoadExtremity(
            road_id=road_id,
            cw=cw,
            ccw=ccw,
            outward=(float(outward[0]), float(outward[1])),
        )

    def _node_road_ids(self, junction: Junction) -> list[str]:
        """Parent roads at the junction: each connection's incoming + connecting-road successor."""
        model = self._sampler.model
        ids: set[str] = set()
        for conn in junction.connections:
            ids.add(conn.incoming_road)
            link = model.get_road(conn.connecting_road).link
            if link.successor is not None and link.successor[0] == "road":
                ids.add(link.successor[1])
        return sorted(ids)


def _ring_pairs(items: list[RoadExtremity]) -> list[tuple[RoadExtremity, RoadExtremity]]:
    """Consecutive pairs around the closed ring: (i, i+1) with wrap-around."""
    n = len(items)
    return [(items[i], items[(i + 1) % n]) for i in range(n)]
