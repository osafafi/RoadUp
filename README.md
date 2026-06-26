# RoadUp

Pure-Python, **OpenDRIVE-native** procedural road authoring, presented through an **Omniverse Kit
App**. The `.xodr` network is the single source of truth; USD geometry is generated from it for the
viewport.

- **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md) — responsibilities, boundaries, data flow, decisions.
- **Interfaces / code sketches:** [CODE_REFERENCE.md](CODE_REFERENCE.md) — class/function signatures per module.

> **Status:** scaffolding. Every module is a typed stub raising `NotImplementedError`; unit tests are
> placeholders skipped pending the step-by-step build session.

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
app/exts/roadup.tool/   Omniverse Kit extension (viewport input, manipulators, panels)
tests/             integration tests + fixtures (unit tests are co-located per package)
```

## Requirements

**Python 3.12** (CPython 3.12.x). This is not arbitrary: the `roadup` core is imported by the Kit extension inside Omniverse Kit's *embedded* interpreter, so the dev/test interpreter must match it.
The targeted **Kit SDK 110.1.x** embeds **CPython 3.12.13**. Develop and test on 3.12.

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
```

The Omniverse extension is not pip-installed: add `app/exts/` to your Kit app's extension search
path and enable **roadup.tool** (the `roadup` core library must be importable by Kit's Python).

## Build order

See [ARCHITECTURE.md §15](ARCHITECTURE.md). Phase 1 starts with `common/`, `geometry/`, and
`opendrive/model/`.
