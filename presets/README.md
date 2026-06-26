# RoadUp presets (external, editable)

Road-type and marking preset **values** live here as YAML — they are **not** hardcoded in the Python
codebase. Edit these files to customize RoadUp's defaults. The code
([`roadup/segments/presets.py`](../roadup/segments/presets.py),
[`roadup/markings/presets.py`](../roadup/markings/presets.py)) defines only the *schema* and *loads*
these files.

| File | What |
|---|---|
| `road_types.yaml` | Per road-type lane layout (count, type, width), default markings, design speed, junction fillet radius. |
| `markings.yaml` | Lane-marking presets: pattern (solid / broken / double), line width, dash/gap, separation, color, material params. |

## ⚠️ Values are PROVISIONAL (UAE / GCC)

The seeded numbers target **UAE and Gulf** roads but are **not yet validated** against official
sources. Treat them as placeholders to tweak. When you confirm an official figure, update the YAML and
record the citation in the `road-design-standards` skill's `cheatsheet.md`.

## Customizing / relocating

The loader resolves the presets directory in this order
(`roadup.common.config.resolve_presets_dir`):

1. an explicit path passed to the loader, or `Config.presets_dir`;
2. the `ROADUP_PRESETS_DIR` environment variable;
3. this `presets/` folder at the repo root (default — suits running from source).

**Conventions:** units are **meters** / **km/h**; lane ids are right = -1, -2, …, left = +1, +2, …,
center = 0; every `marking_preset` referenced in `road_types.yaml` must exist in `markings.yaml`.
