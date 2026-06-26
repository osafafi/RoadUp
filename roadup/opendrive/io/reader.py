""".xodr -> model. libOpenDRIVE adapter + pure-Python fallback. CODE_REFERENCE.md S4."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from roadup.opendrive.io.backend import ReaderBackend
    from roadup.opendrive.model.network import OpenDriveModel


class LibOpenDriveReader:
    """.xodr -> model using libOpenDRIVE bindings. Owns all libOpenDRIVE imports."""

    def parse(self, xodr_path: str) -> "OpenDriveModel":
        raise NotImplementedError


class LxmlFallbackReader:
    """Pure-Python, topology-only reader (no native dependency) - used in CI/tests."""

    def parse(self, xodr_path: str) -> "OpenDriveModel":
        raise NotImplementedError


def default_reader() -> "ReaderBackend":
    """Return :class:`LibOpenDriveReader` if importable, else :class:`LxmlFallbackReader`."""
    raise NotImplementedError
