# RoadUp — Build Status

> **Current stage: Stage 5 — USD output & headless tooling  ·  ✅ complete**
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
**showcase golden file** now includes a 5-junction stress gallery (classic 4-way, a complex skewed
4-way with unequal lane counts + mismatched widths, a 2-road bend, a 3-way, and a 5-road star).
**Stage 4.5 adds road elevation + banking and curvature-adaptive meshing** (see below).
**Stage 5 generates the USD viewport stage and the headless tooling layer** (see below).
**223 tests pass, 0 fail; 3 remain skipped** for not-yet-built modules (`blender` → Phase 7;
`network/spatial` + `network/snapping` → Phase 6). The USD tests need `pxr` and `importorskip` it,
so they run where USD is installed and skip cleanly in pure-Python CI.

> **Stage 4.5 (elevation, banking, adaptive sampling):** roads carry an editable **vertical profile**
> (`<elevationProfile>`, `z` along `s`) and **superelevation** (`<lateralProfile>`, bank angle along
> `s`), authored as 1D laws (`segments.vertical_profile.ElevationLaw` / `SuperelevationLaw`, mirroring
> `WidthLaw`) and round-tripped via `<userData>`. `opendrive.eval.elevation.apply_profiles` lifts the
> planar sampled frames into 3D (z + pitched tangent + bank-rolled normal); lateral offsetting and
> meshing then get correct elevation/banking for free. Meshing is now **curvature-adaptive** by
> default (`sample_planview_adaptive`): station density follows the tangent's turn (heading + pitch +
> bank) under an angle/chord threshold, so a straight collapses to two triangles while curves and
> grades densify. `<shape>` (lateral crown) and junction elevation-continuity are deferred.

> **Stage 5 (USD output & headless tooling):** `usd.StageGenerator` builds the viewport stage from
> the model + `Sampler` — road-surface ribbons, lane-edge marking strips, and junction surfaces as
> `UsdGeom.Mesh`, plus per-road **Rails** (centerline + lane-edge `UsdGeom.BasisCurves`,
> `purpose=guide`) tagged with `roadup:*` ids. Every prim sits at a **stable id-keyed path**
> (`usd.mapping`), materials dedup from marking presets (`usd.MaterialLibrary`), and
> `update_road`/`update_junction` regenerate non-destructively. The stage is the **generated layer**:
> sublayer-ready so a `*.scene.usda` can sublayer it and scatter/array along the rails (two-source
> model — ARCHITECTURE.md §9.1). The headless `tooling` layer (no `omni.*`) implements the
> `RoadToolController` (with the `ROAD`/`SCENE` edit-context seam), `HoverModel`, `ManipulatorModel`,
> the undoable `CommandStack` + commands (`MoveControlPoint`, `AddControlPoint`, `SetLaneCount`,
> `SetLaneWidthLaw`, `SetLaneMarking`, `ConnectSegments`), and `PreviewGenerator`. The Kit extension,
> the scatter/array tools, and the toggle UI are Phase 6+.

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
| **4.5 Elevation & adaptive mesh** | `opendrive/eval/elevation`, `segments/vertical_profile`, adaptive `planview`; writer/reader profiles ✅ | ✅ |
| **5. Output & tooling** | `usd` ✅ (mapping/materials/stage + guide-curve Rails), `tooling` ✅ (controller/hover/manipulators/commands/preview + `ROAD`/`SCENE` seam) | ✅ |
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

### Phase 4.5 — Elevation, banking & curvature-adaptive sampling ✅

| Module | Status | Notes |
|---|---|---|
| `opendrive/model/road` | ✅ | `ElevationRecord` + `SuperelevationRecord` (cubic in `ds`); `Road.elevation` / `Road.superelevation` (empty ⇒ flat ⇒ unchanged output) |
| `opendrive/eval/elevation` | ✅ | `eval_elevation`/`_slope`/`eval_superelevation`; `apply_profiles` lifts frames to 3D (z + pitched tangent + Rodrigues bank-rolled normal); `vertical_angle_fn` feeds adaptive refinement; identity when flat |
| `opendrive/eval/planview` | ✅ | `sample_planview_adaptive`: angle-threshold + chord-error + min/max-step station picking; folds in `vertical_angle` (pitch+bank); densifies under-resolved straights so vertical curves refine. Uniform `sample_planview` retained |
| `opendrive/eval/sampler` | ✅ | adaptive by default (`adaptive=True`, `config`-driven); `adaptive=False` keeps the fixed grid; `reference_frames` applies profiles after sampling |
| `segments/vertical_profile` | ✅ | `ElevationLaw` / `SuperelevationLaw` (constant/linear/spline → records), mirroring `WidthLaw`; constructors `grade`/`crest`/`ramp` |
| `segments/builder` | ✅ | `with_elevation` / `with_superelevation`; bakes records + round-trips the laws in `<userData>` |
| `opendrive/io/writer` | ✅ | emits `<elevationProfile>` / `<lateralProfile>` via `scenariogeneration` `add_elevation`/`add_superelevation` (skipped when empty) |
| `opendrive/io/reader` | ✅ | parses both profiles back (was silently dropped) |
| `common/config` | ✅ | adaptive knobs: `adaptive_max_angle_deg`, `adaptive_chord_tol`, `adaptive_min_step`, `adaptive_max_step` |

> **Stage 4.5 design:** OpenDRIVE separates vertical (`z(s)`) from lateral (bank `α(s)`) profiles, so
> RoadUp authors each as its own 1D law (not from the reference-line spline z) and bakes to cubic
> records — same pattern as lane width laws, so it round-trips losslessly via `<userData>` and is
> ready for viewport elevation handles (Stage 6). Sampling moved from a fixed step to a
> curvature-adaptive station picker driven by an **angle threshold** (heading + elevation pitch +
> bank), so a flat straight is two triangles and curves/grades refine only where needed.
> `tests/integration/test_xodr_roundtrip.py` (profiles survive) + `test_mesh_export.py` (adaptive
> counts, 3D mesh) are the gates. Deferred: `<lateralProfile><shape>` (lane crown) and junction
> elevation continuity.

### Phase 5 — USD output & headless tooling ✅

| Module | Status | Notes |
|---|---|---|
| `usd/mapping` | ✅ | pure-Python (no `pxr`): stable id-keyed prim paths + rail/marking helpers; `resolve_prim` reads `roadup:*` tags |
| `usd/materials` | ✅ | `MaterialLibrary`: UsdPreviewSurface from `MaterialParams`, dedup by `material_key`; `asphalt()` default |
| `usd/stage` | ✅ | `StageGenerator`: surfaces + marking strips + junction surfaces as `Mesh`; **guide-curve Rails** (centerline + lane edges); incremental `update_road`/`update_junction`; `export`/`to_usda` |
| `tooling/manipulators` | ✅ | `Handle` + `ManipulatorModel.set_handles` (keeps live selection/hover) |
| `tooling/hover` | ✅ | `HoverModel`: road/junction → control-point handles; selection-pinned merge |
| `tooling/commands` | ✅ | `CommandStack` (undo/redo) + `Move`/`Add` control point, `SetLaneCount`/`WidthLaw`/`Marking`, `ConnectSegments` |
| `tooling/controller` | ✅ | `RoadToolController` + `ROAD`/`SCENE` `EDIT_CONTEXTS` seam; drag→`MoveControlPoint`→scoped regen |
| `tooling/preview` | ✅ | `PreviewGenerator`: low-res centerline guide curve on a throwaway stage |

> **Stage 5 design:** USD is the **generated layer** — derived, regenerated, never hand-edited, with
> stable id-keyed paths so a `*.scene.usda` can **sublayer** it and author the scene beside it
> (scatter/props/env), riding the guide-curve **Rails**. One-way dependency, no sync (ARCHITECTURE.md
> §9.1). `pxr` is imported lazily and the USD tests `importorskip` it, keeping the core pure-Python.
> `tests/integration/test_usd_generation.py` is the gate: tags, guide rails, path stability across
> regeneration, and scene-sublayer composition.

---

## See it / verify locally

```bash
. .venv/Scripts/activate                 # Python 3.12 (see README "Requirements")
pytest -q                                # 223 passed, 3 skipped (USD tests need `pxr`; importorskip otherwise)

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

The 3 skips are placeholder tests for `blender` (Phase 7) and `network/spatial` + `network/snapping`
(deferred to Phase 6); each is unskipped and implemented as its module is built. The USD unit +
integration tests `importorskip("pxr")`, so they run where USD is installed and skip in pure-Python CI.

---

## Next stage (Stage 6 — Omniverse Kit app: `app/exts/roadup.tool`)

The headless `usd` + `tooling` layers are done; Stage 6 is the **only** place `omni.*`/`carb.*` are
imported. It binds the viewport to the controller and renders its state — no new authoring logic.

**Host app (decided — ARCHITECTURE.md §10).** RoadUp ships the **extension**, not the app. Generate
the runnable host **fresh** from `kit-app-template` (`repo template new` → **`kit_base_editor`**,
Kit 110.1) in a **separate sibling repo** — don't vendor the template into this repo, don't reuse the
old project's app shell. The host adds `app/exts/` to its ext search path, makes `roadup` importable
by Kit's Python, and enables `roadup.tool`. Step 0 of this stage is creating that host.

1. `extension.py` — `omni.ext.IExt`: load/attach the `OpenDriveModel`, build `StageGenerator`, create
   `RoadToolController(model, stage)`, wire input/render, register panels. Consult **kit-dev-mcp**.
2. `viewport_input.py` — cursor move/click/drag → hit-test → `usd.mapping.resolve_prim` → forward to
   the controller; render `controller.manipulators()` via `manipulator_view.py` (`omni.ui.scene`).
3. `panels.py` — `omni.ui` panels (lane count, marking/road-type presets) issuing tooling commands;
   add the **ROAD / SCENE toggle** that drives `controller.set_context`. Consult **ui-kit-mcp**.

Then the **scene-authoring** stage builds the scatter/array tools that ride the guide-curve Rails
inside the `*.scene.usda` layer (ARCHITECTURE.md §9.1) — `PointInstancer` along a rail, etc.

> Stage 5 already consumes the 3D sampled frames directly, so road surfaces, lane strips and junction
> patches inherit elevation + banking with no extra work in `usd/`; the rails carry that 3D shape too.

### Superseded — Stage 4.5 (elevation, banking, adaptive mesh) ✅ done

1. `opendrive/model/road` — `ElevationRecord` / `SuperelevationRecord` + `Road` fields.
2. `opendrive/eval/elevation` — profile eval + `apply_profiles` (3D frames) + `vertical_angle_fn`.
3. `opendrive/eval/planview` — `sample_planview_adaptive` (angle/chord-driven); `sampler` adaptive default.
4. `segments/vertical_profile` + `segments/builder` — editable laws, baked + `<userData>` round-trip.
5. Writer/reader `<elevationProfile>` / `<lateralProfile>`; showcase gains a climbing, banked curve.

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
