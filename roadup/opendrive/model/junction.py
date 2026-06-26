"""Junction / connection dataclasses. CODE_REFERENCE.md S3."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LaneLinkPair:
    from_lane: int
    to_lane: int


@dataclass
class Connection:
    id: str
    incoming_road: str
    connecting_road: str            # the connecting <road> carrying the connection spline
    contact_point: str = "start"    # "start" | "end"
    lane_links: list[LaneLinkPair] = field(default_factory=list)


@dataclass
class Junction:
    id: str
    name: str = ""
    connections: list[Connection] = field(default_factory=list)
    user_data: dict = field(default_factory=dict)
