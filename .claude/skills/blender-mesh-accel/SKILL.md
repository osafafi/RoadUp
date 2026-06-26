---
name: blender-mesh-accel
description: Use headless Blender as RoadUp's optional, isolated mesh-processing accelerator (roadup/blender) — robust boolean union for complex junction surfaces, remesh, decimate, UV unwrap — across a MeshData in/out boundary, run out-of-process. Use when implementing or prototyping such a mesh op, or deciding whether an operation needs Blender at all. Prototype against blender-mcp, then port the verified bpy into _bpy_worker.py. Not a component-export pipeline.
---

# Blender Mesh Accelerator

Blender is an **optional accelerator** in RoadUp, never a hard dependency, and must not become
spaghetti. It sits behind `roadup.blender.MeshProcessor`; the default implementation is pure-Python
(numpy). See [ARCHITECTURE.md §11](../../../ARCHITECTURE.md) and [CODE_REFERENCE.md §12](../../../CODE_REFERENCE.md).

> RoadUp's USD is generated from OpenDRIVE — Blender is **not** a component-authoring or USD-export
> pipeline here. Its only job is heavy mesh ops the pure-Python path can't do well.

## Rules of isolation (non-negotiable)

- **Boundary is `MeshData` in / `MeshData` out** (points + faces). `bpy` types never cross it.
- **Out-of-process by default:** shell out to `blender --background --python _bpy_worker.py` over a
  temp exchange file. `_bpy_worker.py` is the **only** module that imports `bpy`; the in-process
  `BlenderMeshProcessor` is a thin subprocess driver.
- **Never required to import the core.** If `roadup/geometry` + numpy suffice, the Blender path stays
  disabled and nothing changes in the core. `get_processor(prefer_blender=…)` chooses at runtime.

## When to reach for it

- Robust **boolean union** of overlapping connecting-road surfaces in a multi-leg junction.
- **Remesh / decimate** a dense generated mesh.
- **UV unwrap** where planar projection isn't enough.

Everything else stays in `roadup/geometry`.

## Prototype with blender-mcp, then port

The `blender-mcp` server drives a live Blender — use it to **prove a mesh op before** wiring it into
`_bpy_worker.py`:
- `mcp__blender-mcp__get_scene_info` — coarse inventory (object names/types, material count).
- `mcp__blender-mcp__get_object_info(object_name)` — transforms, world bounding box, mesh vert/edge/
  poly counts, material names.
- `mcp__blender-mcp__execute_blender_code(code)` — **the workhorse.** Run `bpy` to test the actual
  boolean/remesh/decimate on a sample mesh and read back the result.
- `mcp__blender-mcp__get_viewport_screenshot(max_size)` — eyeball the result.

Each tool takes a `user_prompt` arg (telemetry). Fetch via ToolSearch if not loaded.

**Discipline:** validate the operation in `blender-mcp` (correct result, expected vert count, manifold
output), then port the *verified* `bpy` into `roadup/blender/_bpy_worker.py`. Keep the worker pure:
read the exchange file → run the op → write `MeshData` back.

## Caveats

- `bpy` is version-locked and heavy — out-of-process keeps it from polluting the core and its imports.
- Exchange via a temp file (OBJ/USD) that carries points + faces; round-trip and assert the mesh is
  manifold (`MeshData.is_manifold`) before handing it to **usd-viewport**.
