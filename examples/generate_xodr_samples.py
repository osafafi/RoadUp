"""Write sample .xodr files you can open in an OpenDRIVE visualizer.

Run from the repo root (with the venv active)::

    python examples/generate_xodr_samples.py

Writes into ``examples/out/`` (gitignored):

* ``showcase.xodr``            — all sample roads in one file (side-by-side in +y).
* ``NN_<name>.xodr``          — each road on its own, for isolated inspection.
"""
from __future__ import annotations

import re
from pathlib import Path

from examples.showcase import build_showcase_model, showcase_roads
from roadup.opendrive.io.writer import ScenarioGenerationWriter
from roadup.opendrive.model.network import Header, OpenDriveModel

OUT_DIR = Path(__file__).parent / "out"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    writer = ScenarioGenerationWriter()

    combined = build_showcase_model()
    problems = combined.validate()
    if problems:
        print("validation warnings:")
        for msg in problems:
            print("  -", msg)

    combined_path = OUT_DIR / "showcase.xodr"
    writer.write(combined, str(combined_path))
    print(f"wrote {combined_path}  ({len(combined.roads)} roads)")

    # One file per road for isolated viewing.
    for i, road in enumerate(showcase_roads(), start=1):
        note = road.user_data.get("note", road.id)
        single = OpenDriveModel(header=Header(name=f"RoadUp {note}", version="1.7"))
        single.add_road(road)
        path = OUT_DIR / f"{i:02d}_{_slug(note)}.xodr"
        writer.write(single, str(path))
        print(f"wrote {path}  ({note})")


if __name__ == "__main__":
    main()
