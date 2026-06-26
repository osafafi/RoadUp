---
name: usd-viewport
description: Generate and audit the USD stage that the Omniverse viewport renders, built from sampled OpenDRIVE geometry (not hand-authored). Use when writing roadup/usd — stage generation, prim<->OpenDRIVE id tags, materials from marking presets, incremental per-road/junction updates, instancing repeated geometry — or reviewing a generated .usda for units, prim-path stability, id tags, and scale correctness. Consult usd-mcp; show the resulting .usda.
---

# USD Viewport Stage

In RoadUp, USD is **generated output**, not the source of truth. `roadup/usd` turns sampled
OpenDRIVE geometry into a stage Omniverse renders, and maintains the bridge that makes viewport
interaction possible. See [CODE_REFERENCE.md §10](../../../CODE_REFERENCE.md).

## Consult usd-mcp before writing `pxr`

Don't author USD API calls from memory — verify:
- `mcp__usd-mcp__search_usd_code_examples` — the pattern (Mesh authoring, primvars, instancing).
- `mcp__usd-mcp__get_usd_class_detail` / `get_usd_method_detail` — exact API.
- `mcp__usd-mcp__search_usd_knowledge` — composition / scale concepts.

Fetch via ToolSearch if not loaded (`select:mcp__usd-mcp__search_usd_code_examples,mcp__usd-mcp__get_usd_method_detail`).

## Stage contract

- All prims under **`/RoadNetwork`**; stage metadata **Z-up, `metersPerUnit = 1.0`**.
- Roads, junction surfaces, and lane-edge marking strips → `UsdGeom.Mesh`. Reference lines may be
  `UsdGeom.BasisCurves` for debug only.
- **Prim paths are derived from OpenDRIVE ids** (`/RoadNetwork/Roads/Road_001`) so they're stable and
  updates are non-destructive — never path by enumeration order.

## Prim ↔ id tags (load-bearing for interaction)

Every generated prim carries `roadup:*` custom attributes (`roadId`, `laneId`, `junctionId`, and for
handles `controlPointId`) — see `usd/mapping.py`. The Kit app hit-tests a prim and calls
`resolve_prim` → `{kind, id}` so the tooling layer can act on the right model element. **If a prim
isn't tagged, hover/picking can't map it back — that's a bug, not an optimization.**

## Materials from presets

Build `UsdShade` materials from marking `MaterialParams` (`usd/materials.py`); **dedup by
`material_key`** so identical presets share one material. Bind by preset id. Don't invent per-prim
materials.

## Incremental update (the scale discipline)

Regenerate only the **changed** road/junction prims (`update_road` / `update_junction`), preserving
stable paths. Don't rebuild the whole stage on every edit. Repeated content (signs, poles, marking
dashes at scale) should resolve to **instanceable / PointInstancer**, not N duplicated subtrees —
duplicated inline geometry is the #1 scale killer.

## Audit checklist (review a generated `.usda`)

Read the `.usda` as text and report **pass / risk / fail**, each with the line and fix:

- [ ] Exactly one `defaultPrim`; everything under `/RoadNetwork`.
- [ ] `upAxis = "Z"`, `metersPerUnit = 1`.
- [ ] Every road/lane/junction prim tagged with the matching `roadup:*` id.
- [ ] Prim paths derived from ids (stable across regeneration), no order-dependent names.
- [ ] Repeated geometry is `instanceable`/PointInstancer — no duplicated `points` arrays.
- [ ] An incremental `update_*` changed only the intended prims and orphaned none.
- [ ] Materials deduped by `material_key`; bindings present.

## Output format (when reviewing)

```
## USD Viewport Review — <file/stage>
✅ Pass: <what's correct>
⚠️ Risk: <line> — <why it bites at scale> — <fix>
❌ Fail: <line> — <problem> — <concrete fix>
```

Always show the resulting `.usda` so composition is auditable. Sampling that feeds this comes from
**opendrive-core** (`opendrive/eval`); interaction that consumes the id tags is **kit-app-tooling**.
