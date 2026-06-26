---
name: kit-app-tooling
description: Build the RoadUp Omniverse Kit extension UI and interaction (app/exts/roadup.tool). Use when working on omni.ui panels (lane count, markings, presets), omni.ui.scene manipulators / control points for nodes and spline points, viewport cursor hover / click / drag, picking a prim back to its OpenDRIVE id, or binding any of it to the headless roadup.tooling controller. Consult ui-kit-mcp (omni.ui / omni.ui.scene) and kit-dev-mcp (extension scaffolding, viewport, input).
---

# Kit App Tooling

The Omniverse Kit App is RoadUp's **only** UI, and it is deliberately **thin**: it binds viewport
input and rendering to the headless `roadup.tooling` controller and draws that controller's
manipulator state. All `omni.*` / `carb.*` imports live **only** under `app/`. See
[ARCHITECTURE.md §10](../../../ARCHITECTURE.md) and [CODE_REFERENCE.md §11, §13](../../../CODE_REFERENCE.md).

## Consult the MCP servers first

`omni.ui` widgets, `omni.ui.scene` gestures/shapes, and Kit extension/viewport APIs are version-
specific — look them up, don't guess:
- **ui-kit-mcp** — `get_ui_instructions`, `list_ui_classes` / `get_ui_class_detail`,
  `get_ui_method_detail`, `get_ui_style_docs`, `search_ui_window_examples`. For `omni.ui` **and**
  `omni.ui.scene` (SceneView, Manipulator, gestures, shapes).
- **kit-dev-mcp** — `search_kit_extensions` / `get_kit_extension_details`,
  `search_kit_code_examples`, `get_kit_api_details`, `search_kit_settings`. For the extension
  lifecycle, the active viewport, input subscriptions, and picking.

Fetch via ToolSearch if not loaded.

## The thin-app / headless-logic split (do not violate)

- **Logic is headless and tested without Omniverse:** hover→visibility policy (`tooling.HoverModel`),
  the control-point set (`tooling.ManipulatorModel`), tool modes and undo (`tooling.controller`,
  `tooling.commands`). Unit-tested in `roadup/tooling/tests`.
- **The app only:** subscribes to input, hit-tests, forwards normalized events, and renders the
  manipulator model. No road logic in `app/`.

## The pieces (`app/exts/roadup.tool/roadup_tool/`)

- `extension.py` — `omni.ext.IExt` `on_startup`/`on_shutdown`; wires controller ↔ viewport input ↔
  manipulator view ↔ panels. Declares deps + `[[python.module]] name = "roadup_tool"` in
  `config/extension.toml`.
- `viewport_input.py` — subscribes to **cursor move / click / drag**; `_pick(x,y)` hit-tests the
  viewport and resolves the prim via `roadup.usd.mapping.resolve_prim` → `{kind, id, point}`; forwards
  to `controller.on_hover/on_click/on_drag`.
- `manipulator_view.py` — an `omni.ui.scene` `Manipulator` that draws control points (node handles,
  spline points) from `ManipulatorModel.visible`; each handle is an `sc.Arc`/`sc.Points` with a
  **hover gesture** (show on hover) and a **drag gesture** (→ `controller.on_drag`).
- `panels.py` — `omni.ui` panels: road-type preset, lane-count steppers, marking-preset dropdowns;
  edits issue tooling commands (`SetLaneCount`, `SetLaneMarking`, …).

## The hover requirement (explicit)

Listen to cursor movement every frame. On hover over a road/node/junction, ask
`tooling.HoverModel` which control points to **show**; on hover-out, **hide** them. The visibility
*policy* is headless and unit-tested — the app just renders the result and `invalidate()`s the
manipulator. Dragging a shown control point edits the OpenDRIVE model (a spline or reference-line
point), after which only the affected geometry regenerates (see **usd-viewport**).

## Workflow

1. Confirm the panel/manipulator's job, inputs, and which controller method it drives.
2. Look up the exact widgets / gestures / style keys via ui-kit-mcp (and extension/viewport/pick APIs
   via kit-dev-mcp) — **don't invent APIs.**
3. Build layout/structure → style → wire to the controller. Keep all logic callable headlessly.

## Setup notes

The `roadup` core library must be importable by Kit's Python (pip-install into the Kit interpreter or
add to `PYTHONPATH`); the extension module is `roadup_tool` (kept distinct from `roadup` to avoid path
shadowing). Add `app/exts/` to the Kit app's extension search path and enable **roadup.tool**.
