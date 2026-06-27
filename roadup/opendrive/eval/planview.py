"""Pure-Python evaluation of OpenDRIVE plan-view records. CODE_REFERENCE.md S5.

Turns a ``<planView><geometry>`` record (line / arc / spiral / paramPoly3) into world points and
headings, and samples a whole reference line into station :class:`Frame`s. This is the pure-Python
geometry-evaluation path used when no native libOpenDRIVE backend is pinned (the default in CI):

* **line / arc** — closed form.
* **spiral** (clothoid) — heading is quadratic in arc length; position by numeric integration of
  ``(cos h, sin h)`` (the standard odrSpiral approach, no Fresnel/scipy dependency).
* **paramPoly3** — local cubic ``u(p), v(p)`` rotated by ``hdg``; the parameter ``p`` is mapped to
  arc length by a fine cumulative integration (so frame ``s`` values are true arc length).
"""
from __future__ import annotations

import math
from collections.abc import Callable
from typing import TYPE_CHECKING

import numpy as np

from roadup.common.errors import GeometryError
from roadup.common.types import GeometryType, Vec3
from roadup.geometry.sampling import Frame

if TYPE_CHECKING:
    from roadup.opendrive.model.road import Geometry

# Internal integration step (metres) for spiral/paramPoly3 dense sampling. Fine enough that a
# viewport-grade reference line is sub-millimetre accurate over typical record lengths.
_SUBSTEP = 0.25


def eval_record(geom: Geometry, ds: float) -> Vec3:
    """Return ``(x, y, hdg)`` at local arc length ``ds`` along ``geom`` (``ds`` in ``[0, length]``).

    The third component is the heading (radians), not a z-coordinate — plan-view records are planar.
    """
    ds = min(max(ds, 0.0), geom.length)
    if geom.type == GeometryType.LINE:
        return (geom.x + ds * math.cos(geom.hdg), geom.y + ds * math.sin(geom.hdg), geom.hdg)
    if geom.type == GeometryType.ARC:
        return _eval_arc(geom, ds)
    if geom.type in (GeometryType.SPIRAL, GeometryType.PARAM_POLY3):
        s_local, xs, ys, hdgs = _dense_record(geom)
        x = float(np.interp(ds, s_local, xs))
        y = float(np.interp(ds, s_local, ys))
        hdg = float(np.interp(ds, s_local, np.unwrap(hdgs)))
        return (x, y, hdg)
    raise GeometryError(f"unsupported plan-view geometry type {geom.type!r}")


def sample_planview(geometry: list[Geometry], step: float) -> list[Frame]:
    """Sample a road's plan-view (ordered geometry records) into station frames ~``step`` m apart.

    Frames carry true cumulative arc length ``s`` (``geom.s`` + local), exact analytic tangents, and
    the OpenDRIVE +t normal (left of tangent). Shared record joints are de-duplicated.
    """
    if step <= 0.0:
        raise GeometryError("step must be positive")
    if not geometry:
        raise GeometryError("plan-view has no geometry records")

    frames: list[Frame] = []
    for geom in sorted(geometry, key=lambda g: g.s):
        s_local, xs, ys, hdgs = _dense_record(geom)
        total = float(s_local[-1])
        if total <= 0.0:
            continue
        n = max(1, int(round(total / step)))
        targets = np.linspace(0.0, total, n + 1)
        tx = np.interp(targets, s_local, xs)
        ty = np.interp(targets, s_local, ys)
        th = np.interp(targets, s_local, np.unwrap(hdgs))
        for i, ts in enumerate(targets):
            # Skip the first sample of every record after the first: it coincides with the
            # previous record's end joint.
            if frames and i == 0:
                continue
            frames.append(_frame(geom.s + float(ts), float(tx[i]), float(ty[i]), float(th[i])))
    return frames


def sample_planview_adaptive(
    geometry: list[Geometry],
    *,
    max_angle: float,
    max_chord_error: float,
    min_step: float,
    max_step: float,
    vertical_angle: Callable[[float], float] | None = None,
) -> list[Frame]:
    """Sample a reference line with **curvature-adaptive** station spacing.

    A station is emitted only when the reference frame's tangent has turned by more than
    ``max_angle`` (radians) since the last one, or the chord would deviate from the true curve by
    more than ``max_chord_error`` (metres) — bounded below by ``min_step`` (caps hairpin density)
    and above by ``max_step``. The turn metric is the plan-view heading change plus, when
    ``vertical_angle`` is supplied, the change in the vertical angle (elevation pitch + bank) at the
    same global ``s`` — so a rising or banking straight still gets enough samples while a flat
    straight collapses to its two endpoints (one quad, two triangles).

    The fixed-grid :func:`sample_planview` remains available for callers that want a uniform step.
    """
    if max_angle <= 0.0 or min_step <= 0.0 or max_step <= 0.0:
        raise GeometryError("adaptive sampling needs positive max_angle/min_step/max_step")
    if not geometry:
        raise GeometryError("plan-view has no geometry records")

    frames: list[Frame] = []
    for geom in sorted(geometry, key=lambda g: g.s):
        s_local, xs, ys, hdgs = _dense_record(geom)
        total = float(s_local[-1])
        if total <= 0.0:
            continue
        hdg_unwrapped = np.unwrap(hdgs)
        # A straight record is exactly two dense points; with no interior candidates the adaptive
        # walk can't add stations for *vertical* curvature. Densify under-resolved records (a line
        # is straight, so linear interpolation is exact) so pitch/bank refinement has a place to go.
        n_target = max(2, int(math.ceil(total / _SUBSTEP)) + 1)
        if vertical_angle is not None and len(s_local) < n_target:
            grid = np.linspace(0.0, total, n_target)
            xs = np.interp(grid, s_local, xs)
            ys = np.interp(grid, s_local, ys)
            hdg_unwrapped = np.interp(grid, s_local, hdg_unwrapped)
            s_local = grid
        keep = _adaptive_indices(
            s_local, hdg_unwrapped, geom.s, max_angle, max_chord_error,
            min_step, max_step, vertical_angle,
        )
        for k, idx in enumerate(keep):
            # Drop the shared joint with the previous record (its end == this record's start).
            if frames and k == 0:
                continue
            frames.append(
                _frame(geom.s + float(s_local[idx]), float(xs[idx]), float(ys[idx]),
                       float(hdg_unwrapped[idx]))
            )
    return frames


def _adaptive_indices(
    s_local: np.ndarray,
    hdg: np.ndarray,
    s_base: float,
    max_angle: float,
    max_chord_error: float,
    min_step: float,
    max_step: float,
    vertical_angle: Callable[[float], float] | None,
) -> list[int]:
    """Pick indices into a dense record so consecutive samples respect the adaptive criteria."""
    n = len(s_local)
    if n <= 2:
        return list(range(n))
    # Per-point local curvature κ ≈ |dψ/ds| (central difference), for the chord-error bound.
    kappa = np.zeros(n)
    dpsi = np.gradient(hdg)
    dl = np.gradient(s_local)
    with np.errstate(divide="ignore", invalid="ignore"):
        kappa = np.where(dl > 1e-12, np.abs(dpsi / dl), 0.0)
    # Cumulative vertical turn (elevation pitch + bank) at each station, if a profile is supplied.
    if vertical_angle is not None:
        vangle = np.array([vertical_angle(s_base + float(s)) for s in s_local])
        cum_vert = np.concatenate([[0.0], np.cumsum(np.abs(np.diff(vangle)))])
    else:
        cum_vert = np.zeros(n)

    keep = [0]
    last = 0
    k_seg = 0.0
    for i in range(1, n):
        k_seg = max(k_seg, float(kappa[i]))
        seg_len = float(s_local[i] - s_local[last])
        turn = abs(float(hdg[i] - hdg[last])) + float(cum_vert[i] - cum_vert[last])
        chord_limit = math.sqrt(8.0 * max_chord_error / k_seg) if k_seg > 1e-9 else math.inf
        over = turn >= max_angle or seg_len >= max_step or seg_len >= chord_limit
        if over and seg_len >= min_step:
            keep.append(i)
            last = i
            k_seg = 0.0
    if keep[-1] != n - 1:
        keep.append(n - 1)
    return keep


# --- per-record evaluation ------------------------------------------------------------
def _eval_arc(geom: Geometry, ds: float) -> Vec3:
    k = geom.params.get("curvature", 0.0)
    if abs(k) < 1e-12:
        return (geom.x + ds * math.cos(geom.hdg), geom.y + ds * math.sin(geom.hdg), geom.hdg)
    hdg = geom.hdg + k * ds
    x = geom.x + (math.sin(hdg) - math.sin(geom.hdg)) / k
    y = geom.y - (math.cos(hdg) - math.cos(geom.hdg)) / k
    return (x, y, hdg)


def _dense_record(geom: Geometry) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Dense ``(s_local, xs, ys, hdgs)`` along one record; ``s_local`` is true arc length."""
    if geom.type == GeometryType.LINE:
        s = np.array([0.0, geom.length])
        return s, geom.x + s * math.cos(geom.hdg), geom.y + s * math.sin(geom.hdg), \
            np.array([geom.hdg, geom.hdg])
    if geom.type == GeometryType.ARC:
        return _dense_arc(geom)
    if geom.type == GeometryType.SPIRAL:
        return _dense_spiral(geom)
    if geom.type == GeometryType.PARAM_POLY3:
        return _dense_parampoly3(geom)
    raise GeometryError(f"unsupported plan-view geometry type {geom.type!r}")


def _dense_arc(geom: Geometry) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n = max(2, int(math.ceil(geom.length / _SUBSTEP)) + 1)
    s = np.linspace(0.0, geom.length, n)
    k = geom.params.get("curvature", 0.0)
    if abs(k) < 1e-12:
        return s, geom.x + s * math.cos(geom.hdg), geom.y + s * math.sin(geom.hdg), \
            np.full(n, geom.hdg)
    hdg = geom.hdg + k * s
    xs = geom.x + (np.sin(hdg) - math.sin(geom.hdg)) / k
    ys = geom.y - (np.cos(hdg) - math.cos(geom.hdg)) / k
    return s, xs, ys, hdg


def _dense_spiral(geom: Geometry) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Clothoid: curvature varies linearly with arc length; integrate position numerically."""
    c0 = geom.params.get("curvStart", 0.0)
    c1 = geom.params.get("curvEnd", 0.0)
    length = geom.length
    n = max(2, int(math.ceil(length / _SUBSTEP)) + 1)
    s = np.linspace(0.0, length, n)
    dk = (c1 - c0) / length if length > 0 else 0.0
    hdg = geom.hdg + c0 * s + 0.5 * dk * s * s
    # Trapezoidal integration of the unit tangent gives position.
    cos_h, sin_h = np.cos(hdg), np.sin(hdg)
    ds = np.diff(s)
    dx = 0.5 * (cos_h[:-1] + cos_h[1:]) * ds
    dy = 0.5 * (sin_h[:-1] + sin_h[1:]) * ds
    xs = geom.x + np.concatenate([[0.0], np.cumsum(dx)])
    ys = geom.y + np.concatenate([[0.0], np.cumsum(dy)])
    return s, xs, ys, hdg


def _dense_parampoly3(geom: Geometry) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """paramPoly3: sample by parameter ``p``; ``s_local`` is recovered cumulative arc length."""
    p_arclen = geom.params.get("pRangeArcLength", 0.0) > 0.5  # default = normalized (p in [0,1])
    p_end = geom.length if p_arclen else 1.0
    n = max(2, int(math.ceil(geom.length / _SUBSTEP)) + 1)
    p = np.linspace(0.0, p_end, n)
    aU, bU, cU, dU = (geom.params.get(k, 0.0) for k in ("aU", "bU", "cU", "dU"))
    aV, bV, cV, dV = (geom.params.get(k, 0.0) for k in ("aV", "bV", "cV", "dV"))
    u = aU + bU * p + cU * p**2 + dU * p**3
    v = aV + bV * p + cV * p**2 + dV * p**3
    du = bU + 2 * cU * p + 3 * dU * p**2
    dv = bV + 2 * cV * p + 3 * dV * p**2
    ch, sh = math.cos(geom.hdg), math.sin(geom.hdg)
    xs = geom.x + ch * u - sh * v
    ys = geom.y + sh * u + ch * v
    hdg = geom.hdg + np.arctan2(dv, du)
    # Cumulative chord-length recovers arc length along the (already dense) curve.
    seg = np.hypot(np.diff(xs), np.diff(ys))
    s_local = np.concatenate([[0.0], np.cumsum(seg)])
    return s_local, xs, ys, hdg


def _frame(s: float, x: float, y: float, hdg: float) -> Frame:
    tangent = (math.cos(hdg), math.sin(hdg), 0.0)
    normal = (-math.sin(hdg), math.cos(hdg), 0.0)  # left of tangent in xy (+t)
    return Frame(s=s, position=(x, y, 0.0), tangent=tangent, normal=normal)
