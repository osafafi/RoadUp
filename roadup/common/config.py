"""Configuration bundle and loader. CODE_REFERENCE.md S1."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Loaded preset/config bundle.

    Road-type presets live in :mod:`roadup.segments.presets` and marking presets in
    :mod:`roadup.markings.presets`; this object carries global knobs only.
    """

    opendrive_version: str = "1.7"
    default_sampling_step: float = 1.0  # meters


def load_config(path: str | None = None) -> Config:
    """Load a :class:`Config` from ``path`` (TOML/JSON) or return defaults when ``None``."""
    raise NotImplementedError
