"""Sample the model into frames and lane boundaries. CODE_REFERENCE.md S5.

Pure-Python path: plan-view evaluation via :mod:`roadup.opendrive.eval.planview`, lateral
offsetting via :mod:`roadup.geometry.offset`. A native libOpenDRIVE backend can wrap behind the
same surface once a binding is pinned (deferred; see ARCHITECTURE.md decision 4).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from roadup.common.config import Config
from roadup.common.types import Vec3
from roadup.geometry.offset import offset_polyline
from roadup.opendrive.eval.elevation import apply_profiles, vertical_angle_fn
from roadup.opendrive.eval.planview import sample_planview, sample_planview_adaptive

if TYPE_CHECKING:
    from roadup.geometry.sampling import Frame
    from roadup.opendrive.model.network import OpenDriveModel
    from roadup.opendrive.model.road import Lane, LaneSection, Road


@dataclass
class LaneBoundaries:
    lane_id: int
    inner: list[Vec3] = field(default_factory=list)  # boundary toward the reference line
    outer: list[Vec3] = field(default_factory=list)  # boundary away from the reference line


class Sampler:
    """Wraps libOpenDRIVE evaluation; falls back to :mod:`roadup.geometry` for the pure path."""

    def __init__(
        self,
        model: OpenDriveModel,
        step: float | None = None,
        *,
        config: Config | None = None,
        adaptive: bool = True,
    ) -> None:
        self._model = model
        self._config = config or Config()
        # `step` defaults to the configured sampling step so one Config drives the whole pipeline.
        self._step = self._config.default_sampling_step if step is None else step
        self._adaptive = adaptive

    @property
    def model(self) -> OpenDriveModel:
        """The model being sampled (read-only; consumers that need road/junction lookups)."""
        return self._model

    @property
    def config(self) -> Config:
        """The active config (read-only; downstream builders inherit it from the sampler)."""
        return self._config

    @property
    def step(self) -> float:
        """Nominal sampling step in metres (uniform path / corner sampling default)."""
        return self._step

    def reference_frames(self, road_id: str) -> list[Frame]:
        road = self._model.get_road(road_id)
        frames = self._sample_reference(road)
        return apply_profiles(frames, road)

    def _sample_reference(self, road: Road) -> list[Frame]:
        """Plan-view frames for ``road`` — curvature-adaptive by default, uniform on request."""
        if not self._adaptive:
            return sample_planview(road.geometry, self._step)
        cfg = self._config
        return sample_planview_adaptive(
            road.geometry,
            max_angle=math.radians(cfg.adaptive_max_angle_deg),
            max_chord_error=cfg.adaptive_chord_tol,
            min_step=cfg.adaptive_min_step,
            max_step=cfg.adaptive_max_step,
            vertical_angle=vertical_angle_fn(road),
        )

    def lane_boundaries(self, road_id: str, s0: float, s1: float) -> list[LaneBoundaries]:
        """Inner/outer boundary polylines for each lane of the section governing ``s0``.

        Widths are evaluated per station (so width tapers are honoured). ``[s0, s1]`` is expected to
        lie within a single lane section.
        """
        road = self._model.get_road(road_id)
        frames = [f for f in self.reference_frames(road_id) if s0 - 1e-6 <= f.s <= s1 + 1e-6]
        if not frames:
            return []
        section = road.lane_section_at(s0)
        out: list[LaneBoundaries] = []
        # Left lanes accumulate +t outward (ids 1, 2, ...); right lanes accumulate -t (-1, -2, ...).
        out.extend(self._side_boundaries(section, frames, section.left, sign=1.0))
        out.extend(self._side_boundaries(section, frames, section.right, sign=-1.0))
        return out

    def road_surface_polylines(self, road_id: str) -> tuple[list[Vec3], list[Vec3]]:
        """Outermost left & right drivable edges for the ribbon (uses each frame's own section)."""
        road = self._model.get_road(road_id)
        frames = self.reference_frames(road_id)
        left_t: list[float] = []
        right_t: list[float] = []
        for f in frames:
            section = road.lane_section_at(f.s)
            ds = f.s - section.s
            left_t.append(sum(self._width_at(ln, ds) for ln in section.left))
            right_t.append(-sum(self._width_at(ln, ds) for ln in section.right))
        return offset_polyline(frames, left_t), offset_polyline(frames, right_t)

    # --- internals --------------------------------------------------------------------
    def _side_boundaries(
        self,
        section: LaneSection,
        frames: list[Frame],
        lanes: list[Lane],
        sign: float,
    ) -> list[LaneBoundaries]:
        ordered = sorted(lanes, key=lambda ln: ln.id, reverse=sign < 0)
        cum = [0.0] * len(frames)
        result: list[LaneBoundaries] = []
        for lane in ordered:
            inner = list(cum)
            widths = [self._width_at(lane, f.s - section.s) for f in frames]
            cum = [c + sign * w for c, w in zip(cum, widths, strict=True)]
            result.append(
                LaneBoundaries(
                    lane_id=lane.id,
                    inner=offset_polyline(frames, inner),
                    outer=offset_polyline(frames, list(cum)),
                )
            )
        return result

    def _width_at(self, lane: Lane, ds: float) -> float:
        """Evaluate the lane width law ``w = a + b*l + c*l^2 + d*l^3`` (``l = ds - s_offset``)."""
        if not lane.widths:
            return 0.0
        rec = lane.widths[0]
        for w in sorted(lane.widths, key=lambda r: r.s_offset):
            if w.s_offset <= ds + 1e-9:
                rec = w
            else:
                break
        local = ds - rec.s_offset
        return rec.a + rec.b * local + rec.c * local**2 + rec.d * local**3
