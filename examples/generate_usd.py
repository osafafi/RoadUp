"""Generate the USD viewport stage from the showcase model — the Phase 5 output layer.

This drives :class:`roadup.usd.stage.StageGenerator` (the real 3D pipeline, unlike the
``.obj`` validation harness in ``generate_obj_meshes.py``): it samples the OpenDRIVE model and
writes id-tagged ``UsdGeom.Mesh`` surfaces / marking strips / junction patches plus the guide-curve
**Rails**, all under stable ``/RoadNetwork`` paths.

Run from the repo root (with the venv active, ``pxr`` installed)::

    python examples/generate_usd.py

Writes into ``examples/out/`` (gitignored), beside the ``.xodr`` / ``.obj`` files:

* ``showcase.usdc``      — the whole network in one **crate** (binary) layer.
* ``NN_<name>.usdc``     — each road on its own.

**Why crate (``.usdc``) and not ``.usda``:** the generated layer is heavy mesh data — vertices and
face indices for every road surface, lane strip and junction patch. That belongs in a binary crate
layer, not a hand-readable ``.usda``. ``.usda`` is reserved for *small* stages we want to eyeball —
e.g. a future ``*.scene.usda`` that merely **sublayers** one of these crates and adds scatter — which
we don't author here. To audit composition, open a ``.usdc`` with ``usdview`` or run ``usdcat`` on it.

**Units, meters, Z-up** — ``metersPerUnit = 1.0``, ``upAxis = "Z"`` (set by ``StageGenerator``),
matching the ``.xodr`` truth and Omniverse.
"""
from __future__ import annotations

import re
from pathlib import Path

from examples.showcase import build_showcase_model, showcase_roads
from roadup.opendrive.eval.sampler import Sampler
from roadup.opendrive.model.network import OpenDriveModel
from roadup.usd.stage import StageGenerator

OUT_DIR = Path(__file__).parent / "out"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def generate(model: OpenDriveModel, path: Path) -> int:
    """Build the stage for ``model`` and export it to ``path`` (``.usdc`` crate). Returns prim count."""
    generator = StageGenerator(model, Sampler(model))
    stage = generator.build_all()
    generator.export(str(path))
    return sum(1 for _ in stage.Traverse())


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    combined = build_showcase_model()
    combined_path = OUT_DIR / "showcase.usdc"
    prims = generate(combined, combined_path)
    print(f"wrote {combined_path}  "
          f"({len(combined.roads)} roads, {len(combined.junctions)} junctions, {prims} prims)")

    # One crate per road for isolated inspection.
    for i, road in enumerate(showcase_roads(), start=1):
        single = OpenDriveModel()
        single.add_road(road)
        note = road.user_data.get("note", road.id)
        path = OUT_DIR / f"{i:02d}_{_slug(note)}.usdc"
        prims = generate(single, path)
        print(f"wrote {path}  ({note}, {prims} prims)")


if __name__ == "__main__":
    main()
