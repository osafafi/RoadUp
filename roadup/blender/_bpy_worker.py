"""Blender-interpreter worker - the ONLY module that imports ``bpy``. CODE_REFERENCE.md S12.

Executed as ``blender --background --python _bpy_worker.py -- <exchange.json>``. Never imported
by the in-process RoadUp code; ``bpy`` is imported inside :func:`main`, not at module top, so the
file stays importable/lint-able by a normal interpreter.
"""
from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    import bpy  # noqa: F401  (only available inside the Blender interpreter)

    # Read the exchange file, perform the requested op (boolean/remesh/decimate), write result.
    raise NotImplementedError


if __name__ == "__main__":
    # Args after the Blender "--" separator.
    sep = sys.argv.index("--") if "--" in sys.argv else len(sys.argv)
    raise SystemExit(main(sys.argv[sep + 1:]))
