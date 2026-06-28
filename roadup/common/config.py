"""Global config + external presets-directory resolution. CODE_REFERENCE.md S1."""
from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path

#: Environment variable that overrides the presets directory location.
PRESETS_DIR_ENV = "ROADUP_PRESETS_DIR"

#: Repo root = two levels up from this file (roadup/common/config.py -> repo root).
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PRESETS_DIR = _REPO_ROOT / "presets"


@dataclass(frozen=True)
class Config:
    """Global knobs only.

    Preset *values* are **not** here — they live in external YAML under the presets directory
    (see :func:`resolve_presets_dir` and ``presets/README.md``). Road-type presets are loaded by
    :mod:`roadup.segments.presets`, marking presets by :mod:`roadup.markings.presets`.
    """

    opendrive_version: str = "1.7"        # pinned target (see ARCHITECTURE.md §17)
    default_sampling_step: float = 1.0    # meters (uniform sampler / fixed-grid callers)
    presets_dir: str | None = None        # override the presets directory; None = default

    # === Curvature/elevation-adaptive mesh sampling (the default sampling path) ==========
    # A station is emitted when the reference frame's tangent (heading + elevation pitch + bank)
    # turns by more than ``adaptive_max_angle_deg``, or the chord error would exceed
    # ``adaptive_chord_tol``, bounded by a min/max station spacing. A straight collapses to its two
    # endpoints (2 triangles); a tight curve densifies. Trade-off: smaller values = smoother mesh,
    # more vertices, slower.
    adaptive_max_angle_deg: float = 5.0   # degrees of tangent turn per segment. e.g. 2.0 = very
    #                                       smooth curves (dense); 10.0 = coarse, faceted curves.
    adaptive_chord_tol: float = 0.02      # meters — max chord deviation from the true curve. e.g.
    #                                       0.005 = sub-cm fidelity (dense); 0.1 = visibly chorded.
    adaptive_min_step: float = 0.5        # meters — floor on station spacing (caps hairpins).
    #                                  Raise (e.g. 1.0) to cap vertex count on tight geometry.
    adaptive_max_step: float = 1.0e6      # meters — cap on spacing (effectively unbounded; keeps
    #                                  straights at 2 samples). Set e.g. 10.0 to force a minimum
    #                                  tessellation even on dead-straight roads.

    # === Intersection — lane connectivity (which default movements get seeded) ===========
    # The signed heading change from an incoming road's approach to an outgoing road's departure
    # classifies each candidate movement; these thresholds bin it into straight / left / right /
    # u-turn. U-turns are dropped from the seeded defaults. See intersections/connectivity.py.
    turn_straight_max_deg: float = 45.0   # |heading change| ≤ this ⇒ STRAIGHT. e.g. 30.0 makes only
    #                                  nearly-aligned roads "straight"; gentle bends become turns.
    turn_u_turn_min_deg: float = 135.0    # |heading change| ≥ this ⇒ U_TURN (dropped). e.g. 150.0
    #                                  keeps sharper hairpins as ordinary left/right movements.

    # === Intersection — connecting-road geometry =========================================
    connecting_lane_default_width: float = 3.5  # meters — fallback width when a lane has no width
    #                                  law. UAE/GCC arterial ≈ 3.5; residential ≈ 3.0.
    connection_tangent_tol: float = 0.999  # unit-tangent dot above which two directions count as
    #                                  "aligned" (~2.6°). Decides line-vs-arc-vs-Bézier for a
    #                                  connector. Lower (0.99 ≈ 8°) ⇒ more connectors snap to a
    #                                  straight line; higher ⇒ stricter, more arcs/Béziers.
    connection_upgrade_samples: int = 3   # interior samples kept when an edited arc upgrades to a
    #                                  control-point spline (more = closer to the arc shape).

    # === Junction surface — boundary fillets + cap topology ==============================
    # The junction surface is the cap over a boundary loop of node-road end-edges joined by editable
    # corner Bézier fillets (intersections/boundary.py + surface.py).
    junction_corner_sampling_step: float | None = None  # meters between samples along each corner
    #                                  fillet. None ⇒ use ``default_sampling_step``. e.g. 0.5 =
    #                                  smoother rounded corners (more verts); 2.0 = chunkier.
    # meters between interior Delaunay points filling the cap. Smaller ⇒ denser, more uniform
    # triangles (no slivers); e.g. 1.5 = fine, 6.0 = coarse. Set 0 (or negative) ⇒ centroid fan.
    junction_cap_interior_spacing: float = 3.0
    # meters — subdivide boundary edges longer than this before triangulating (mainly the straight
    # road end-edges) so boundary detail matches the interior density. Keep ≈ the spacing above.
    junction_cap_boundary_max_edge: float = 3.0


def resolve_presets_dir(override: str | Path | None = None) -> Path:
    """Locate the external presets directory.

    Resolution order: explicit ``override`` → ``$ROADUP_PRESETS_DIR`` → the repo-root ``presets/``
    folder (beside the installed ``roadup`` package). The default suits running from source;
    packaged deployments set the env var or pass an override.
    """
    if override is not None:
        return Path(override)
    env = os.environ.get(PRESETS_DIR_ENV)
    if env:
        return Path(env)
    return _DEFAULT_PRESETS_DIR


def load_config(path: str | None = None) -> Config:
    """Load a :class:`Config` from ``path`` (YAML) or return defaults when ``None``."""
    if path is None:
        return Config()
    import yaml

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    known = {f.name for f in fields(Config)}
    return Config(**{k: v for k, v in data.items() if k in known})
