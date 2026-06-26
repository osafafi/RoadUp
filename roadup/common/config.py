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
    default_sampling_step: float = 1.0    # meters
    presets_dir: str | None = None        # override the presets directory; None = default


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
