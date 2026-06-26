---
name: road-design-standards
description: Source real-world road geometric-design figures to back RoadUp presets — lane / shoulder / median widths, lane-marking dimensions / colors / patterns, junction corner radii, design speed, max grade, taper lengths. Use when a preset value needs to become real rather than a placeholder. Every figure must cite an official source; the governing jurisdiction/standard is confirmed with the author; ask before fetching any standard from the web.
---

# Road Design Standards (reference)

RoadUp's presets (`segments/presets.py`, `markings/presets.py`, fillet radii, grades) are **presets
for now** — illustrative numbers. This skill is the discipline for turning them into *cited* values,
plus a growing datasheet. It starts empty on purpose.

## Confirm the jurisdiction first

There is no single global road standard. Before sourcing a figure, **confirm with the author which
standard governs** — e.g. AASHTO *Green Book* (US), a national/agency geometric-design manual, or a
specific country/city authority. Don't assume one. Different standards give different lane widths,
radii, and marking dimensions; mixing them silently is a bug.

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
