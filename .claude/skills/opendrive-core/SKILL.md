---
name: opendrive-core
description: Read, write, and model OpenDRIVE (.xodr) — RoadUp's single source of truth — using scenariogeneration (write) and libOpenDRIVE (read/eval). Use when authoring or parsing .xodr, mapping the road/lane/junction model, building or editing intersection connection splines, lane width laws along length, road marks, road/lane links, or round-tripping editing intent via <userData>. Grounds in the library APIs and the ASAM OpenDRIVE spec — never invented signatures.
---

# OpenDRIVE Core

The heart of RoadUp. The `.xodr` network carries all road logic and topology; USD is generated from
it. This skill governs `roadup/opendrive/{model,io,eval}`, plus the OpenDRIVE-facing parts of
`segments`, `markings`, and `intersections`. See [CODE_REFERENCE.md §3–§5](../../../CODE_REFERENCE.md).

## Ground every claim — there is no OpenDRIVE MCP

Don't write `scenariogeneration` / libOpenDRIVE calls or `.xodr` element layouts from memory.
- **Write path:** `scenariogeneration.xodr` — verify class/param names against the installed version.
- **Read / eval path:** the libOpenDRIVE binding — verify the parse + sampling API.
- **Spec questions** (element nesting, attribute semantics): the **ASAM OpenDRIVE** spec is the
  reference — **target version 1.7**. **Ask the author before fetching it or any docs from the web**
  (project rule). Reference only (do not fetch without asking): ASAM OpenDRIVE user guide —
  `https://www.asam.net/index.php?eID=dumpFile&t=f&f=4422&token=e590561f3c39aa2260e5442e29e93f6693d1cccd`

The USD/Kit MCP servers do **not** cover OpenDRIVE — use them only for the USD output layer.

## The three layers (keep them separate)

1. **`opendrive/model/`** — thin, neutral dataclasses mirroring OpenDRIVE (`Road`, `LaneSection`,
   `Lane`, `WidthRecord`, `RoadMark`, `Junction`, `Connection`, `LaneLink`, `OpenDriveModel`). **No
   third-party types here.** This is the only authoritative, editable representation.
2. **`opendrive/io/`** — adapters that quarantine the libraries: `writer` (model → `.xodr` via
   scenariogeneration), `reader` (`.xodr` → model via libOpenDRIVE, with a pure-Python `lxml`
   topology fallback for CI), `userdata` (round-trip editing intent).
3. **`opendrive/eval/`** — `sampler` wraps libOpenDRIVE to turn the model into reference-line frames
   and lane-boundary polylines for meshing. Don't re-implement spiral/poly3/paramPoly3 math.

The libraries are write-optimized (scenariogeneration) and read/eval-optimized (libOpenDRIVE);
neither is a round-trippable editing model, which is why the neutral model exists.

## Concept → OpenDRIVE element (the mapping to honor)

| RoadUp concept | OpenDRIVE | Notes |
|---|---|---|
| Reference line | `<planView>` `line`/`arc`/`spiral`/`poly3`/`paramPoly3` | Editable spline baked to records. |
| Lane count/layout | `<laneSection>` `<left>/<center>/<right><lane>` | New section where the count changes along `s`. |
| **Lane width along length** | one or more `<width sOffset a b c d>` per lane | A piecewise-cubic width *law*; multiple records vary width along `s`. |
| **Road markings** | `<roadMark>` (+ `<type>/<line>` for dashes) | type/weight/color/width + dash length/space. |
| Marking **material** | `<userData>` (preset id) | OpenDRIVE has no material model. |
| Segment link | `<road><link><predecessor>/<successor>` | Road-level. |
| **Lane link** | `<lane><link>` and junction `<laneLink>` | Kept consistent with the road link. |
| Intersection | `<junction>` + connecting `<road>`s | Each connection is a connecting road. |
| **Connection spline** | connecting road `<planView>` | Default `arc`; edited → `paramPoly3`. |

## Connection splines (the distinctive bit)

Default when two lanes connect = a single circular `arc` tangent-matched to both ends. Adding control
points upgrades it to a control-point spline (`geometry/splines.py`) baked to `paramPoly3`. The
connecting road's lanes follow the edited reference line; the junction surface is regenerated.
Store the user's control points/tangents in `<userData>` so editing intent survives a round-trip;
the sampled `paramPoly3` stays canonical for any other OpenDRIVE consumer.

## Round-trip discipline (the invariant that proves correctness)

`write (scenariogeneration) → read (libOpenDRIVE) → compare` must preserve **topology + lane links +
`<userData>` editing intent**. The integration test `tests/integration/test_xodr_roundtrip.py` is
the gate. CI uses the pure-Python fallback reader so it needs no native library.

`<userData>` payloads use `code="roadup"` and compact JSON — see
[CODE_REFERENCE.md §14](../../../CODE_REFERENCE.md). Helpers live in `opendrive/io/userdata.py`.

## Handoff

Sampled geometry → **usd-viewport**. Junction connection splines + surface → `intersections` (see the
intersection logic in CODE_REFERENCE §9). Preset values that need real figures → **road-design-standards**.
