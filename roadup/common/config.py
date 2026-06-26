"""Global config + external presets-directory resolution. CODE_REFERENCE.md S1."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

#: Environment variable that overrides the presets directory location.
PRESETS_DIR_ENV = "ROADUP_PRESETS_DIR"


@dataclass(frozen=True)
class Config:
    """Global knobs only.

    Preset *values* are **not** here — they live in external YAML under the presets directory
    (see :func:`resolve_presets_dir` and ``presets/README.md``). Road-type presets are loaded by
    :mod:`roadup.segments.presets`, marking presets by :mod:`roadup.markings.presets`.
    """

    opendrive_version: str = "1.7"        # pinned target (see ARCHITECTURE.md §17)
    default_sampling_step: float = 1.0    # meters
    presets_dir: str | None = None        # override the presets directory; None = default


def resolve_presets_dir(override: str | Path | None = None) -> Path:
    """Locate the external presets directory.

    Resolution order: explicit ``override`` → ``$ROADUP_PRESETS_DIR`` → the repo-root ``presets/``
    folder (beside the installed ``roadup`` package). The default suits running from source;
    packaged deployments set the env var or pass an override.
    """
    raise NotImplementedError


def load_config(path: str | None = None) -> Config:
    """Load a :class:`Config` from ``path`` (YAML) or return defaults when ``None``."""
    raise NotImplementedError
