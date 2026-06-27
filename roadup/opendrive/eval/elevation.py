"""Vertical profile (elevation) + lateral profile (superelevation) evaluation. CODE_REFERENCE.md S5.

Plan-view evaluation (:mod:`roadup.opendrive.eval.planview`) produces planar station
:class:`~roadup.geometry.sampling.Frame`s (``z = 0``, horizontal tangent/normal). This module lifts
those frames into 3D using the road's ``<elevationProfile>`` (``z`` along ``s``) and
``<lateralProfile><superelevation>`` (bank/roll angle along ``s``):

* ``z`` comes straight from the elevation cubic.
* the tangent gains a pitch ``θ = atan(dz/ds)`` from the elevation slope.
* the lateral normal (OpenDRIVE +t, left) is rolled about the tangent by the bank angle, so a banked
  cross-section tilts (lane width is then measured in that tilted plane — exactly superelevation).

When a road has no elevation and no superelevation the frames are returned unchanged (flat), so the
existing planar behaviour — and every flat-road golden — is byte-for-byte preserved.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

import numpy as np

from roadup.geometry.sampling import Frame

if TYPE_CHECKING:
    from roadup.opendrive.model.road import (
        ElevationRecord,
        Road,
        SuperelevationRecord,
    )


def _governing(records: Sequence, s: float):
    """The last record whose ``s`` is at or before the query (mirrors ``Sampler._width_at``)."""
    rec = records[0]
    for candidate in sorted(records, key=lambda r: r.s):
        if candidate.s <= s + 1e-9:
            rec = candidate
        else:
            break
    return rec


def eval_poly3(records: Sequence, s: float) -> float:
    """Evaluate a piecewise cubic (elevation z or bank angle) at station ``s``."""
    if not records:
        return 0.0
    rec = _governing(records, s)
    ds = s - rec.s
    return rec.a + rec.b * ds + rec.c * ds * ds + rec.d * ds * ds * ds


def eval_poly3_slope(records: Sequence, s: float) -> float:
    """Evaluate the analytic derivative ``d/ds`` of the piecewise cubic at station ``s``."""
    if not records:
        return 0.0
    rec = _governing(records, s)
    ds = s - rec.s
    return rec.b + 2.0 * rec.c * ds + 3.0 * rec.d * ds * ds


def eval_elevation(records: Sequence[ElevationRecord], s: float) -> float:
    """Elevation ``z`` at station ``s``."""
    return eval_poly3(records, s)


def eval_elevation_slope(records: Sequence[ElevationRecord], s: float) -> float:
    """Elevation slope ``dz/ds`` at station ``s`` (drives the tangent pitch)."""
    return eval_poly3_slope(records, s)


def eval_superelevation(records: Sequence[SuperelevationRecord], s: float) -> float:
    """Bank/roll angle (radians) at station ``s``."""
    return eval_poly3(records, s)


def vertical_angle_fn(road: Road) -> Callable[[float], float] | None:
    """Build ``s -> (elevation pitch + bank angle)`` for adaptive sampling, or ``None`` if flat.

    The returned value is the vertical turning the adaptive sampler folds into its angle threshold
    so a rising/banking road gets enough longitudinal samples. ``None`` signals "nothing vertical
    to refine" so the sampler skips the per-station evaluation entirely.
    """
    elev = road.elevation
    superelev = road.superelevation
    if not elev and not superelev:
        return None

    def _f(s: float) -> float:
        pitch = math.atan(eval_elevation_slope(elev, s)) if elev else 0.0
        bank = eval_superelevation(superelev, s) if superelev else 0.0
        return pitch + bank

    return _f


def _rotate_about_axis(v: np.ndarray, axis: np.ndarray, angle: float) -> np.ndarray:
    """Rodrigues rotation of ``v`` about a unit ``axis`` by ``angle`` (radians)."""
    if abs(angle) < 1e-12:
        return v
    c, s = math.cos(angle), math.sin(angle)
    return v * c + np.cross(axis, v) * s + axis * float(np.dot(axis, v)) * (1.0 - c)


def apply_profiles(frames: list[Frame], road: Road) -> list[Frame]:
    """Return ``frames`` lifted to 3D using ``road``'s elevation + superelevation profiles.

    Pure function: builds new :class:`Frame`s, leaving the planar inputs untouched. A road with no
    profiles is returned with the same z/tangent/normal it had (flat).
    """
    elev = road.elevation
    superelev = road.superelevation
    if not elev and not superelev:
        return frames

    out: list[Frame] = []
    for f in frames:
        s = f.s
        z = eval_elevation(elev, s)
        pitch = math.atan(eval_elevation_slope(elev, s)) if elev else 0.0
        bank = eval_superelevation(superelev, s) if superelev else 0.0

        # Planar heading from the (horizontal) tangent; pitch tilts it up/down.
        hdg = math.atan2(f.tangent[1], f.tangent[0])
        cos_p, sin_p = math.cos(pitch), math.sin(pitch)
        tangent = np.array(
            [math.cos(hdg) * cos_p, math.sin(hdg) * cos_p, sin_p], dtype=float
        )
        # Horizontal left normal (+t), then rolled about the tangent by the bank angle.
        h_normal = np.array([-math.sin(hdg), math.cos(hdg), 0.0], dtype=float)
        t_unit = tangent / np.linalg.norm(tangent)
        normal = _rotate_about_axis(h_normal, t_unit, bank)

        out.append(
            Frame(
                s=s,
                position=(f.position[0], f.position[1], float(z)),
                tangent=(float(tangent[0]), float(tangent[1]), float(tangent[2])),
                normal=(float(normal[0]), float(normal[1]), float(normal[2])),
            )
        )
    return out
