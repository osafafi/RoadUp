# RoadUp — Build Status

> **Current stage: Stage 3 — Authoring (segments + markings + network)  ·  ✅ complete**
> Last updated: 2026-06-26

**What works right now:** you can **draw a reference-line `Spline` and bake it** into a road —
`roadup.segments.builder.SegmentBuilder` lowers the spline to plan-view geometry (line/arc, or one
`paramPoly3` per cubic segment) and lays out lanes, width laws (`segments.lane_width.WidthLaw`) and
road marks from **external presets** (`segments.presets` + `markings.presets`, values in
`presets/*.yaml`). Roads are linked with `network.linkage.LinkResolver` (road↔lane link invariant)
and queried with `network.graph.RoadGraph`; the writer now **emits `<link>`** and the reader consumes
it. Everything before still holds: validate the model, write **OpenDRIVE 1.7 `.xodr`**, read it back,
and sample reference lines + lane boundaries. The **showcase is now the author-side "max variations"
golden file** — roads drawn-and-baked (one explicit spiral kept, since a clothoid isn't producible by
cubic-spline baking). **138 tests pass, 0 fail; 17 remain skipped** for not-yet-built modules.

> **Backend note (Stage 2 decision):** read + geometry-eval are **pure-Python** (no native
> libOpenDRIVE). The spiral/clothoid is evaluated by numeric integration; line/arc/paramPoly3 are
> closed-form. `LibOpenDriveReader` stays a stub and `default_reader()` falls back to the lxml
> reader — a native binding can slot in behind `ReaderBackend` later (ARCHITECTURE.md decision 4).

This file is the single source of truth for "where are we". It is part of the
**definition of done**: any change that advances or alters the build updates this file in the same
commit (same rule as keeping ARCHITECTURE.md / CODE_REFERENCE.md in sync).

---

## Phase progress (build order: [ARCHITECTURE.md §15](ARCHITECTURE.md))

Legend: ✅ done · 🚧 in progress · ⬜ not started

| Phase | Scope | Status |
|---|---|---|
| **1. Core model & geometry** | `common`, `geometry`, `opendrive/model` | ✅ |
| **2. OpenDRIVE I/O** | `opendrive/io` (writer ✅, userdata ✅, reader ✅), `opendrive/eval` ✅ | ✅ |
| **3. Authoring** | `segments` ✅, `markings` ✅, `network` (graph+linkage ✅; spatial/snapping → Phase 6) | ✅ |
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

### Phase 2 — OpenDRIVE I/O ✅

| Module | Status | Notes |
|---|---|---|
| `opendrive/io/userdata` | ✅ | stable-order JSON `encode`/`decode` for `<userData code="roadup">` |
| `opendrive/io/writer` | ✅ | `ScenarioGenerationWriter` (sole `scenariogeneration` importer): geometry (line/arc/spiral/paramPoly3), lanes, width laws, road marks, userData → 1.7 `.xodr` |
| `opendrive/io/reader` | ✅ | `LxmlFallbackReader` (pure-Python, CI default) — inverse of the writer; `default_reader()` falls back to it. `LibOpenDriveReader` stub deferred until a binding is pinned |
| `opendrive/io/backend` | ✅ | `ReaderBackend`/`WriterBackend` protocols satisfied |
| `opendrive/eval/planview` | ✅ | **new** — pure-Python plan-view evaluation: line/arc/paramPoly3 closed-form, spiral by numeric integration; `eval_record` + `sample_planview` → frames |
| `opendrive/eval/sampler` | ✅ | `Sampler`: `reference_frames`, `lane_boundaries` (width-law cubic + `geometry/offset`), `road_surface_polylines` |

### Phase 3 — Authoring ✅

| Module | Status | Notes |
|---|---|---|
| `markings/presets` | ✅ | schema + cached YAML loader (`markings.yaml`); `MarkingPreset`/`MaterialParams` |
| `markings/roadmark` | ✅ | preset → `RoadMark` (pattern→type mirrors the writer so it round-trips); line offsets |
| `markings/material` | ✅ | `material_key` (stable dedup key for the USD material library) |
| `segments/presets` | ✅ | schema + cached YAML loader (`road_types.yaml`) → `RoadTypePreset` per `RoadType` |
| `segments/lane_width` | ✅ | `WidthLaw` constant/linear/spline → baked piecewise-cubic `<width>` records |
| `segments/builder` | ✅ | `SegmentBuilder` + `bake_reference_line`: spline → line/arc/`paramPoly3` + lanes + marks |
| `network/linkage` | ✅ | `LinkResolver`: road link + lane link (atomic invariant); default lane map; disconnect/revalidate |
| `network/graph` | ✅ | `RoadGraph`: adjacency from road links + junction siblings |
| `opendrive/io/writer` | ✅ | now emits road + lane `<link>` (contactPoint inferred from the reciprocal link) |

> **Bake path (Stage 3 decision):** a freeform (`bezier`/`catmullRom`) reference line lowers to **one
> `<paramPoly3>` per cubic segment** in its local frame — exact for cubics (sampled geometry traces
> the drawn curve to ~cm; `tests/integration/test_segment_creation.py` is the gate). `line`/`arc`
> splines stay single records. Assumes C1 continuity at joints (true for `catmullRom`).
>
> **Deferred to Phase 6 (interaction-time):** `network/spatial` (AABB index) and `network/snapping`
> remain stubs — they depend on sampled bounds and serve the app/tooling layer.

---

## See it / verify locally

```bash
. .venv/Scripts/activate                 # Python 3.12 (see README "Requirements")
pytest -q                                # 138 passed, 17 skipped

# Generate .xodr files to open in an OpenDRIVE visualizer (-> examples/out/, gitignored):
python examples/generate_xodr_samples.py
#   showcase.xodr  + one file per sample road
#   covers line / arc / spiral / paramPoly3, 6 lane types, white+yellow + double marks, a width taper

pytest tests/integration/test_xodr_write.py -s       # prints a generated .xodr to stdout
pytest tests/integration/test_xodr_roundtrip.py -s   # write -> read -> compare topology + userData
ruff check roadup/common roadup/geometry roadup/opendrive roadup/segments roadup/markings roadup/network  # clean
mypy roadup/common roadup/geometry roadup/opendrive roadup/segments roadup/markings roadup/network        # clean

pytest tests/integration/test_segment_creation.py -s  # draw -> bake -> write/read + sampling gate
```

> **The showcase is now the author-side "max variations" golden file** (`examples/showcase.py`):
> roads are *drawn and baked* through `segments.SegmentBuilder` + presets (one explicit spiral kept).
> `tests/integration/test_xodr_showcase.py` asserts the variety; `test_xodr_roundtrip.py` proves the
> write→read inverse; `test_segment_creation.py` is the author-side bake-correctness gate.

The 17 skips are placeholder tests for modules in Phases 4–7 (plus `network/spatial` +
`network/snapping`, deferred to Phase 6); each is unskipped and implemented as its module is built.

---

## Next stage (Stage 4 — intersections: `intersections/{connectivity,connection_spline,junction_builder,surface}`)

1. `intersections/connectivity` — `ConnectivitySolver`: default movements at a node by geometry + lane type.
2. `intersections/connection_spline` — `ConnectionSpline`: default tangent-matched arc, editable →
   `paramPoly3`; `to_geometry_records()` (reuse `segments.builder.bake_reference_line` / `Spline.circular_arc`).
3. `intersections/junction_builder` — `JunctionBuilder`: build a `Junction` + connecting roads from
   movements; register `<connection>`/`<laneLink>` (writer/reader junction emission as needed).
4. `intersections/surface` — `IntersectionSurface`: junction surface mesh (pure-Python; heavy boolean
   cases delegate to `blender` later).

### Superseded — Stage 3 (authoring) ✅ done

1. `markings/presets` + `segments/presets` — schema + cached YAML loaders.
2. `segments/lane_width` (`WidthLaw` → `<width>` records) + `segments/builder` (`SegmentBuilder` +
   `bake_reference_line`: spline → plan-view geometry + lanes + width records + road marks).
3. `network/{graph,linkage}` — road↔lane link invariant; writer emits `<link>`, reader consumes it.
4. Showcase rebaked as the drawn-and-baked author-side golden file.
