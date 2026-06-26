"""Reader/Writer adapter contracts (keeps native libs swappable). CODE_REFERENCE.md S4."""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from roadup.opendrive.model.network import OpenDriveModel


class ReaderBackend(Protocol):
    """A .xodr reader (libOpenDRIVE default; pure-Python fallback for CI)."""

    def parse(self, xodr_path: str) -> OpenDriveModel: ...


class WriterBackend(Protocol):
    """A model -> .xodr writer (scenariogeneration default)."""

    def write(self, model: OpenDriveModel, xodr_path: str) -> None: ...
