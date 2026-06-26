# RoadUp — OpenDRIVE-native procedural roads (pure Python + Omniverse Kit)

RoadUp authors road networks where **OpenDRIVE (`.xodr`) is the single source of truth** and USD is
*generated* output for the Omniverse Kit viewport. The core is **pure Python**, modular, each system
self-contained with co-located tests. Architecture is fixed first; the code is built step by step.

## Read these first (authoritative — load on demand, don't re-read every session)

| Doc | What |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Layers, module map, data flow, decisions. **Read before any structural/architectural work**; keep in sync in the *same* change (definition-of-done). |
| [CODE_REFERENCE.md](CODE_REFERENCE.md) | Interface signatures per module — the build contract the stubs follow. |

## What lives where

| Path | What |
|---|---|
| `roadup/` | Pure-Python core: `common`, `geometry`, `opendrive/{model,io,eval}`, `network`, `segments`, `markings`, `intersections`, `usd`, `tooling`, `blender`. |
| `app/exts/roadup.tool/` | Omniverse Kit extension (viewport input, `omni.ui.scene` manipulators, panels). The **only** place `omni.*` is imported. |
| `tests/` | Integration tests + fixtures; **unit tests are co-located** in each `roadup/<pkg>/tests/`. |

## MCP servers — your domain experts (consult BEFORE answering from memory)

USD / Kit / `omni.ui` / Blender APIs change between versions. **Ground claims in these servers — not
training data or the web.** Local servers; the http ones need their Docker containers running.

| Server | Use it for | Prefix |
|---|---|---|
| **usd-mcp** (`:9903`) | USD: composition, schemas, prim/stage APIs, code examples | `mcp__usd-mcp__*` |
| **kit-dev-mcp** (`:9902`) | Kit framework: extensions, viewport, input, settings, Python APIs | `mcp__kit-dev-mcp__*` |
| **ui-kit-mcp** (`:9901`) | `omni.ui` / `omni.ui.scene`: widgets, layouts, manipulators, styling | `mcp__ui-kit-mcp__*` |
| **blender-mcp** (stdio) | Drive/query headless Blender to prototype a mesh op before wiring it in | `mcp__blender-mcp__*` |

If a server's tools aren't loaded, fetch via ToolSearch (e.g. `select:mcp__usd-mcp__search_usd_code_examples`).

> **OpenDRIVE has no MCP.** Ground OpenDRIVE work in the `scenariogeneration` (write) and libOpenDRIVE
> (read/eval) APIs plus the ASAM OpenDRIVE spec. **Ask before fetching any spec/docs from the web.**

## Hard conventions (enforce everywhere)

- **OpenDRIVE is truth.** Network semantics live in the `.xodr` model; USD is generated, never
  authoritative. Anything authoritative must exist in the model.
- **Units: meters; Z-up.** `metersPerUnit = 1.0`, USD stage Z-up — matches OpenDRIVE (z up) and
  Omniverse. Road-local frame: **s** along the reference line, **t** lateral (+t = left), **z** up.
- **Pure-Python core; adapters quarantine native deps.** `scenariogeneration`, `libOpenDRIVE`, `pxr`,
  `bpy`, `omni.*` each appear in exactly **one** package, behind an interface. No upward imports
  (core never imports `tooling`/`usd`/`app`; `tooling` never imports `omni.*`).
- **Editing intent → OpenDRIVE `<userData code="roadup">`** (spline control points, width laws,
  marking-preset ids) so a read → edit → write cycle round-trips losslessly.
- **Generated USD prims carry `roadup:*` id tags** (`roadId`/`laneId`/`junctionId`/`controlPointId`)
  so viewport picking/hover maps back to model elements.
- **Naming:** `snake_case` modules/functions, `PascalCase` classes, zero-padded type-prefixed ids
  (`road_001`, `junction_007`). USD paths `PascalCase` under `/RoadNetwork`.
- **Tests co-located** per package; they run on plain Python using fakes — no native deps in CI.

## Skills (`.claude/skills/`) — reach for these when the task matches

- **opendrive-core** — read/write/model `.xodr` (scenariogeneration + libOpenDRIVE): connection
  splines, lane width laws, road marks, junctions, lane links, `<userData>` round-trip.
- **usd-viewport** — generate + audit the USD stage Omniverse renders from sampled OpenDRIVE
  (prim↔id tags, materials from presets, instancing, incremental update). Consult usd-mcp.
- **kit-app-tooling** — the Kit extension: `omni.ui` panels + `omni.ui.scene` manipulators + viewport
  hover/picking, bound to the headless tooling controller. Consult ui-kit-mcp / kit-dev-mcp.
- **blender-mesh-accel** — optional, isolated headless Blender as an out-of-process mesh processor
  (boolean / remesh / decimate). Consult blender-mcp.
- **road-design-standards** — sourcing real geometric-design figures to back presets; cite official
  sources; ask before fetching.

## Working agreement

- Consult the MCP servers / library APIs for signatures — **don't invent USD/Kit/`omni.ui`/OpenDRIVE
  APIs.** Prefer a server lookup over a guess.
- When you produce USD, show the resulting `.usda` so composition is auditable.
- Keep ARCHITECTURE.md / CODE_REFERENCE.md authoritative and in sync with structural changes.
- Don't re-read the whole codebase each session — the module map above + ARCHITECTURE.md are the
  index. Build step by step; the stubs raise `NotImplementedError` until their phase.
