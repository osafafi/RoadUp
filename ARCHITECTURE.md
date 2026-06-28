# RoadUp — Architecture Document

**Version:** 2.1.0
**Date:** 2026-06-26
**Status:** Foundation / Ready for Scaffolding
**Owner:** Architecture-first build team

> This document describes **architecture only** — responsibilities, boundaries, data flow, and
> decisions. All illustrative code (class skeletons, interface signatures, schema fragments, preset
> tables) lives in the companion **[CODE_REFERENCE.md](CODE_REFERENCE.md)**. Keep this file lean.

---

## 1. Project Vision

Build a **pure-Python, OpenDRIVE-native** procedural road authoring system that replicates the
interaction model of Cities: Skylines road tools, presented through an **Omniverse Kit App**.

The **OpenDRIVE (`.xodr`) network is the single source of truth** for all road logic and topology.
Geometry for the viewport is *generated* from that model into a USD stage that Omniverse renders.
Editing in the viewport mutates the OpenDRIVE model and regenerates the affected geometry.

```
            authoring / editing
   .xodr  <───────────────────────>  Core Model (Python)  ──generate──>  USD stage  ──>  Omniverse viewport
 (truth)        read / write                                 (output)                       (render + input)
```

### Key Principles

- **OpenDRIVE is the source of truth.** Network semantics (roads, lanes, lane widths, road marks,
  junctions, lane links) live in the OpenDRIVE model and serialize to `.xodr`. USD is a derived
  output, never the authority.
- **Pure-Python core.** All backend logic is Python. Native/third-party libraries (read/eval,
  Blender, Omniverse) sit behind thin adapters so the core stays portable and unit-testable.
- **Lean on proven libraries.** We do **not** re-implement OpenDRIVE serialization or curve math:
  `scenariogeneration` writes `.xodr`; **libOpenDRIVE** reads and evaluates geometry. Each is wrapped
  by an adapter we own.
- **Modular & decoupled.** Every system and tool is a self-contained package with a narrow public
  interface and its **own co-located unit tests**. No module reaches across another's internals.
- **Headless core, thin UI.** Interaction *logic* (hover, selection, control-point editing, tool
  modes) is headless and testable. The Omniverse layer only binds input/rendering to that logic.
- **Procedural, not baked.** Geometry is regenerated from the OpenDRIVE model; the model is the only
  thing that is persisted and edited.
- **Editable everywhere it matters.** Reference lines, lane width laws, and intersection connection
  splines are all control-point editable; the standard `.xodr` records are produced from them.

---

## 2. System Overview

```
+=============================================================================+
|                       OMNIVERSE KIT APP  (the only UI)                      |
|                                                                             |
|   +-------------------+   +----------------------+   +------------------+   |
|   |  Viewport Input   |   |  Manipulator View    |   |   UI Panels      |   |
|   | hover / click /   |   | control points for   |   | lane count,      |   |
|   | drag / pick       |   | nodes & spline pts   |   | markings, presets|   |
|   +---------+---------+   +-----------+----------+   +---------+--------+   |
|             |                         |                        |            |
|             +------------+------------+------------------------+            |
|                          v  (events in / manipulator state out)            |
+==========================+==================================================+
                           |
+--------------------------+--------------------------------------------------+
|                  TOOLING  (headless, UI-agnostic interaction)               |
|   RoadToolController · HoverModel · ManipulatorModel · Preview · Commands    |
+--------------------------+--------------------------------------------------+
                           |
+--------------------------+--------------------------------------------------+
|                          CORE  (pure Python)                                |
|                                                                             |
|  +-----------------------------------------------------------------------+  |
|  |  OPENDRIVE  (source of truth)                                         |  |
|  |    model/   thin dataclasses: Road · LaneSection · Lane · LaneWidth   |  |
|  |             RoadMark · Junction · Connection · LaneLink               |  |
|  |    io/      reader (lxml pure-Python; libOpenDRIVE deferred) ·        |  |
|  |             writer (scenariogeneration) · userdata (<userData>)       |  |
|  |    eval/    planview (pure-Python record eval) + sampler:             |  |
|  |             ref-line frames, lane boundaries                          |  |
|  +-----------------------------------+-----------------------------------+  |
|         |               |            |               |              |        |
|  +------+----+  +-------+-----+  +---+--------+  +---+--------+  +--+-----+   |
|  | network   |  | segments    |  | markings   |  |intersect-  |  |geometry|  |
|  | graph ·   |  | lane count· |  | presets ·  |  |ions        |  | splines|  |
|  | spatial · |  | width laws ·|  | dims ·     |  | junction · |  | offset |  |
|  | linkage · |  | presets     |  | materials  |  | conn-spline|  | mesh   |  |
|  | snapping  |  |             |  |            |  | surface    |  |        |  |
|  +-----------+  +-------------+  +------------+  +------------+  +--------+   |
+--------------------------+-----------------------------+---------------------+
                           |                             |
+--------------------------+--------+        +-----------+-------------------+
|  USD OUTPUT  (generated)          |        |  BLENDER  (optional, isolated) |
|   stage · prim<->id mapping ·     |        |   MeshProcessor adapter, used  |
|   materials (from presets)        |        |   only for heavy mesh ops      |
+--------------------------+--------+        +--------------------------------+
                           |
                     +-----+------+
                     | USD stage  |  -> Omniverse Hydra render
                     +------------+
```

Dependencies point **downward and inward**. The Omniverse layer depends on Tooling; Tooling depends
on Core; nothing in Core depends on Tooling, USD, or Omniverse.

---

## 3. Architecture Layers & The Editing Loop

There are four layers. Each only knows about the layer directly beneath it.

| Layer | Packages | Knows about | Never imports |
|-------|----------|-------------|---------------|
| **App (UI)** | `app/` (Kit extension) | Tooling | — |
| **Tooling** | `tooling/` | Core packages, USD output | `omni.*`, `carb.*` |
| **Core** | `opendrive/`, `network/`, `segments/`, `markings/`, `intersections/`, `geometry/` | each other (narrowly), `common/` | `tooling/`, `usd/`, `app/`, `omni.*` |
| **Output / Accel** | `usd/`, `blender/` | Core models, `geometry/` | `tooling/`, `app/` |

### The editing loop (the heart of the system)

```
1. Input        Omniverse viewport: cursor move / click / drag
2. Hit-test     usd.mapping resolves the hovered prim -> OpenDRIVE element id (road/lane/junction/handle)
3. Hover        tooling.HoverModel decides which control points (node handles, spline points) are visible
4. Edit         user drags a control point -> tooling issues a Command
5. Mutate       Command edits the OpenDRIVE model (e.g. move a connection-spline control point)
6. Resample     opendrive.eval re-samples only the affected roads/junctions
7. Regenerate   usd.stage rebuilds only the affected prims (geometry adapts)
8. Persist      on save, opendrive.io writes .xodr (editing intent preserved via <userData>)
```

Steps 5–7 are incremental: a single edit touches one road or one junction, not the whole network.

---

## 4. Module Map

Each row is a self-contained package with co-located unit tests (`<package>/tests/`).
Detailed interfaces are in [CODE_REFERENCE.md](CODE_REFERENCE.md) under the matching section.

| Package | Responsibility | Key external deps | Pure Python? |
|---------|----------------|-------------------|--------------|
| `common/` | Shared enums, dataclasses, IDs, units, error hierarchy, config loading. | — | Yes |
| `geometry/` | Editable control-point splines, curve sampling, lateral offset, `MeshData` + builders, Delaunay polygon fill (`triangulate`). | numpy | Yes |
| `opendrive/model/` | Thin dataclasses mirroring OpenDRIVE 1.x elements (the source-of-truth model). | — | Yes |
| `opendrive/io/` | `.xodr` read (pure-Python lxml default; libOpenDRIVE adapter deferred) and write (scenariogeneration adapter); `<userData>` round-trip. | scenariogeneration, lxml, (libOpenDRIVE) | Adapter-isolated |
| `opendrive/eval/` | Pure-Python plan-view eval (`planview`: line/arc/paramPoly3 closed-form, spiral integrated) + `sampler`: ref-line frames and lane boundary polylines for meshing. A native libOpenDRIVE path can replace eval behind the same surface. | numpy, (libOpenDRIVE) | Adapter-isolated |
| `network/` | Topology graph, spatial index, snapping queries, and **road↔lane link resolution**. | numpy | Yes |
| `segments/` | Author a road: lane count, lane types, **lane width laws along length**, road-type presets (loaded from external `presets/road_types.yaml`). | pyyaml | Yes |
| `markings/` | Road-mark model + **presets** (continuous / dashed / double, dimensions, material params) loaded from external `presets/markings.yaml`. | pyyaml | Yes |
| `intersections/` | Junction authoring, **editable connection splines**, lane connectivity, surface generation. | numpy | Yes |
| `usd/` | Generate/update the USD viewport stage; map prims ↔ OpenDRIVE ids; build materials from presets. | pxr (USD) | Adapter-isolated |
| `tooling/` | Headless interaction: tool modes, hover/selection state, manipulator model, preview, command/undo. | — | Yes |
| `blender/` | Optional, isolated headless Blender adapter for heavy mesh ops, behind a `MeshProcessor` interface. | bpy (optional) | Adapter-isolated |
| `app/` | Omniverse Kit extension: viewport input, manipulator rendering, UI panels. Binds input/render to Tooling. | omni.*, carb.* | No (UI) |

**Self-containment rules**

1. A package's public surface is what it exports from its `__init__.py`. Other packages import only
   that surface.
2. Native or framework dependencies (`scenariogeneration`, `libOpenDRIVE`, `pxr`, `bpy`, `omni.*`)
   appear **only** inside their owning package's adapter, never in `common/`, `geometry/`,
   `network/`, `segments/`, `markings/`, `intersections/`, or `tooling/`.
3. Each package ships `tests/` next to its code. A package's unit tests must run without importing
   any sibling package's internals (use `common/` fixtures or local fakes).

---

## 5. OpenDRIVE Mapping (Source of Truth)

Our concepts map directly onto ASAM OpenDRIVE elements. We add nothing the standard cannot express
except *editing intent*, which is preserved in `<userData>`.

| RoadUp concept | OpenDRIVE element | Notes |
|----------------|-------------------|-------|
| Road segment | `<road>` + `<planView>` reference-line geometry | Geometry = `line` / `arc` / `spiral` / `poly3` / `paramPoly3`. |
| Reference line (editable) | a control-point spline → serialized geometry records | Default straight/arc; extra control points → `paramPoly3`. |
| Lane count & layout | `<laneSection>` with `<left>/<center>/<right>` `<lane>` | Multiple lane sections allow the count to change along the road. |
| **Lane width along length** | one or more `<width sOffset a b c d>` per lane | A piecewise cubic *width law*; multiple records vary width along `s`. |
| **Road elevation (z along s)** | `<elevationProfile><elevation s a b c d>` | A piecewise cubic *vertical profile law*; absent ⇒ flat (`z=0`). |
| **Road banking (superelevation)** | `<lateralProfile><superelevation s a b c d>` | A piecewise cubic *bank-angle law* (radians); rolls the cross-section about the reference line. `<shape>` (lane crown) deferred. |
| Lane type | `<lane type=...>` | vehicle / sidewalk / biking / parking / shoulder / etc. |
| **Road markings** | `<roadMark>` (+ `<type>/<line>` for dashes) | type (solid/broken/solid-solid…), weight, color, width, dash length/space. |
| Marking **material** | `<userData>` on the road mark (preset id) | OpenDRIVE has no material model; the USD layer resolves the preset → material. |
| Segment connection | `<road><link><predecessor>/<successor>` | Road-level link. |
| **Lane connection** | `<lane><link><predecessor>/<successor>` and junction `<laneLink>` | Lane-level link, kept consistent with the road link (see §8). |
| Intersection | `<junction>` + connecting `<road>`s | Each connection is a connecting road. |
| **Connection spline (editable)** | connecting road `<planView>` geometry | Default `arc` (circular); add control points → `paramPoly3`. |
| Editing intent (handles, presets) | `<userData>` payloads | Round-trips our control points / preset choices that aren't native to OpenDRIVE. |

**Why a thin model of our own (and not the libraries' objects):** `scenariogeneration` is
write-optimized and libOpenDRIVE is read/eval-optimized; neither is a round-trippable editing model.
We keep a small neutral dataclass model that both adapters convert to/from, so reading, editing, and
writing share one representation. See [CODE_REFERENCE.md §3](CODE_REFERENCE.md).

---

## 6. Intersections & Editable Connection Splines

This is the most distinctive requirement and drives the intersection design.

- A junction is built from the incoming roads at a node. For every permitted movement, a **connecting
  road** is authored whose reference line is the **connection spline**.
- **Default shape:** when two lanes are first connected, the connection spline is a **basic circular
  curve** (a single `arc`, tangent-matched to the incoming and outgoing lane directions).
- **Editable shape:** the user can **add control points** to a connection spline and drag them. The
  spline upgrades from the implicit arc to an explicit control-point curve (Bézier/Catmull-Rom in
  `geometry/`), serialized to OpenDRIVE as `paramPoly3` (one or more records).
- **Geometry adapts:** the connecting road's lanes follow the edited reference line; the
  intersection **surface** is regenerated. Move a control point → resample that connecting road →
  rebuild the junction surface patch. No other junction is affected.
- **Junction surface = capped boundary loop** (`intersections/boundary` + `surface`), *not* a blind
  union of connecting-road ribbons (that double-stacks a vertex on every shared edge). Each **node
  road** contributes its drivable end-cross-section (two corner vertices); angularly-adjacent roads
  are bridged by an **editable corner fillet** — a cubic Bézier tangent to each road's edge, curving
  *inward* (concave, toward the junction centre — the classic rounded corner), handle length sized
  to a true circular arc of the corner angle. The ring (end-edges + sampled fillets, every vertex once)
  is capped to one watertight mesh — by default a **Delaunay fill** (`geometry/triangulate`) that
  scatters interior Steiner points (`Config.junction_cap_interior_spacing`) for near-isotropic
  triangles, not a stretchy centroid fan. Corner handles are editable in the viewport (Stage 6); only
  *edited* handles persist, as offsets from their geometry-derived endpoints, under
  `junction.user_data["boundary"]` so a read → edit → write cycle round-trips.
- **Lane connectivity** (which incoming lane connects to which outgoing lane) is resolved separately
  from spline *shape*; connectivity defines *which* connecting roads exist, the spline defines their
  *path*. See [CODE_REFERENCE.md §9](CODE_REFERENCE.md).

Editing intent (the user-added control points and tangents) is stored in `<userData>` on the
connecting road so it round-trips; the sampled `paramPoly3` is what other OpenDRIVE consumers read.

---

## 7. Lanes, Widths & Markings

**Lane count.** Authored per `<laneSection>`. Changing the count along a road adds a new lane section
at the `s` where the change occurs. Presets (per road type) seed a sensible default count and layout.

**Lane width along length.** Each lane carries a **width law**: a list of `<width>` records, each a
cubic `a + b·ds + c·ds² + d·ds³` valid from an `sOffset`. The authoring layer exposes this as an
editable law (constant, linear taper, or control-point curve) and bakes it to `<width>` records.

**Road elevation & banking.** A road carries a **vertical profile** (`z` along `s`) and a
**superelevation** (bank angle along `s`), each authored as the *same* kind of 1D law as lane width
(`segments.vertical_profile.ElevationLaw` / `SuperelevationLaw`: constant / linear / control-point
spline) and baked to `<elevationProfile><elevation>` / `<lateralProfile><superelevation>` cubic
records. They are authored independently of the plan-view spline — matching OpenDRIVE's own
separation of horizontal, vertical, and lateral geometry — and round-trip via `<userData>`. The
sampler (`opendrive.eval.elevation.apply_profiles`) lifts the planar station frames into 3D (sets
`z`, pitches the tangent by the elevation slope, rolls the +t normal by the bank angle), so lateral
offsetting and meshing inherit elevation + banking with no further work. Sampling is
**curvature-adaptive**: station density tracks the tangent's turn (heading + pitch + bank), collapsing
straights to two triangles while refining curves and grades. `<lateralProfile><shape>` (per-lane
crown) and junction elevation-continuity are deferred.

**Road markings (presets for now).** A marking preset bundles:

- **Pattern** — continuous (solid), dashed (broken), double (solid-solid / solid-broken / broken-broken).
- **Dimensions** — line width, and for dashes the dash length and gap; double-line separation.
- **Material parameters** — color and a surface/material preset id consumed by the USD layer.

**Externalized presets.** Road-type and marking preset *values* are **not hardcoded** — they live in
editable YAML under `presets/` (`road_types.yaml`, `markings.yaml`). The registries (`segments/presets`,
`markings/presets`) define only the schema and load these files via `common.config.resolve_presets_dir`
(overridable by `Config.presets_dir` or `$ROADUP_PRESETS_DIR`). Authoring assigns a marking-preset id to
a lane edge; the OpenDRIVE `<roadMark>` carries the geometric/semantic part and the material preset id
rides in `<userData>`. Initial values target **UAE/GCC** and are **provisional** pending validation (see
the `road-design-standards` skill). See [CODE_REFERENCE.md §7–§8](CODE_REFERENCE.md).

---

## 8. Segment ↔ Lane Connection Awareness

A core requirement: **segment connections must be fully aware of lane connections.**

- Connecting two segments creates a **road-level link** *and* resolves **lane-level links**.
- Default lane-link resolution matches lanes by **type then index/position** across the shared
  boundary (e.g. driving-lane 1 → driving-lane 1), and is **overridable** by the user.
- Through a junction, lane links are expressed as `<laneLink from to>` on each connection; outside
  junctions they are `<lane><link>` predecessor/successor pairs.
- `network/linkage` owns this resolution and enforces an invariant: **a road link is never authored
  without a consistent set of lane links**, and editing one side (adding a lane, changing a count)
  re-resolves the affected links and flags any that can no longer be satisfied.

This keeps topology coherent: deleting or re-laning a segment cascades to the lane links and to any
junction connections that referenced those lanes.

---

## 9. USD Output Layer (Generated for Omniverse)

USD is **generated**, not authoritative. The `usd/` package turns sampled OpenDRIVE geometry into a
stage Omniverse can render, and maintains the bridge needed for interaction.

- **Stage generation:** road surfaces, lane-edge marking strips, and junction surfaces become
  `UsdGeom.Mesh` prims. Per-road **Rails** — the reference-line centerline and each lane's outer
  edge — are emitted as `UsdGeom.BasisCurves` with `purpose = "guide"` (non-rendering, still
  pickable/snappable). The rails are first-class output, not debug: they are the curves the scene
  layer (below) scatters/arrays objects along.
- **Prim ↔ id mapping:** every generated prim is tagged (via custom attributes) with the OpenDRIVE
  element id (`roadId`, `laneId`, `junctionId`, and for handles a `controlPointId`). Viewport picking
  resolves a hit prim back to a model element so Tooling can act on it.
- **Materials from presets:** asphalt and marking materials are created from the marking/material
  presets; binding is by preset id so identical presets share one material.
- **Incremental updates:** regeneration is scoped to changed roads/junctions; prim paths are stable
  and derived from ids so updates are non-destructive.

No road *semantics* are stored only in USD — anything authoritative must exist in the OpenDRIVE model.

### 9.1 Scene coexistence (two sources of truth, one-way dependency)

OpenDRIVE cannot hold a *scene* — scattered props, environment, lighting, terrain. That data needs
its own authoritative home, but it must not compete with the `.xodr`. We partition with a **one-way
dependency**, expressed as USD **sublayers**:

| Artifact | Owns | Authored? |
|---|---|---|
| `*.xodr` | the **road network** (geometry, lanes, junctions, markings) | yes (via the model) |
| `*.generated.usda` | derived road USD (meshes, marking strips, **guide-curve rails**) | **no** — regenerated by `usd.StageGenerator`, never hand-edited |
| `*.scene.usda` | **everything else** (scatter, instancers, props, env) | yes — the second persisted artifact |

`*.scene.usda` **sublayers** `*.generated.usda` and authors scene content beside it. The scene
*depends on* the road (it references road **Rails** by their stable, id-keyed prim path); the road
**never depends on the scene**. So there is no bidirectional sync: a road edit just regenerates the
generated layer, and because prim paths are derived from ids and stable, the scene's references to
the rails survive regeneration. Sublayers (not references) because the two layers share one
namespace and we want a simple overlay the app can mute/reload; scatter uses `PointInstancer`
*inside* the scene layer. The **stable id-keyed prim path is the cross-layer contract** — see
`usd.mapping` (path helpers) and the guide-curve rails in `usd.stage`.

The "enter road editing tool" toggle is the user-facing face of this split: it selects the **edit
context** (`tooling.RoadToolController.EDIT_CONTEXTS` = `ROAD` | `SCENE`). `ROAD` edits flow to the
model → `.xodr` → regenerate the generated layer (road handles visible); `SCENE` authors the scene
layer (road locked). The toggle UI and the scatter/array tooling land with the Kit app (Phase 6+);
the headless seam exists now.

### 9.2 USD import boundary & version alignment (decision)

The same `.usda`/`.usdc` output must behave identically in two interpreters: the **dev/CI** venv
(pip `usd-core`) and **Kit's embedded** interpreter (NVIDIA's `nv_usd`). Kit's `nv_usd` is only ABI-
incompatible with vanilla USD in **Hydra/UsdImaging and the Asset Resolver** — the *authoring* Python
API (`Usd`, `UsdGeom`, `UsdShade`, `Sdf`, `Gf`) is stock and stable across releases. Two rules keep
us out of version-compat traps:

- **Authoring-subset-only.** `roadup/usd/` may import **only** OpenUSD *authoring* modules
  (`pxr.Usd`, `UsdGeom`, `UsdShade`, `Sdf`, `Gf`), always **lazily** (inside functions). It must
  **never** import Hydra/UsdImaging/AssetResolver or any `omni.*`/`carb.*`. This is the line that
  guarantees a stage written under pip-`usd-core` loads identically inside Kit. `usd/mapping.py`
  stays pure-Python (no `pxr` at all) so paths/tags are testable without USD.
- **Pin the dev USD to Kit's USD.** `usd-core` is a **dev/test/CI convenience only** — in Kit,
  `import pxr` resolves to `nv_usd`, not this wheel. The `usd` extra is pinned to the OpenUSD version
  Kit bundles (**Kit 110.1 → OpenUSD 25.11**); bump it in lockstep when the Kit target moves. Because
  pxr ships no stubs and injects symbols at runtime (`Tf.PreparePythonModule`), editor completion
  comes from generated stubs (`tools/gen_pxr_stubs.py` → `typings/`), regenerated per USD bump.

---

## 10. Omniverse Kit App Integration

The Kit App is the **only** UI. It is intentionally thin: it binds input and rendering to the
headless Tooling layer and renders the Tooling layer's manipulator state.

**Extension structure** (`app/exts/roadup.tool/`):

- `extension.py` — `omni.ext.IExt` with `on_startup` / `on_shutdown`; wires the controller, viewport
  input, manipulator view, and panels; declares dependencies in `extension.toml`.
- `viewport_input.py` — subscribes to viewport **cursor movement, click, and drag**; performs
  hit-tests and forwards normalized events to `tooling.RoadToolController`.
- `manipulator_view.py` — uses **`omni.ui.scene`** to draw control points (node handles, spline
  points) as an overlay manipulator, driven by the Tooling `ManipulatorModel`.
- `panels.py` — `omni.ui` panels for lane count, marking presets, and road-type presets.

**Cursor / hover behavior (explicit requirement).**

- The app listens to cursor movement every frame (an `omni.ui.scene` hover gesture for overlay
  handles, plus a viewport hit-test for prims under the cursor).
- On hover over a road, node, or junction, the app asks `tooling.HoverModel` which control points
  should be **shown**; on hover-out they are **hidden**. The visibility *policy* is headless and
  unit-tested; the app only renders the result.
- Control points are interactive `omni.ui.scene` shapes; dragging one emits a Tooling command that
  edits the OpenDRIVE model (e.g. a connection-spline point or a reference-line point), after which
  only the affected geometry is regenerated.

**Why this split:** all interaction *logic* lives in `tooling/` and is tested without Omniverse.
`omni.*` and `carb.*` imports appear only under `app/`. The app can be swapped or run headless in
tests by driving `RoadToolController` directly. Interface sketches: [CODE_REFERENCE.md §11–§13](CODE_REFERENCE.md).

**Host app strategy (decision).** RoadUp owns the **extension** (`app/exts/roadup.tool/`), not a Kit
*app*. The runnable app is a **thin host** generated **fresh** from NVIDIA's `kit-app-template`
(`repo template new` → **`kit_base_editor`**, the minimal editor — it already pulls
`omni.kit.manipulator.{prim,selection,camera}`, `omni.kit.viewport.window`, and the property/stage
windows the tooling binds to), kept in a **separate sibling repo** — *not* vendored into RoadUp (its
`repo`/premake/packman build machinery would muddy the pure-Python boundary) and *not* a copy of an
older project's app shell (the template is versioned with the Kit SDK; regenerate so it matches the
**Kit 110.1** target). The host adds `app/exts/` to its extension search path, makes the `roadup`
core importable by Kit's Python (PYTHONPATH / `.pth`), and enables `roadup.tool`. This keeps the
"core never depends on Kit" rule intact and lets the host be regenerated/upgraded independently.

---

## 11. Blender Headless (Optional, Isolated)

Blender is an **optional accelerator**, never a hard dependency, and must not become spaghetti.

- It sits behind a single `MeshProcessor` interface in `blender/`. The default implementation is
  pure Python (numpy); the Blender implementation is selected only when available.
- The boundary is `MeshData` in / `MeshData` out (points + faces). **`bpy` types never leak** past
  the adapter.
- Preferred execution is **out-of-process** (`blender --background --python …` over a temp
  OBJ/USD/glTF exchange file) so the heavy runtime is isolated and the core stays importable without
  Blender installed.
- Used only for operations that are painful in pure Python (robust booleans for complex multi-leg
  junctions, remesh/decimation, UV unwrapping). Everything else stays in `geometry/`.

If `geometry/` + numpy prove sufficient, the Blender path is simply never enabled — no code change in
the core.

---

## 12. Decoupling & Self-Containment Rules

1. **One source of truth.** Authoritative state is the OpenDRIVE model; USD and Blender consume it.
2. **Adapters quarantine dependencies.** `scenariogeneration`, `libOpenDRIVE`, `pxr`, `bpy`, `omni.*`
   each appear in exactly one package, behind an interface the rest of the system depends on.
3. **No upward imports.** Core never imports Tooling/USD/App; Tooling never imports `omni.*`.
4. **Narrow public surfaces.** Cross-package use goes through `__init__.py` exports only.
5. **Co-located tests.** Each package owns `tests/`; unit tests run with no native deps using fakes,
   so the whole core test suite is green on a plain Python install.
6. **Swappable backends.** The read/eval backend is chosen behind an adapter (libOpenDRIVE default;
   pure-Python topology fallback for tests), so CI needs no native libraries.

---

## 13. Testing Strategy

**Unit tests — co-located** in each `<package>/tests/`, one file per module. Run on a plain Python
environment using fakes for native backends. Examples: spline evaluation and control-point insertion;
width-law baking to `<width>` records; lane-link resolution; connection-spline default-arc and
edited-`paramPoly3` cases; marking-preset expansion; prim↔id mapping.

**Integration tests — top-level** `tests/integration/`, exercising flows across packages:

- `test_segment_creation` — author a road from a preset → model → `.xodr` → reload → equal.
- `test_intersection_editing` — build a junction, add a control point to a connection spline, assert
  the surface and `paramPoly3` update.
- `test_xodr_roundtrip` — write (scenariogeneration) → read (libOpenDRIVE) → compare topology +
  `<userData>` editing intent.
- `test_usd_generation` — sample a small network → USD stage → assert prim count and id tags.

**Fixtures** (`tests/fixtures/`): a straight 2-lane road, a 4-way junction, a width-tapered road, and
a tiny pre-built network.

---

## 14. Dependencies

```
# Required (core)
numpy                 # geometry math, sampling, mesh building
scenariogeneration    # OpenDRIVE (.xodr) writing
lxml                  # <userData> round-trip, fallback xodr parsing
libOpenDRIVE (binding)# OpenDRIVE reading + geometry evaluation  [native, isolated in opendrive/]

# Required (USD output)
usd-core (pxr)        # USD stage authoring for the Omniverse viewport

# Optional / accelerators (behind adapters, never required to import the core)
bpy                   # headless Blender mesh ops (prefer out-of-process)
scipy                 # advanced spatial queries / optimization
shapely               # 2D geometric helpers

# Provided by the runtime (not pip-installed)
omni.*, carb.*        # Omniverse Kit — only used under app/

# Development
pytest, pytest-cov    # testing + coverage
mypy                  # type checking
ruff                  # lint + format
```

> **Backend note.** The concrete `libOpenDRIVE` Python binding is pinned during the build session;
> `opendrive/io` and `opendrive/eval` are written against an internal adapter interface, with a
> pure-Python topology fallback, so the choice (libOpenDRIVE / esmini / pyxodr) is swappable and CI
> needs no native library. Tracked in §17 Open Questions.

---

## 15. Build Order (Implementation Sequence)

**Phase 1 — Core model & geometry**
1. `common/` — enums, ids, units, errors, config.
2. `geometry/` — splines (control-point editing), sampling, offset, `MeshData`/builders, `triangulate` (Delaunay fill).
3. `opendrive/model/` — dataclasses for roads, lane sections, lanes, width laws, road marks, junctions.

**Phase 2 — OpenDRIVE I/O (lean on libraries)**
4. `opendrive/io/writer` — model → `.xodr` via scenariogeneration.
5. `opendrive/io/reader` — `.xodr` → model via libOpenDRIVE (+ lxml fallback).
6. `opendrive/io/userdata` — round-trip editing intent.
7. `opendrive/eval/sampler` — model → ref-line frames + lane boundaries.

**Phase 3 — Authoring**
8. `segments/` — lane count, width laws, road-type presets.
9. `markings/` — road-mark model + presets (patterns, dims, materials).
10. `network/` — graph, spatial index, snapping, **road↔lane linkage**.

**Phase 4 — Intersections**
11. `intersections/connectivity` — lane connectivity resolution.
12. `intersections/connection_spline` — default arc + control-point editing.
13. `intersections/junction_builder` — author junction + connecting roads.
14. `intersections/{boundary,surface}` — editable junction boundary (node-road end-edges + corner
    Bézier fillets) capped to the intersection surface.

**Phase 5 — Output & Tooling**
15. `usd/` — stage generation, prim↔id mapping, materials.
16. `tooling/` — controller, hover/manipulator models, preview, commands/undo.

**Phase 6 — Omniverse App**
17. `app/` — Kit extension: viewport input, manipulator view, panels.

**Phase 7 — Optional acceleration**
18. `blender/` — `MeshProcessor` interface + out-of-process Blender impl (only if needed).

---

## 16. Naming & Layout Conventions

- **Modules:** snake_case (`connection_spline.py`).
- **Classes:** PascalCase (`ConnectionSpline`, `LaneWidthLaw`).
- **Functions/methods:** snake_case (`bake_width_records`).
- **Constants:** UPPER_SNAKE_CASE (`DEFAULT_FILLET_RADIUS`).
- **Private:** `_leading_underscore`.
- **IDs:** zero-padded, type-prefixed (`road_001`, `lane_-2`, `junction_007`, `cp_003`).
- **USD paths:** PascalCase under `/RoadNetwork` (`/RoadNetwork/Roads/Road_001`).
- **Tests:** co-located `tests/test_<module>.py`; integration in top-level `tests/integration/`.

### Repository layout (scaffolded)

```
roadup/
  common/        geometry/      opendrive/{model,io,eval}/   network/
  segments/      markings/      intersections/               usd/
  tooling/       blender/       app/exts/roadup.tool/
presets/         road_types.yaml   markings.yaml          # external, editable preset VALUES
tests/
  integration/   fixtures/
ARCHITECTURE.md  CODE_REFERENCE.md  pyproject.toml  README.md
.claude/         skills/   settings.json                  # MCP-grounded skills + permissions
.mcp.json                                                 # MCP server declarations
```

Each `roadup/<package>/` contains its modules and a `tests/` subfolder. Full tree and per-module
interfaces are in [CODE_REFERENCE.md](CODE_REFERENCE.md).

---

## 17. Open Questions & Decisions

| # | Question | Status | Decision |
|---|----------|--------|----------|
| 1 | Source of truth: USD or OpenDRIVE? | DECIDED | **OpenDRIVE (`.xodr`)**. USD is generated viewport output. |
| 2 | Build OpenDRIVE I/O or lean on libraries? | DECIDED | **Lean on libraries**: scenariogeneration (write), libOpenDRIVE (read/eval), behind adapters. |
| 3 | Our own editing model, or the libraries' objects? | DECIDED | **Thin neutral dataclass model**; adapters convert to/from each library. |
| 4 | Which libOpenDRIVE Python binding? | PENDING | Pin during build; adapter keeps it swappable (libOpenDRIVE / esmini / pyxodr) with a pure-Python fallback. |
| 5 | UI target. | DECIDED | **Omniverse Kit App only.** |
| 6 | Intersection connection geometry. | DECIDED | **Editable connection spline**; default circular `arc`, edited → `paramPoly3`. |
| 7 | Lane width along length. | DECIDED | OpenDRIVE `<width>` cubic records driven by an editable width law. |
| 8 | Road markings. | DECIDED | **Preset registry** (continuous/dashed/double + dims + material), values in external `presets/markings.yaml`; material via `<userData>`. |
| 9 | Blender headless. | DECIDED | **Optional**, behind `MeshProcessor`, preferably out-of-process; never required. |
| 10 | Where does editing intent live across save/load? | DECIDED | OpenDRIVE `<userData>` payloads (control points, tangents, preset ids). |
| 11 | Hover / control-point visibility. | DECIDED | Headless policy in `tooling.HoverModel`; `omni.ui.scene` renders it; logic is unit-tested. |
| 12 | OpenDRIVE version target. | DECIDED | **1.7** (move to 1.8 only if a needed feature requires it). |
| 13 | Presets hardcoded or external? | DECIDED | **External, editable YAML** in `presets/`; Python holds only schema + loader. |
| 14 | Road-design jurisdiction. | DECIDED | **UAE / GCC** target; seeded values **provisional**, validated by the author against official sources (see `road-design-standards`). |

---

## 18. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-06-25 | Architecture Team | Initial USD-first architecture. |
| 2.0.0 | 2026-06-26 | Architecture Team | Pivot to **OpenDRIVE source of truth**; USD becomes generated viewport output. Lean on scenariogeneration + libOpenDRIVE behind adapters. Editable intersection connection splines; lane width laws; marking presets; explicit segment↔lane link awareness. **Omniverse Kit App is the only UI** (removed Three.js / web). Optional, isolated headless Blender. Code snippets moved to CODE_REFERENCE.md. |
| 2.1.0 | 2026-06-26 | Architecture Team | **Externalized presets** to editable `presets/*.yaml` (schema + loader stay in code). **Pinned OpenDRIVE 1.7.** Design-standard target set to **UAE / GCC** with provisional seeded values. Added MCP server config + domain-expert skills under `.claude/`. |

---

*End of Architecture Document v2.1.0 — see [CODE_REFERENCE.md](CODE_REFERENCE.md) for all interface code.*
