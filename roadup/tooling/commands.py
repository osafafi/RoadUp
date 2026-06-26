"""Undoable commands; each mutates the model then triggers scoped regeneration. CODE_REFERENCE.md S11."""
from __future__ import annotations

from typing import Protocol


class Command(Protocol):
    def do(self) -> None: ...
    def undo(self) -> None: ...


class CommandStack:
    def execute(self, cmd: Command) -> None:
        raise NotImplementedError

    def undo(self) -> None:
        raise NotImplementedError

    def redo(self) -> None:
        raise NotImplementedError


# Concrete commands (implemented in the build session). Each edits the OpenDRIVE model and
# requests regeneration of only the affected roads/junctions.
class MoveControlPoint:
    def do(self) -> None: raise NotImplementedError
    def undo(self) -> None: raise NotImplementedError


class AddControlPoint:
    def do(self) -> None: raise NotImplementedError
    def undo(self) -> None: raise NotImplementedError


class SetLaneCount:
    def do(self) -> None: raise NotImplementedError
    def undo(self) -> None: raise NotImplementedError


class SetLaneWidthLaw:
    def do(self) -> None: raise NotImplementedError
    def undo(self) -> None: raise NotImplementedError


class SetLaneMarking:
    def do(self) -> None: raise NotImplementedError
    def undo(self) -> None: raise NotImplementedError


class ConnectSegments:
    def do(self) -> None: raise NotImplementedError
    def undo(self) -> None: raise NotImplementedError
