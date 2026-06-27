"""Generate flat, Pylance-resolvable ``.pyi`` stubs for ``pxr`` by live introspection.

OpenUSD ships **no** type stubs, and each ``pxr`` submodule populates its namespace at
import time via ``Tf.PreparePythonModule()`` -- a runtime injection a static analyzer
(Pylance/pyright) cannot see, which is why ``UsdGeom.Mesh`` shows up as "not recognized"
with no completion. ``stubgen`` also fails here because the boost-python C extensions
don't expose PEP-style signatures.

This script imports each submodule (running the injection) and emits one flat
``__init__.pyi`` per submodule listing classes (with member names) and module-level
functions. Signatures are intentionally shallow (``*args, **kwargs``) -- enough to make
the API "recognized" and give member-name autocomplete. It is **not** a substitute for
the real signatures; consult the usd-mcp server for exact call signatures.

Usage (after ``pip install -e ".[usd]"`` so ``pxr`` is importable)::

    python tools/gen_pxr_stubs.py

Writes to ``<repo>/typings/pxr`` (gitignored; Pylance reads ``./typings`` by default).
Re-run whenever the pinned ``usd-core`` version changes so the stubs track the runtime.
"""
from __future__ import annotations

import importlib
import inspect
import os
import pkgutil
import shutil

import pxr

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_ROOT = os.path.join(REPO_ROOT, "typings", "pxr")

shutil.rmtree(OUT_ROOT, ignore_errors=True)
os.makedirs(OUT_ROOT, exist_ok=True)

submods = sorted(
    name for _, name, _ in pkgutil.iter_modules(pxr.__path__) if not name.startswith("_")
)

# Package __init__.pyi re-exports every submodule so ``from pxr import UsdGeom`` resolves.
with open(os.path.join(OUT_ROOT, "__init__.pyi"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(f"from . import {m} as {m}" for m in submods) + "\n")

generated = 0
for m in submods:
    try:
        mod = importlib.import_module(f"pxr.{m}")
    except Exception:
        continue

    lines: list[str] = ["from typing import Any", ""]
    for name, obj in sorted(vars(mod).items(), key=lambda kv: kv[0]):
        if name.startswith("_"):
            continue
        if inspect.isclass(obj):
            body: list[str] = []
            for member in sorted(dir(obj)):
                if member.startswith("__"):
                    continue
                try:
                    attr = inspect.getattr_static(obj, member)
                except Exception:
                    try:
                        attr = getattr(obj, member)
                    except Exception:
                        continue
                if isinstance(attr, staticmethod):
                    body.append("    @staticmethod")
                    body.append(f"    def {member}(*args: Any, **kwargs: Any) -> Any: ...")
                elif callable(attr):
                    body.append(f"    def {member}(self, *args: Any, **kwargs: Any) -> Any: ...")
                else:
                    body.append(f"    {member}: Any")
            lines.append(f"class {name}:")
            lines.extend(body or ["    ..."])
            lines.append("")
        elif callable(obj):
            lines.append(f"def {name}(*args: Any, **kwargs: Any) -> Any: ...")
        else:
            lines.append(f"{name}: Any")

    moddir = os.path.join(OUT_ROOT, m)
    os.makedirs(moddir, exist_ok=True)
    with open(os.path.join(moddir, "__init__.pyi"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    generated += 1

print(f"Generated pxr stubs for {generated} submodules under {OUT_ROOT}")
