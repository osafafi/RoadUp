# RoadUp

Pure-Python, **OpenDRIVE-native** procedural road authoring, presented through an **Omniverse Kit
App**. The `.xodr` network is the single source of truth; USD geometry is generated from it for the
viewport.

- **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md) — responsibilities, boundaries, data flow, decisions.
- **Interfaces / code sketches:** [CODE_REFERENCE.md](CODE_REFERENCE.md) — class/function signatures per module.

> **Stage: 6 / 7 — Omniverse Kit app (environment set up 🚧) · core through Stage 5 ✅** · see **[STATUS.md](STATUS.md)**
> for the exact, per-module build state. The pure-Python core through authoring and intersections is
> implemented: draw a reference-line spline and **bake** it into a road (geometry + lanes + width
> laws + marking presets), link roads (road↔lane link invariant), and **author junctions** —
> geometry-aware default movements, editable connection splines (line / minimal arc / tangent-matched
> Bézier), and a junction surface. Roads carry an editable **vertical profile (elevation) and
> superelevation (banking)** that round-trip through the **OpenDRIVE 1.7 writer + pure-Python
> reader** (incl. `<elevationProfile>` / `<lateralProfile>` and `<junction>`); evaluation lifts the
> sampled frames into 3D, and meshing samples **curvature-adaptively**. Stage 5 **generates the USD
> viewport stage** — road/junction surfaces + marking strips as meshes, plus guide-curve **Rails**
> (centerline + lane edges) tagged with `roadup:*` ids at stable paths — built so a `*.scene.usda`
> can **sublayer** the generated layer and author a scene beside it (two sources of truth, one-way
> dependency). A headless **tooling** layer (controller, hover, undoable commands, `ROAD`/`SCENE` edit
> context) drives edits with **no `omni.*`**. **Stage 6 has begun:** the Omniverse Kit app (**"Purple
> Light"**) and the `roadup.*` extensions are scaffolded in a **sibling repo** (`../PurpleLight`) — the
> environment loads and imports this core; the viewport/panel interaction logic is the work in progress.
> Phase 7 (optional Blender) is a stub.

## Layout

```
roadup/            core library (pure Python)
  common/          enums, ids, units, errors, config
  geometry/        editable splines, sampling, offset, mesh
  opendrive/       source of truth: model + io (read/write) + eval (sampling)
  network/         topology graph, spatial index, snapping, road<->lane linkage
  segments/        lane count, width laws, road-type presets
  markings/        road-mark presets (continuous/dashed/double + dims + material)
  intersections/   junctions + editable connection splines + surface
  usd/             generated USD viewport stage + prim<->id mapping + materials
  tooling/         headless interaction (controller, hover, manipulators, commands)
  blender/         optional, isolated headless Blender mesh adapter
tests/             integration tests + fixtures (unit tests are co-located per package)
```

The Omniverse Kit app **"Purple Light"** and the `roadup.*` extensions (viewport input, manipulators,
panels) live in a **separate sibling repo** (`../PurpleLight`), scaffolded from NVIDIA's
`kit-app-template`; they import this pure-Python core. See [ARCHITECTURE.md](ARCHITECTURE.md) §10.

## Requirements

**Python 3.12** (CPython 3.12.x). This is not arbitrary: the `roadup` core is imported by the Kit extension inside Omniverse Kit's *embedded* interpreter, so the dev/test interpreter must match it.
The targeted **Kit SDK 110.1.x** embeds **CPython 3.12.13** and **OpenUSD 25.11**. Develop and test on
3.12; the `usd` extra pins `usd-core` to that USD version so local output matches Kit's `nv_usd`
(dev/CI only — in Kit, `import pxr` resolves to Kit's USD, not this wheel). See [ARCHITECTURE.md §9.2](ARCHITECTURE.md).

## Quickstart

```bash
# from the repo root — Python 3.12 required (see Requirements)
py -3.12 -m venv .venv && . .venv/Scripts/activate    # Windows; use bin/activate on POSIX
# or with uv:  uv venv --python 3.12 .venv
pip install -e ".[dev]"                                # core + dev tools
pip install -e ".[dev,read,usd,accel]"                 # add backends when building those layers

pytest                                                 # placeholder unit + integration tests
ruff check roadup                                      # lint
mypy roadup                                            # type-check

# Editor completion for `pxr` (it ships no stubs; symbols are injected at runtime):
python tools/gen_pxr_stubs.py                          # -> typings/ (gitignored); needs the `usd` extra
```

The Omniverse extensions live in the sibling **Purple Light** repo (`../PurpleLight`), not here.
There, `repo build && repo launch` runs the app; its `roadup.core` extension locates this repo and
makes the `roadup` core importable by Kit's Python (auto-discovers a sibling `RoadUp/` folder, or set
`exts."roadup.core".roadupRepoPath` / the `ROADUP_REPO` env var). See ARCHITECTURE.md §10.

## Build order

See [ARCHITECTURE.md §15](ARCHITECTURE.md). Phase 1 starts with `common/`, `geometry/`, and
`opendrive/model/`.
