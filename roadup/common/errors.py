"""Error hierarchy for RoadUp. CODE_REFERENCE.md S1."""
from __future__ import annotations


class RoadError(Exception):
    """Base class for all RoadUp errors."""


class ValidationError(RoadError):
    """Model failed a validation invariant."""


class GeometryError(RoadError):
    """Geometric operation could not be completed (degenerate input, cusp, etc.)."""


class TopologyError(RoadError):
    """Inconsistent road/lane connectivity."""


class OpenDriveIOError(RoadError):
    """Reading or writing a .xodr failed."""


class IntersectionError(RoadError):
    """Junction authoring or surface generation failed."""


class USDError(RoadError):
    """USD stage authoring failed."""
