# RoadUp — Build Status

> **Current stage: Stage 4 — Intersections (connectivity + connection splines + junctions)  ·  ✅ complete**
> Last updated: 2026-06-27

**What works right now:** you can **author a junction** where several roads meet —
`roadup.intersections.connectivity.ConnectivitySolver` seeds geometry-aware default movements
(straight/left/right by heading delta, RHT lane pairing), `roadup.intersections.junction_builder.JunctionBuilder`
authors a **connecting road per movement** whose reference line is an **editable
`ConnectionSpline`** — the default is the simplest tangent-honouring connector (`<line>` for
straight-throughs, minimal `<arc>` for symmetric turns, else a tangent-matched cubic Bézier →
`paramPoly3`), and it upgrades to a control-point spline when edited — registers the
`<connection>`/`<laneLink>`, and
`roadup.intersections.surface.IntersectionSurface` meshes the junction surface (connecting-road
ribbons + a fan cap, pure-Python). The writer now **emits `<junction>`** (connecting roads carry the
junction id) and the reader parses it back. Stage 3 still holds: **draw a reference-line `Spline` and
bake it** via `SegmentBuilder` into plan-view geometry + lanes + width laws + road marks from
**external presets** (`presets/*.yaml`); link roads with `network.linkage.LinkResolver`; validate,
write **OpenDRIVE 1.7 `.xodr`**, read it back, and sample reference lines + lane boundaries. The
**showcase golden file** now includes a 4-way junction alongside the drawn-and-baked roads.
**158 tests pass, 0 fail; 12 remain skipped** for not-yet-built modules (Phases 5–7).

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
| **4. Intersections** | `intersections/{connectivity,connection_spline,junction_builder,surface}` ✅; writer/reader `<junction>` ✅ | ✅ |
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

### Phase 4 — Intersections ✅

| Module | Status | Notes |
|---|---|---|
| `intersections/connectivity` | ✅ | `ConnectivitySolver.movements_at`: per-road node contact + travel dir (`road_ends`), heading-delta turn classification (straight/left/right, u-turns dropped), RHT driving-lane pairing inner-to-inner |
| `intersections/connection_spline` | ✅ | `ConnectionSpline`: default = simplest tangent-honouring connector (`<line>` straight / minimal `<arc>` symmetric / tangent-matched cubic Bézier → `paramPoly3` for skew); `add_control_point` upgrades to a Catmull-Rom spline; reuses `segments.builder.bake_reference_line`; `<userData>` payload |
| `intersections/junction_builder` | ✅ | `JunctionBuilder`: connecting road per movement (lane centre from `Sampler.lane_boundaries`), `<connection>`/`<laneLink>`, road+lane links, editable-spline registry, `rebuild_connection` |
| `intersections/surface` | ✅ | `IntersectionSurface`: connecting-road ribbons (`MeshBuilder.ribbon`) + fan cap (`polygon_surface`), pure-Python; boolean union deferred to `blender` (Phase 7) |
| `opendrive/io/writer` | ✅ | now emits `<junction>` + `<connection>`/`<laneLink>`; connecting roads carry the junction id (`road_type`) |
| `opendrive/io/reader` | ✅ | parses `<junction>` back (int road-id → string id map) |

> **Intersection design (Stage 4):** connectivity (which lanes connect) is resolved separately from
> spline *shape* (the path). Default movements are geometry-aware (RHT, UAE-GCC). The default
> connector is the simplest curve honouring both lane-end tangents — line / minimal arc / tangent-
> matched cubic Bézier — since a single arc can't honour two arbitrary tangents (a clothoid/biarc
> fitter is a deferred fidelity upgrade). The connecting road's reference line anchors on the lane's
> **inner edge** (a connecting lane spans one side of its reference line). Editing intent (control
> points) round-trips via `<userData>`; sampled records stay canonical.
> `tests/integration/test_intersection_editing.py` is the gate.

---

## See it / verify locally

```bash
. .venv/Scripts/activate                 # Python 3.12 (see README "Requirements")
pytest -q                                # 158 passed, 12 skipped

# Generate .xodr files to open in an OpenDRIVE visualizer (-> examples/out/, gitignored):
python examples/generate_xodr_samples.py
#   showcase.xodr  + one file per sample road
#   covers line / arc / spiral / paramPoly3, 6 lane types, white+yellow + double marks, a width taper

# Mesh the showcase into .obj for visual topology inspection in Blender (-> examples/out/):
python examples/generate_obj_meshes.py
#   showcase.obj + per-road; each road = <road>_Surface + one <road>_Lane_<id> object (meters, Z-up).
#   Validation harness over the built Sampler + MeshBuilder; the real 3D layer is roadup/usd (Phase 5).
#   tests/integration/test_mesh_export.py is the programmatic mesh-correctness gate.

pytest tests/integration/test_xodr_write.py -s       # prints a generated .xodr to stdout
pytest tests/integration/test_xodr_roundtrip.py -s   # write -> read -> compare topology + userData
ruff check roadup/common roadup/geometry roadup/opendrive roadup/segments roadup/markings roadup/network  # clean
mypy roadup/common roadup/geometry roadup/opendrive roadup/segments roadup/markings roadup/network        # clean

pytest tests/integration/test_segment_creation.py -s     # draw -> bake -> write/read + sampling gate
pytest tests/integration/test_intersection_editing.py -s # build junction -> edit spline -> round-trip
```

> **The showcase is now the author-side "max variations" golden file** (`examples/showcase.py`):
> roads are *drawn and baked* through `segments.SegmentBuilder` + presets (one explicit spiral kept).
> `tests/integration/test_xodr_showcase.py` asserts the variety; `test_xodr_roundtrip.py` proves the
> write→read inverse; `test_segment_creation.py` is the author-side bake-correctness gate.

The 12 skips are placeholder tests for modules in Phases 5–7 (plus `network/spatial` +
`network/snapping`, deferred to Phase 6); each is unskipped and implemented as its module is built.

---

## Next stage (Stage 5 — output & tooling: `usd`, `tooling`)

1. `usd/mapping` + `usd/materials` — prim-path helpers + `roadup:*` id tags; `MaterialLibrary` from
   marking `MaterialParams` (dedup by `material_key`). Consult the **usd-viewport** skill / usd-mcp.
2. `usd/stage` — `StageGenerator`: build the viewport stage from `OpenDriveModel` + `Sampler` (road
   surfaces, lane-edge marking strips, junction surfaces via `intersections.surface`); incremental
   `update_road` / `update_junction`; show the resulting `.usda`.
3. `tooling/{manipulators,hover,commands,controller,preview}` — headless interaction model (no
   `omni.*`): handles, hover policy, undoable commands, the `RoadToolController`.

### Superseded — Stage 4 (intersections) ✅ done

1. `intersections/connectivity` — geometry-aware default movements (turn classification + RHT lane pairing).
2. `intersections/connection_spline` — default arc (or line), editable → `paramPoly3`; `<userData>` round-trip.
3. `intersections/junction_builder` — `Junction` + connecting roads + `<connection>`/`<laneLink>`; rebuild on edit.
4. `intersections/surface` — pure-Python junction surface (ribbons + fan cap).
5. Writer/reader `<junction>` emission + parse; showcase + obj generators gain a 4-way junction.

### Superseded — Stage 3 (authoring) ✅ done

1. `markings/presets` + `segments/presets` — schema + cached YAML loaders.
2. `segments/lane_width` (`WidthLaw` → `<width>` records) + `segments/builder` (`SegmentBuilder` +
   `bake_reference_line`: spline → plan-view geometry + lanes + width records + road marks).
3. `network/{graph,linkage}` — road↔lane link invariant; writer emits `<link>`, reader consumes it.
4. Showcase rebaked as the drawn-and-baked author-side golden file.
