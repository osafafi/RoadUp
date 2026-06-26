# RoadUp — Build Status

> **Current stage: Stage 1 — Foundation + first `.xodr`  ·  ✅ complete**
> Last updated: 2026-06-26

**What works right now:** you can author a road network in code with the pure-Python model
(`roadup.opendrive.model`), validate it, and write a valid **OpenDRIVE 1.7 `.xodr`** via
`roadup.opendrive.io.writer.ScenarioGenerationWriter`. Editing intent round-trips through
`<userData code="roadup">`. The geometry math foundation (splines, sampling, offset, mesh) is in
place. **65 tests pass, 0 fail; 30 remain skipped** for not-yet-built modules.

This file is the single source of truth for "where are we". It is part of the
**definition of done**: any change that advances or alters the build updates this file in the same
commit (same rule as keeping ARCHITECTURE.md / CODE_REFERENCE.md in sync).

---

## Phase progress (build order: [ARCHITECTURE.md §15](ARCHITECTURE.md))

Legend: ✅ done · 🚧 in progress · ⬜ not started

| Phase | Scope | Status |
|---|---|---|
| **1. Core model & geometry** | `common`, `geometry`, `opendrive/model` | ✅ |
| **2. OpenDRIVE I/O** | `opendrive/io` (writer ✅, userdata ✅, reader ⬜), `opendrive/eval` ⬜ | 🚧 |
| **3. Authoring** | `segments`, `markings`, `network` | ⬜ |
| **4. Intersections** | `intersections/{connectivity,connection_spline,junction_builder,surface}` | ⬜ |
| **5. Output & tooling** | `usd`, `tooling` | ⬜ |
| **6. Omniverse app** | `app/exts/roadup.tool` | ⬜ |
| **7. Optional acceleration** | `blender` | ⬜ |

### Phase 1 — Core model & geometry ✅

| Module | Status | Notes |
|---|---|---|
| `common/types` · `common/errors` | ✅ | enums + error hierarchy (scaffold) |
| `common/ids` | ✅ | `make_id` / `parse_id` / `IdAllocator` (zero-padded, signed) |
| `common/units` | ✅ | `kmh_to_ms`, `deg_to_rad`, `grade_percent` |
| `common/config` | ✅ | `Config`, `resolve_presets_dir` (override → env → repo `presets/`) |
| `geometry/splines` | ✅ | `Spline` line/catmullRom/bezier/arc; evaluate/tangent/curvature/length/sample; edit ops; `circular_arc` |
| `geometry/sampling` | ✅ | `Frame`, `sample_frames`, `resample_by_arclength` (+t = left-of-tangent) |
| `geometry/offset` | ✅ | `offset_polyline`, `lane_boundary` |
| `geometry/mesh` | ✅ | `MeshData` merge/manifold; `MeshBuilder` ribbon/extrude/polygon_surface |
| `opendrive/model/road` | ✅ | dataclasses + `LaneSection.lane/lane_ids`, `Road.lane_section_at` |
| `opendrive/model/junction` | ✅ | dataclasses (junction *building* is Phase 4) |
| `opendrive/model/network` | ✅ | `OpenDriveModel` add/get/remove/validate |

### Phase 2 — OpenDRIVE I/O 🚧

| Module | Status | Notes |
|---|---|---|
| `opendrive/io/userdata` | ✅ | stable-order JSON `encode`/`decode` for `<userData code="roadup">` |
| `opendrive/io/writer` | ✅ | `ScenarioGenerationWriter` (sole `scenariogeneration` importer): geometry (line/arc/spiral/paramPoly3), lanes, width laws, road marks, userData → 1.7 `.xodr` |
| `opendrive/io/reader` | ⬜ | libOpenDRIVE + lxml fallback → **Stage 2** |
| `opendrive/io/backend` | ⬜ | protocols defined; reader impls pending |
| `opendrive/eval/sampler` | ⬜ | model → frames/lane boundaries → **Stage 2** |

> Road/lane **linking** is authored in Phase 3 (`network`); the writer does not yet emit `<link>`
> for cross-road predecessors/successors.

---

## See it / verify locally

```bash
. .venv/Scripts/activate                 # Python 3.12 (see README "Requirements")
pytest -q                                # 69 passed, 30 skipped

# Generate .xodr files to open in an OpenDRIVE visualizer (-> examples/out/, gitignored):
python examples/generate_xodr_samples.py
#   showcase.xodr  + one file per sample road
#   covers line / arc / spiral / paramPoly3, 6 lane types, white+yellow + double marks, a width taper

pytest tests/integration/test_xodr_write.py -s   # prints a generated .xodr to stdout
ruff check roadup/common roadup/geometry roadup/opendrive   # clean
mypy roadup/common roadup/geometry roadup/opendrive         # clean
```

> **Toward the full "max variations" golden file:** `examples/showcase.py` already exercises every
> geometry primitive the writer supports. Authoring those by *drawing a `geometry.Spline` and baking
> it* (spline → plan-view records + width laws from marking presets) lands with
> `segments.SegmentBuilder` in **Phase 3** — that's when the showcase becomes the canonical
> author-side max-variation test rather than hand-authored records.

The 30 skips are placeholder tests for modules in Phases 2–7; each is unskipped and implemented as
its module is built.

---

## Next stage (Stage 2 — read & round-trip)

1. `opendrive/io/reader` — `LxmlFallbackReader` (pure-Python, CI-safe) then `LibOpenDriveReader`.
2. `opendrive/eval/sampler` — sample reference frames + lane boundaries from the model.
3. Unskip `tests/integration/test_xodr_roundtrip.py`: write → read → compare topology + userData.
