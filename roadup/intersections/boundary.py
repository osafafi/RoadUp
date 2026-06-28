"""Editable junction boundary — node-road extremities joined by corner Bézier fillets.

The junction surface is *not* a blind union of connecting-road ribbons (that double-stacks
vertices along every shared edge). It is the cap over one clean boundary loop:

* each **node road** (a parent road meeting the junction) contributes its drivable cross-section
  where it terminates at the junction — two corner vertices (left + right drivable edge);
* between two angularly-adjacent roads the gap is bridged by a **corner fillet**, a cubic Bézier
  tangent to each road's edge (default handle length ≈ a circular quarter-arc), so the corner is
  editable: dragging a handle in the viewport reshapes the fillet (Stage 6).

Only *edited* corner handles persist — as offsets from their (geometry-derived) endpoints — under
``junction.user_data["boundary"]`` so a read → edit → write cycle round-trips (OpenDRIVE is truth).
The endpoints themselves are always recomputed from current road geometry, so the boundary follows
the roads when they move; a stored handle offset re-applies on top. See
:mod:`roadup.intersections.surface`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from roadup.common.types import Vec3
from roadup.geometry.splines import ControlPoint, Spline

# Bézier handle fraction for a near-straight corner (turn angle → 0); the standard smooth default.
_STRAIGHT_HANDLE_FRACTION = 1.0 / 3.0


def corner_id(from_road: str, to_road: str) -> str:
    """Stable key for the fillet leaving ``from_road`` toward ``to_road`` (survives id reuse)."""
    return f"{from_road}->{to_road}"


@dataclass
class RoadExtremity:
    """One node road's drivable cross-section where it meets the junction.

    ``cw`` / ``ccw`` are the corner vertices on the clockwise / counter-clockwise side seen from the
    junction looking *outward* along the road; ``outward`` is that unit xy direction. Walking the
    boundary counter-clockwise traverses ``cw -> ccw`` (the road's end-edge) then a fillet to the
    next road's ``cw``.
    """

    road_id: str
    cw: Vec3
    ccw: Vec3
    outward: tuple[float, float]


@dataclass
class Corner:
    """Editable cubic-Bézier fillet: ``from_road``'s ccw corner → ``to_road``'s cw corner.

    ``out_handle`` / ``in_handle`` are the Bézier control points (absolute positions). ``edited`` is
    set once a handle is moved, so only user-shaped corners persist to ``<userData>``.
    """

    id: str
    from_road: str
    to_road: str
    start: Vec3
    end: Vec3
    out_handle: Vec3
    in_handle: Vec3
    edited: bool = False

    def spline(self) -> Spline:
        return Spline(
            points=[
                ControlPoint(position=self.start, out_handle=self.out_handle, id="cp_001"),
                ControlPoint(position=self.end, in_handle=self.in_handle, id="cp_002"),
            ],
            kind="bezier",
        )

    def sample(self, step: float) -> list[Vec3]:
        """Polyline along the fillet (endpoints included)."""
        return self.spline().sample(step)

    def move_out_handle(self, position: Vec3) -> None:
        self.out_handle = position
        self.edited = True

    def move_in_handle(self, position: Vec3) -> None:
        self.in_handle = position
        self.edited = True


@dataclass
class JunctionBoundary:
    """The closed boundary of a junction surface: road end-edges + corner fillets, CCW."""

    extremities: list[RoadExtremity] = field(default_factory=list)
    corners: list[Corner] = field(default_factory=list)

    def ring(self, step: float = 1.0) -> list[Vec3]:
        """Closed boundary polyline (CCW): each road end-edge then its fillet to the next road.

        Corner-fillet endpoints coincide with the road-edge corners, so they are dropped from each
        sampled fillet — the returned ring carries every boundary vertex exactly once.
        """
        if not self.extremities:
            return []
        pts: list[Vec3] = []
        for ext, corner in zip(self.extremities, self.corners, strict=True):
            pts.append(ext.cw)
            pts.append(ext.ccw)
            pts.extend(corner.sample(step)[1:-1])  # interior only — endpoints are the edge corners
        return pts

    def corner(self, cid: str) -> Corner:
        for c in self.corners:
            if c.id == cid:
                return c
        raise KeyError(f"no corner {cid!r} in junction boundary")

    # --- round-trip -------------------------------------------------------------------
    def overrides(self) -> dict:
        """``<userData>`` payload: only *edited* corners, as handle offsets from their endpoints.

        Offsets (not absolute positions) so the fillet shape rides along when the road moves and the
        endpoint is recomputed. Empty ``{}`` when nothing was edited (default junctions stay clean).
        """
        edited = {
            c.id: {
                "fromRoad": c.from_road,
                "toRoad": c.to_road,
                "outHandle": _sub(c.out_handle, c.start),
                "inHandle": _sub(c.in_handle, c.end),
            }
            for c in self.corners
            if c.edited
        }
        return {"corners": edited} if edited else {}

    def apply_overrides(self, payload: dict) -> None:
        """Re-apply stored handle offsets onto the (freshly derived) corners."""
        stored = (payload or {}).get("corners", {})
        for c in self.corners:
            ov = stored.get(c.id)
            if ov is None:
                continue
            c.out_handle = _add(c.start, ov["outHandle"])
            c.in_handle = _add(c.end, ov["inHandle"])
            c.edited = True


def default_corner(
    cid: str,
    from_road: str,
    to_road: str,
    start: Vec3,
    end: Vec3,
    start_outward: tuple[float, float],
    end_outward: tuple[float, float],
) -> Corner:
    """A circular fillet: handles point *inward* along each road edge, length sized to the arc.

    Tangent to ``from_road``'s edge at ``start`` and ``to_road``'s edge at ``end``, continuing each
    road's long edge *into* the junction so the corner rounds concavely toward the centre — the
    classic intersection corner, not an outward bulge (which would also break the centroid fan).

    The arc turns from ``-start_outward`` to ``+end_outward``; the handle length
    ``(4/3)·tan(θ/4)·R`` (``R`` = chord / 2·sin(θ/2)) makes the cubic Bézier match a true circular
    arc of that turn angle ``θ`` (near-exact up to ~120°, the usual intersection range).
    """
    chord = (
        (end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2 + (end[2] - start[2]) ** 2
    ) ** 0.5
    h = _circular_handle_length(chord, start_outward, end_outward)
    # Inward: a handle continues the road edge toward the junction (opposite the outward direction).
    out_handle = (start[0] - start_outward[0] * h, start[1] - start_outward[1] * h, start[2])
    in_handle = (end[0] - end_outward[0] * h, end[1] - end_outward[1] * h, end[2])
    return Corner(
        id=cid,
        from_road=from_road,
        to_road=to_road,
        start=start,
        end=end,
        out_handle=out_handle,
        in_handle=in_handle,
    )


def _circular_handle_length(
    chord: float, start_outward: tuple[float, float], end_outward: tuple[float, float]
) -> float:
    """Bézier handle length so the fillet matches a circular arc of the corner's turn angle.

    The arc tangent rotates from ``-start_outward`` to ``+end_outward``; that turn angle ``θ`` is
    the arc's central angle. For a near-straight corner (θ → 0) fall back to the standard chord/3.
    """
    ux, uy = -start_outward[0], -start_outward[1]
    vx, vy = end_outward[0], end_outward[1]
    theta = math.atan2(abs(ux * vy - uy * vx), ux * vx + uy * vy)  # in [0, π]
    half = theta / 2.0
    if math.sin(half) < 1e-6:
        return _STRAIGHT_HANDLE_FRACTION * chord
    radius = chord / (2.0 * math.sin(half))
    return (4.0 / 3.0) * math.tan(theta / 4.0) * radius


def _sub(a: Vec3, b: Vec3) -> list[float]:
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def _add(a: Vec3, off: list[float]) -> Vec3:
    return (a[0] + off[0], a[1] + off[1], a[2] + off[2])
