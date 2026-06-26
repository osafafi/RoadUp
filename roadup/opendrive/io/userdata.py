"""Round-trip RoadUp editing intent via OpenDRIVE <userData>. CODE_REFERENCE.md S4 and S14."""
from __future__ import annotations

import json
from typing import Any

USERDATA_NS = "roadup"  # <userData code="roadup">{json}</userData>


def encode(payload: dict[str, Any]) -> str:
    """Serialize an editing-intent payload to a compact, stable-ordered JSON string.

    Keys are sorted so a read→edit→write cycle produces byte-stable output (diff-friendly).
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def decode(blob: str) -> dict[str, Any]:
    """Inverse of :func:`encode`."""
    if not blob:
        return {}
    data = json.loads(blob)
    if not isinstance(data, dict):
        raise ValueError("userData payload must decode to a JSON object")
    return data
