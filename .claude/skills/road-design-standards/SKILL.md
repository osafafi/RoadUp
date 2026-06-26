---
name: road-design-standards
description: Source real-world road geometric-design figures to back RoadUp presets — lane / shoulder / median widths, lane-marking dimensions / colors / patterns, junction corner radii, design speed, max grade, taper lengths. Use when a preset value needs to become real rather than a placeholder. Every figure must cite an official source; the governing jurisdiction/standard is confirmed with the author; ask before fetching any standard from the web.
---

# Road Design Standards (reference)

RoadUp's preset **values** live in editable `presets/*.yaml` (road-type lane layouts, widths, marking
dimensions, fillet radii, design speeds) — seeded with **provisional** UAE/GCC numbers. This skill is
the discipline for turning them into *cited* values, plus a growing datasheet (`cheatsheet.md`) that
starts empty on purpose.

## Jurisdiction: UAE / GCC

RoadUp targets **UAE and Gulf** roads. Validate figures against the relevant authorities — the
**Dubai RTA**, **Abu Dhabi** (DMT/ITC), the UAE **Ministry of Energy & Infrastructure (MOEI)**, and
**GCC** standard specifications where an emirate manual defers to them. Emirates can differ (Dubai vs
Abu Dhabi) — record which one a figure comes from. Don't mix standards silently.

The seeded values in `presets/road_types.yaml` and `presets/markings.yaml` are **provisional** UAE/GCC
placeholders the author will validate; replace them with cited figures and log the citation in
`cheatsheet.md`.

## How to use this skill

1. If the figure is in **`cheatsheet.md`** and cited → use it.
2. If it's **missing or marked UNVERIFIED** → do **not** invent a number. Either:
   - ask the author for the official figure / document, or
   - clearly label the value a placeholder that must be confirmed before it drives real geometry.
3. When a value is confirmed, **append it to `cheatsheet.md`** with its source + date so the project
   accumulates verified ground truth. Never write figures into this playbook.

> **Ask before fetching.** Per the project rule, do not fetch a standards document or webpage without
> the author's go-ahead. Prefer a document the author provides.

## Figure → OpenDRIVE / preset target

| Design figure | Lands in | OpenDRIVE element |
|---|---|---|
| Lane / shoulder / median width | `RoadTypePreset.lane_specs_*`, `WidthLaw` | `<lane><width>` `a` coefficient |
| Marking pattern + line width + dash length/gap | `MarkingPreset` | `<roadMark>` type / `<line>` length·space·width |
| Marking color | `MarkingPreset.color` / `MaterialParams` | `<roadMark color>` (+ `<userData>` material) |
| Junction corner radius | `RoadTypePreset.default_fillet_radius` | connecting-road `arc` radius |
| Design speed | `RoadTypePreset.design_speed_kmh` | road metadata |
| Max grade | road preset / validation | elevation profile constraint |
| Taper / transition length | segment authoring | lane-section transition along `s` |

## Datasheet

Confirmed, cited figures live in the sibling **`cheatsheet.md`**. Read it when you need a value;
append to it (with source + date) when one is confirmed. Keep placeholder/test values clearly
separate from cited production values.

## Handoff

Confirmed figures feed **opendrive-core** (what to author into the model) and the preset registries
used by `segments` / `markings`.
