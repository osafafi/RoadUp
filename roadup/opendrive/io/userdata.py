"""Round-trip RoadUp editing intent via OpenDRIVE <userData>. CODE_REFERENCE.md S4 and S14."""
from __future__ import annotations

from typing import Any

USERDATA_NS = "roadup"  # <userData code="roadup">{json}</userData>


def encode(payload: dict[str, Any]) -> str:
    """Serialize an editing-intent payload to a compact, stable-ordered JSON string."""
    raise NotImplementedError


def decode(blob: str) -> dict[str, Any]:
    """Inverse of :func:`encode`."""
    raise NotImplementedError
