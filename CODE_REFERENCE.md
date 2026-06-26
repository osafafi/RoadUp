# RoadUp — Code Reference

**Companion to [ARCHITECTURE.md](ARCHITECTURE.md).** Version 2.1.0 · 2026-06-26

> These are **interface sketches**, not final implementations — signatures, dataclasses, enums, and
> preset tables that show intended boundaries. The buildable starting point is the stub package under
> `roadup/`; this file is the design reference those stubs follow. Section numbers match the package
> map in ARCHITECTURE.md §4. Bodies are elided with `...` or `raise NotImplementedError`.

**Conventions used below**

- `Vec3 = tuple[float, float, float]`, `Vec2 = tuple[float, float]` (plain tuples at boundaries;
  numpy internally). No `pxr`/`Gf` types in the pure-Python core.
- All ids are `str` (see §1). `s` denotes arc length along a reference line (OpenDRIVE convention).

---

## Table of Contents

1. [common](#1-common)
2. [geometry](#2-geometry)
3. [opendrive.model](#3-opendrivemodel)
4. [opendrive.io](#4-opendriveio)
5. [opendrive.eval](#5-opendriveeval)
6. [network](#6-network)
7. [segments](#7-segments)
8. [markings](#8-markings)
9. [intersections](#9-intersections)
10. [usd](#10-usd)
11. [tooling](#11-tooling)
12. [blender](#12-blender)
13. [app (Omniverse Kit extension)](#13-app-omniverse-kit-extension)
14. [userData extension payloads](#14-userdata-extension-payloads)

---

## 1. common

```python
# common/types.py
from __future__ import annotations
from enum import Enum

Vec2 = tuple[float, float]
Vec3 = tuple[float, float, float]


class RoadType(str, Enum):
    HIGHWAY = "highway"
    ARTERIAL = "arterial"
    LOCAL = "local"
    PEDESTRIAN = "pedestrian"
    BIKE = "bike"


class LaneType(str, Enum):
    # Subset of OpenDRIVE lane types we author.
    DRIVING = "driving"
    SIDEWALK = "sidewalk"
    BIKING = "biking"
    PARKING = "parking"
    SHOULDER = "shoulder"
    MEDIAN = "median"
    NONE = "none"


class LaneSide(str, Enum):
    LEFT = "left"      # positive lane ids in OpenDRIVE
    CENTER = "center"  # lane id 0 (reference lane)
    RIGHT = "right"    # negative lane ids


class GeometryType(str, Enum):
    LINE = "line"
    ARC = "arc"
    SPIRAL = "spiral"
    POLY3 = "poly3"
    PARAM_POLY3 = "paramPoly3"


class TurnType(str, Enum):
    STRAIGHT = "straight"
    LEFT = "left"
    RIGHT = "right"
    U_TURN = "uTurn"
    MERGE = "merge"
```

```python
# common/ids.py
def make_id(prefix: str, n: int, width: int = 3) -> str:
    """Zero-padded, type-prefixed id, e.g. make_id('road', 1) -> 'road_001'."""
    ...

def parse_id(id_: str) -> tuple[str, int]:
    """'road_001' -> ('road', 1)."""
    ...

class IdAllocator:
    """Monotonic per-prefix id allocation for a session/model."""
    def next(self, prefix: str) -> str: ...
    def reserve(self, id_: str) -> None: ...
```

```python
# common/errors.py
class RoadError(Exception): ...
class ValidationError(RoadError): ...
class GeometryError(RoadError): ...
class TopologyError(RoadError): ...
class OpenDriveIOError(RoadError): ...
class IntersectionError(RoadError): ...
class USDError(RoadError): ...
```

```python
# common/units.py
M_PER_KM = 1000.0
def kmh_to_ms(kmh: float) -> float: ...
def deg_to_rad(deg: float) -> float: ...
def grade_percent(rise: float, run: float) -> float: ...
```

```python
# common/config.py  — global knobs only; preset VALUES are external YAML (§7/§8)
from dataclasses import dataclass
from pathlib import Path

PRESETS_DIR_ENV = "ROADUP_PRESETS_DIR"

@dataclass(frozen=True)
class Config:
    opendrive_version: str = "1.7"        # pinned target
    default_sampling_step: float = 1.0    # meters
    presets_dir: str | None = None        # override presets dir; None = default

def resolve_presets_dir(override: str | Path | None = None) -> Path:
    """Locate presets dir: override -> $ROADUP_PRESETS_DIR -> repo-root presets/."""
    ...

def load_config(path: str | None = None) -> Config: ...
```

---

## 2. geometry

Pure math. The editable spline is the authoring representation behind reference lines and connection
curves; it is *baked* to OpenDRIVE geometry records by `opendrive.io`.

```python
# geometry/splines.py
from __future__ import annotations
from dataclasses import dataclass, field
from common.types import Vec2, Vec3

@dataclass
class ControlPoint:
    position: Vec3
    # Optional explicit tangent handles (Bezier). None -> derived (Catmull-Rom).
    in_handle: Vec3 | None = None
    out_handle: Vec3 | None = None
    id: str = ""

class Spline:
    """Editable control-point spline (planar in xy for reference lines; z carried for elevation)."""
    points: list[ControlPoint]
    kind: str  # "bezier" | "catmullRom" | "line" | "arc"

    def evaluate(self, t: float) -> Vec3: ...
    def tangent(self, t: float) -> Vec3: ...
    def curvature(self, t: float) -> float: ...
    def length(self, t0: float = 0.0, t1: float = 1.0) -> float: ...
    def sample(self, step: float) -> list[Vec3]:
        """Arc-length-ish sampling at ~step meters."""
        ...

    # --- editing (used by tooling) ---
    def insert_control_point(self, t: float) -> ControlPoint:
        """Add a control point at parameter t, preserving shape; returns the new point."""
        ...
    def remove_control_point(self, cp_id: str) -> None: ...
    def move_control_point(self, cp_id: str, position: Vec3) -> None: ...

    @classmethod
    def circular_arc(cls, start: Vec3, start_tangent: Vec3,
                     end: Vec3, end_tangent: Vec3) -> "Spline":
        """Default intersection connector: minimal circular arc matching both tangents."""
        ...
```

```python
# geometry/sampling.py
from common.types import Vec3

@dataclass
class Frame:
    """A station frame along a reference line."""
    s: float
    position: Vec3
    tangent: Vec3   # unit, along +s
    normal: Vec3    # unit, left of tangent in xy (OpenDRIVE +t direction)

def sample_frames(points: list[Vec3], step: float) -> list[Frame]: ...
def resample_by_arclength(points: list[Vec3], step: float) -> list[Vec3]: ...
```

```python
# geometry/offset.py
from common.types import Vec3
from geometry.sampling import Frame

def offset_polyline(frames: list["Frame"], t_offset: float | list[float]) -> list[Vec3]:
    """Lateral offset along frame normals; scalar or per-frame (for varying lane width)."""
    ...

def lane_boundary(frames: list["Frame"], inner_t: list[float], outer_t: list[float]
                  ) -> tuple[list[Vec3], list[Vec3]]:
    """Inner/outer boundary polylines for a lane given per-station t offsets."""
    ...
```

```python
# geometry/mesh.py
from dataclasses import dataclass, field
from common.types import Vec2, Vec3

@dataclass
class MeshData:
    points: list[Vec3] = field(default_factory=list)
    face_vertex_counts: list[int] = field(default_factory=list)
    face_vertex_indices: list[int] = field(default_factory=list)
    normals: list[Vec3] = field(default_factory=list)
    uvs: list[Vec2] = field(default_factory=list)

    def merge(self, other: "MeshData") -> "MeshData": ...
    def is_manifold(self) -> bool: ...

class MeshBuilder:
    def ribbon(self, left: list[Vec3], right: list[Vec3]) -> MeshData:
        """Triangulated strip between two boundary polylines (road / marking surface)."""
        ...
    def extrude(self, path: list[Vec3], cross_section: list[Vec2]) -> MeshData: ...
    def polygon_surface(self, boundary: list[Vec3]) -> MeshData:
        """Cap an intersection area bounded by a closed polyline (ear-clip / constrained)."""
        ...
```

---

## 3. opendrive.model

Thin, neutral dataclasses mirroring OpenDRIVE. This is the **source-of-truth** representation that
`io` reads/writes and `eval` samples. No third-party types here.

```python
# opendrive/model/road.py
from __future__ import annotations
from dataclasses import dataclass, field
from common.types import GeometryType, LaneType

@dataclass
class Geometry:
    """One <planView><geometry> record."""
    s: float
    x: float
    y: float
    hdg: float
    length: float
    type: GeometryType
    params: dict[str, float] = field(default_factory=dict)  # curvature / aU..dV / etc.

@dataclass
class WidthRecord:
    """<lane><width> : w(ds) = a + b*ds + c*ds^2 + d*ds^3, valid from s_offset."""
    s_offset: float
    a: float
    b: float = 0.0
    c: float = 0.0
    d: float = 0.0

@dataclass
class RoadMark:
    """<lane><roadMark> — geometric/semantic part; material preset rides in user_data."""
    s_offset: float
    type: str           # "solid" | "broken" | "solid solid" | "solid broken" | ...
    weight: str = "standard"   # "standard" | "bold"
    color: str = "white"
    width: float = 0.15
    # Explicit dash dimensions when present (<type>/<line>):
    dash_length: float | None = None
    gap_length: float | None = None
    preset_id: str = ""        # RoadUp marking preset (see §8); persisted via user_data

@dataclass
class LaneLink:
    predecessor: int | None = None  # lane id in the previous element
    successor: int | None = None    # lane id in the next element

@dataclass
class Lane:
    id: int                         # OpenDRIVE signed lane id (0 = center/reference)
    type: LaneType = LaneType.DRIVING
    widths: list[WidthRecord] = field(default_factory=list)  # the width law along length
    road_marks: list[RoadMark] = field(default_factory=list)
    link: LaneLink = field(default_factory=LaneLink)
    user_data: dict = field(default_factory=dict)

@dataclass
class LaneSection:
    s: float
    left: list[Lane] = field(default_factory=list)
    center: Lane | None = None
    right: list[Lane] = field(default_factory=list)

    def lane(self, lane_id: int) -> Lane: ...
    def lane_ids(self) -> list[int]: ...

@dataclass
class RoadLink:
    predecessor: tuple[str, str] | None = None  # (elementType, elementId): ("road"|"junction", id)
    successor: tuple[str, str] | None = None

@dataclass
class Road:
    id: str
    length: float = 0.0
    geometry: list[Geometry] = field(default_factory=list)        # plan view reference line
    lane_sections: list[LaneSection] = field(default_factory=list)
    link: RoadLink = field(default_factory=RoadLink)
    junction: str | None = None     # set when this is a connecting road inside a junction
    user_data: dict = field(default_factory=dict)

    def lane_section_at(self, s: float) -> LaneSection: ...
```

```python
# opendrive/model/junction.py
from dataclasses import dataclass, field

@dataclass
class LaneLinkPair:
    from_lane: int
    to_lane: int

@dataclass
class Connection:
    id: str
    incoming_road: str
    connecting_road: str            # the connecting <road> carrying the connection spline
    contact_point: str = "start"    # "start" | "end"
    lane_links: list[LaneLinkPair] = field(default_factory=list)

@dataclass
class Junction:
    id: str
    name: str = ""
    connections: list[Connection] = field(default_factory=list)
    user_data: dict = field(default_factory=dict)
```

```python
# opendrive/model/network.py
from dataclasses import dataclass, field
from opendrive.model.road import Road
from opendrive.model.junction import Junction

@dataclass
class Header:
    version: str = "1.7"
    name: str = "RoadUp"
    geo_reference: str | None = None

@dataclass
class OpenDriveModel:
    """Top-level container — the single source of truth for the network."""
    header: Header = field(default_factory=Header)
    roads: dict[str, Road] = field(default_factory=dict)
    junctions: dict[str, Junction] = field(default_factory=dict)

    def add_road(self, road: Road) -> None: ...
    def remove_road(self, road_id: str) -> None: ...
    def get_road(self, road_id: str) -> Road: ...
    def add_junction(self, junction: Junction) -> None: ...
    def validate(self) -> list[str]:
        """Return a list of validation messages (empty = valid)."""
        ...
```

---

## 4. opendrive.io

Read/write delegated to libraries behind an adapter. Editing intent that OpenDRIVE cannot express is
round-tripped via `<userData>` (see §14).

```python
# opendrive/io/backend.py
from typing import Protocol
from opendrive.model.network import OpenDriveModel

class ReaderBackend(Protocol):
    """Adapter contract for an OpenDRIVE reader (libOpenDRIVE default; pure-Python fallback)."""
    def parse(self, xodr_path: str) -> OpenDriveModel: ...

class WriterBackend(Protocol):
    def write(self, model: OpenDriveModel, xodr_path: str) -> None: ...
```

```python
# opendrive/io/writer.py
from opendrive.model.network import OpenDriveModel

class ScenarioGenerationWriter:
    """model -> .xodr using `scenariogeneration.xodr`. Owns all scenariogeneration imports."""
    def write(self, model: OpenDriveModel, xodr_path: str) -> None:
        # Translate Road/LaneSection/Lane/WidthRecord/RoadMark/Junction into
        # scenariogeneration objects, attach <userData>, then write_xml().
        raise NotImplementedError
```

```python
# opendrive/io/reader.py
from opendrive.model.network import OpenDriveModel

class LibOpenDriveReader:
    """.xodr -> model using libOpenDRIVE bindings. Owns all libOpenDRIVE imports."""
    def parse(self, xodr_path: str) -> OpenDriveModel:
        raise NotImplementedError

class LxmlFallbackReader:
    """Pure-Python topology-only reader (no native dep) — used in CI/tests."""
    def parse(self, xodr_path: str) -> OpenDriveModel:
        raise NotImplementedError

def default_reader() -> "ReaderBackend":
    """libOpenDRIVE if importable, else the lxml fallback."""
    ...
```

```python
# opendrive/io/userdata.py
from typing import Any

USERDATA_NS = "roadup"   # <userData code="roadup">{json}</userData>

def encode(payload: dict[str, Any]) -> str: ...
def decode(blob: str) -> dict[str, Any]: ...
# Helpers attach/extract our editing intent (control points, tangents, preset ids) on
# Road/Lane/Junction model objects so a read->edit->write cycle is lossless.
```

---

## 5. opendrive.eval

Sampling for meshing/visualization. The default path is **pure-Python** (no native dep): plan-view
records are evaluated by `eval/planview.py` (line/arc/paramPoly3 closed-form, spiral by numeric
integration). A native libOpenDRIVE backend can replace this path behind the same `Sampler` surface
once a binding is pinned (deferred; ARCHITECTURE.md decision 4).

```python
# opendrive/eval/planview.py  — pure-Python plan-view evaluation
from common.types import Vec3
from geometry.sampling import Frame
from opendrive.model.road import Geometry

def eval_record(geom: Geometry, ds: float) -> Vec3:
    """(x, y, hdg) at local arc length ds along one plan-view record (3rd item is heading, not z).
    line/arc closed-form; spiral integrated numerically; paramPoly3 with arc-length->parameter map."""
    ...

def sample_planview(geometry: list[Geometry], step: float) -> list[Frame]:
    """Ordered geometry records -> station frames ~step m apart (true cumulative s, analytic
    tangents, +t left normal); shared record joints de-duplicated."""
    ...
```

```python
# opendrive/eval/sampler.py
from dataclasses import dataclass
from common.types import Vec3
from geometry.sampling import Frame
from opendrive.model.road import Road
from opendrive.model.network import OpenDriveModel

@dataclass
class LaneBoundaries:
    lane_id: int
    inner: list[Vec3]   # boundary toward the reference line
    outer: list[Vec3]   # boundary away from the reference line

class Sampler:
    """Wraps libOpenDRIVE's evaluation; falls back to geometry/ for the pure-Python path."""
    def __init__(self, model: OpenDriveModel, step: float = 1.0): ...
    def reference_frames(self, road_id: str) -> list[Frame]: ...
    def lane_boundaries(self, road_id: str, s0: float, s1: float) -> list[LaneBoundaries]: ...
    def road_surface_polylines(self, road_id: str) -> tuple[list[Vec3], list[Vec3]]:
        """Outermost left/right edges for the drivable surface ribbon."""
        ...
```

---

## 6. network

Topology and queries over the OpenDRIVE model. Owns the **road↔lane link** invariant (ARCHITECTURE §8).

```python
# network/graph.py
from opendrive.model.network import OpenDriveModel

class RoadGraph:
    """Connectivity view of the model: endpoints/junctions as nodes, roads as edges."""
    def __init__(self, model: OpenDriveModel): ...
    def neighbors(self, road_id: str) -> list[str]: ...
    def junction_of(self, road_id: str) -> str | None: ...
    def rebuild(self) -> None: ...
```

```python
# network/spatial.py
from common.types import Vec3

class SpatialIndex:
    """AABB index over sampled road geometry for nearby/snap queries."""
    def insert(self, road_id: str, bounds: tuple[Vec3, Vec3]) -> None: ...
    def query_radius(self, point: Vec3, radius: float) -> list[str]: ...
    def nearest(self, point: Vec3, k: int = 1) -> list[str]: ...
```

```python
# network/linkage.py
from opendrive.model.network import OpenDriveModel

class LinkResolver:
    """Keeps road-level and lane-level links consistent (segment connections aware of lanes)."""
    def __init__(self, model: OpenDriveModel): ...

    def connect_roads(self, road_a: str, contact_a: str,
                      road_b: str, contact_b: str,
                      lane_map: dict[int, int] | None = None) -> None:
        """Author a road link AND resolve lane links. Default lane_map matches by type+position."""
        ...
    def default_lane_map(self, road_a: str, road_b: str) -> dict[int, int]: ...
    def revalidate(self, road_id: str) -> list[str]:
        """After a re-laning/width change, re-resolve links; return unsatisfiable link warnings."""
        ...
    def disconnect(self, road_a: str, road_b: str) -> None: ...
```

```python
# network/snapping.py
from dataclasses import dataclass
from enum import Enum
from common.types import Vec3

class SnapKind(str, Enum):
    NODE = "node"; EDGE = "edge"; GRID = "grid"; NONE = "none"

@dataclass
class SnapResult:
    kind: SnapKind
    point: Vec3
    road_id: str | None = None
    s: float | None = None

class SnapEngine:
    SNAP_DISTANCE = 5.0
    def __init__(self, index: "SpatialIndex"): ...
    def find_snap(self, point: Vec3) -> SnapResult: ...
```

---

## 7. segments

Authoring a road segment: lane count/layout, width laws along length, and road-type presets.

```python
# segments/presets.py  — SCHEMA + loader only; VALUES live in presets/road_types.yaml (external)
from dataclasses import dataclass
from pathlib import Path
from common.types import RoadType, LaneType

@dataclass(frozen=True)
class LaneSpec:
    type: LaneType
    width: float
    marking_preset: str = ""   # outer edge marking preset id; must exist in markings.yaml

@dataclass(frozen=True)
class RoadTypePreset:
    road_type: RoadType
    lane_specs_right: tuple[LaneSpec, ...]   # in id order -1, -2, ...
    lane_specs_left: tuple[LaneSpec, ...]    # in id order +1, +2, ...
    center_marking_preset: str
    design_speed_kmh: float
    default_fillet_radius: float

PRESET_FILE = "road_types.yaml"   # under common.config.resolve_presets_dir()

# Values are NOT hardcoded — loaded from presets/road_types.yaml (UAE/GCC, provisional).
def load_road_type_presets(presets_dir: str | Path | None = None
                           ) -> dict[RoadType, RoadTypePreset]: ...
def get_road_type_preset(road_type: RoadType,
                         presets_dir: str | Path | None = None) -> RoadTypePreset: ...
```

```python
# segments/lane_width.py
from dataclasses import dataclass
from opendrive.model.road import WidthRecord

@dataclass
class WidthLaw:
    """Editable width-along-length, baked to OpenDRIVE <width> cubic records."""
    kind: str   # "constant" | "linear" | "spline"
    control: list[tuple[float, float]]   # [(s, width), ...]

    def width_at(self, s: float) -> float: ...
    def bake_records(self) -> list[WidthRecord]:
        """Produce piecewise-cubic <width> records covering the lane length."""
        ...
    @classmethod
    def constant(cls, width: float) -> "WidthLaw": ...
    @classmethod
    def taper(cls, s0: float, w0: float, s1: float, w1: float) -> "WidthLaw": ...
```

```python
# segments/builder.py
from common.types import RoadType, Vec3
from geometry.splines import Spline
from opendrive.model.road import Road

class SegmentBuilder:
    """Build a Road from a reference-line spline + a road-type preset, with overrides."""
    def __init__(self, road_type: RoadType): ...
    def with_reference_line(self, spline: Spline) -> "SegmentBuilder": ...
    def with_lane_count(self, left: int, right: int) -> "SegmentBuilder": ...
    def set_lane_width_law(self, lane_id: int, law: "WidthLaw") -> "SegmentBuilder": ...
    def set_lane_marking(self, lane_id: int, preset_id: str) -> "SegmentBuilder": ...
    def build(self, road_id: str) -> Road:
        """Bake spline -> plan-view geometry, lanes, width records, road marks."""
        ...
```

---

## 8. markings

Road-mark presets: patterns, dimensions, and material parameters. Presets only, for now.

```python
# markings/presets.py  — SCHEMA + loader only; VALUES live in presets/markings.yaml (external)
from dataclasses import dataclass, field
from pathlib import Path

@dataclass(frozen=True)
class MaterialParams:
    """Consumed by the USD layer to build/bind a material. Persisted via <userData>."""
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    roughness: float = 0.7
    metallic: float = 0.0
    emissive: float = 0.0

@dataclass(frozen=True)
class MarkingPreset:
    id: str
    pattern: str            # "solid" | "broken" | "double_solid" | "solid_broken" | "broken_solid"
    line_width: float       # meters
    dash_length: float = 0.0  # 0 for solid
    gap_length: float = 0.0
    separation: float = 0.0   # gap between the two lines of a double marking
    color: str = "white"      # "white" | "yellow"
    material: MaterialParams = field(default_factory=MaterialParams)

PRESET_FILE = "markings.yaml"   # under common.config.resolve_presets_dir()

# Values are NOT hardcoded — loaded from presets/markings.yaml (UAE/GCC, provisional).
def load_marking_presets(presets_dir: str | Path | None = None) -> dict[str, MarkingPreset]: ...
def get_preset(preset_id: str, presets_dir: str | Path | None = None) -> MarkingPreset: ...
```

```python
# markings/roadmark.py
from opendrive.model.road import RoadMark
from markings.presets import MarkingPreset

def to_road_mark(preset: MarkingPreset, s_offset: float = 0.0) -> RoadMark:
    """Expand a preset into an OpenDRIVE RoadMark (+ preset_id stored for user_data)."""
    ...

def marking_geometry_offsets(preset: MarkingPreset) -> list[float]:
    """Lateral t-offsets of each painted line relative to the lane edge (1 for single, 2 for double)."""
    ...
```

```python
# markings/material.py
from markings.presets import MaterialParams
# Pure-data helpers; the actual UsdShade material is built in usd/materials.py from these params.
def material_key(params: MaterialParams) -> str:
    """Stable key so identical params share one USD material."""
    ...
```

---

## 9. intersections

Junction authoring with **editable connection splines**. Default arc; control points upgrade it to a
`paramPoly3`; the surface adapts.

```python
# intersections/connection_spline.py
from geometry.splines import Spline
from common.types import Vec3

class ConnectionSpline:
    """The editable path of one junction connection (one connecting road's reference line)."""
    spline: Spline
    is_default_arc: bool   # True until the user edits control points

    @classmethod
    def default_arc(cls, start: Vec3, start_tangent: Vec3,
                    end: Vec3, end_tangent: Vec3) -> "ConnectionSpline":
        """Basic circular curve between two connected lane ends (the default)."""
        ...
    def add_control_point(self, t: float) -> str:
        """Add an editable control point; flips is_default_arc False. Returns control-point id."""
        ...
    def move_control_point(self, cp_id: str, position: Vec3) -> None: ...
    def remove_control_point(self, cp_id: str) -> None: ...
    def to_geometry_records(self) -> list["Geometry"]:
        """Bake to OpenDRIVE plan-view records: a single <arc> if default, else <paramPoly3>(s)."""
        ...
```

```python
# intersections/connectivity.py
from dataclasses import dataclass
from common.types import TurnType
from opendrive.model.network import OpenDriveModel

@dataclass
class Movement:
    incoming_road: str
    incoming_lane: int
    outgoing_road: str
    outgoing_lane: int
    turn: TurnType

class ConnectivitySolver:
    """Decide which incoming lanes connect to which outgoing lanes at a node."""
    def __init__(self, model: OpenDriveModel): ...
    def movements_at(self, node_road_ids: list[str]) -> list[Movement]:
        """Default movements by geometry + lane type; user can add/remove afterwards."""
        ...
```

```python
# intersections/junction_builder.py
from opendrive.model.network import OpenDriveModel
from opendrive.model.junction import Junction
from intersections.connectivity import Movement

class JunctionBuilder:
    """Create a Junction + connecting roads (each with a ConnectionSpline) from movements."""
    def __init__(self, model: OpenDriveModel): ...
    def build(self, junction_id: str, movements: list[Movement]) -> Junction:
        """For each movement: author a connecting road with a default-arc connection spline,
        add the <connection>/<laneLink>, and register everything on the model."""
        ...
    def connection_spline(self, junction_id: str, connection_id: str) -> "ConnectionSpline":
        """Fetch the editable spline for a connection (for the tooling layer to manipulate)."""
        ...
    def rebuild_connection(self, junction_id: str, connection_id: str) -> None:
        """Re-bake one connection's geometry after its spline was edited."""
        ...
```

```python
# intersections/surface.py
from geometry.mesh import MeshData
from opendrive.model.junction import Junction
from opendrive.eval.sampler import Sampler

class IntersectionSurface:
    """Generate the junction surface mesh from current connection splines + incoming lane edges."""
    def __init__(self, sampler: Sampler): ...
    def generate(self, junction: Junction) -> MeshData:
        """Boundary = union of outer lane edges + connection-spline fans; capped to a surface.
        Heavy boolean cases may be delegated to blender.MeshProcessor (see §12)."""
        ...
```

---

## 10. usd

Generated viewport output. The only package that imports `pxr`.

```python
# usd/mapping.py
# Custom USD attribute names that tag generated prims with their OpenDRIVE source ids.
ATTR_ROAD_ID = "roadup:roadId"
ATTR_LANE_ID = "roadup:laneId"
ATTR_JUNCTION_ID = "roadup:junctionId"
ATTR_CONTROL_POINT_ID = "roadup:controlPointId"

def road_prim_path(road_id: str) -> str: ...           # "/RoadNetwork/Roads/Road_001"
def junction_prim_path(junction_id: str) -> str: ...
def resolve_prim(prim) -> dict:
    """Read the roadup:* tags off a hit prim -> {kind, id} for the tooling layer."""
    ...
```

```python
# usd/materials.py
from markings.presets import MaterialParams

class MaterialLibrary:
    """Build/cache UsdShade materials from marking MaterialParams (dedup by material_key)."""
    def __init__(self, stage): ...
    def get_or_create(self, params: MaterialParams): ...   # -> UsdShade.Material
    def asphalt(self): ...
```

```python
# usd/stage.py
from opendrive.model.network import OpenDriveModel
from opendrive.eval.sampler import Sampler
from geometry.mesh import MeshData

class StageGenerator:
    """Build/update the USD viewport stage from the model + sampler. Incremental by road/junction."""
    def __init__(self, model: OpenDriveModel, sampler: Sampler, stage=None): ...
    def build_all(self) -> "object":  # returns Usd.Stage
        ...
    def update_road(self, road_id: str) -> None:
        """Regenerate only this road's prims (surface, marking strips), preserving paths/ids."""
        ...
    def update_junction(self, junction_id: str) -> None: ...
    def write_marking_strip(self, mesh: MeshData, road_id: str, lane_id: int, preset_id: str): ...
```

---

## 11. tooling

Headless interaction. No `omni.*` imports. The app renders this layer's state and forwards input to it.

```python
# tooling/manipulators.py
from dataclasses import dataclass, field
from common.types import Vec3

@dataclass
class Handle:
    id: str            # control-point id or node id
    position: Vec3
    kind: str          # "node" | "spline_point" | "tangent"
    owner: str         # road_id / junction_id+connection_id it belongs to

@dataclass
class ManipulatorModel:
    """The set of control points the UI should currently draw."""
    visible: list[Handle] = field(default_factory=list)
    selected: str | None = None
    hovered: str | None = None

    def set_handles(self, handles: list[Handle]) -> None: ...
```

```python
# tooling/hover.py
from common.types import Vec3

class HoverModel:
    """Decides which control points are visible given what is hovered. Pure policy — unit-tested."""
    def on_hover_element(self, kind: str, element_id: str) -> list["Handle"]:
        """Hover a road/node/junction -> the handles to show (node handles, spline points)."""
        ...
    def on_hover_clear(self) -> list["Handle"]:
        """Returns the (empty) handle set to hide everything not pinned by selection."""
        ...
```

```python
# tooling/commands.py
from typing import Protocol

class Command(Protocol):
    def do(self) -> None: ...
    def undo(self) -> None: ...

class CommandStack:
    def execute(self, cmd: Command) -> None: ...
    def undo(self) -> None: ...
    def redo(self) -> None: ...

# Concrete commands (each mutates the OpenDRIVE model, then triggers scoped regeneration):
class MoveControlPoint(Command): ...
class AddControlPoint(Command): ...
class SetLaneCount(Command): ...
class SetLaneWidthLaw(Command): ...
class SetLaneMarking(Command): ...
class ConnectSegments(Command): ...
```

```python
# tooling/controller.py
from common.types import Vec3
from opendrive.model.network import OpenDriveModel

class RoadToolController:
    """UI-agnostic interaction controller. The Kit extension drives these methods."""
    TOOL_MODES = ("DRAW_ROAD", "EDIT_SPLINE", "EDIT_INTERSECTION", "EDIT_LANES", "INSPECT")

    def __init__(self, model: OpenDriveModel): ...
    def set_mode(self, mode: str) -> None: ...

    # input (already hit-tested by the app; ids resolved via usd.mapping)
    def on_hover(self, hit: dict | None) -> "ManipulatorModel":
        """hit = {kind, id, point} or None. Returns the manipulator state to render."""
        ...
    def on_click(self, hit: dict, modifiers: dict) -> None: ...
    def on_drag(self, world_point: Vec3, modifiers: dict) -> None: ...
    def on_release(self, world_point: Vec3, modifiers: dict) -> None: ...

    def manipulators(self) -> "ManipulatorModel": ...
    def preview(self): ...   # -> lightweight Usd.Stage (see preview.py)
```

```python
# tooling/preview.py
from opendrive.model.road import Road
class PreviewGenerator:
    """Lightweight, low-res geometry for in-progress edits (separate USD layer above committed data)."""
    def road_preview(self, road: Road): ...      # -> Usd.Stage
    def clear(self) -> None: ...
```

---

## 12. blender

Optional, isolated. Default is pure Python; Blender is opt-in and preferably out-of-process.

```python
# blender/processor.py
from typing import Protocol
from geometry.mesh import MeshData

class MeshProcessor(Protocol):
    """Boundary is MeshData in / MeshData out. No bpy types cross this line."""
    def boolean_union(self, meshes: list[MeshData]) -> MeshData: ...
    def remesh(self, mesh: MeshData, voxel_size: float) -> MeshData: ...
    def decimate(self, mesh: MeshData, ratio: float) -> MeshData: ...

class PurePythonMeshProcessor:
    """numpy/geometry-based default — sufficient for simple junctions."""
    def boolean_union(self, meshes: list[MeshData]) -> MeshData: raise NotImplementedError
    def remesh(self, mesh: MeshData, voxel_size: float) -> MeshData: raise NotImplementedError
    def decimate(self, mesh: MeshData, ratio: float) -> MeshData: raise NotImplementedError

def get_processor(prefer_blender: bool = False) -> MeshProcessor:
    """Return BlenderMeshProcessor if requested and available, else PurePythonMeshProcessor."""
    ...
```

```python
# blender/blender_processor.py
from geometry.mesh import MeshData

class BlenderMeshProcessor:
    """Runs Blender headless out-of-process over a temp exchange file. bpy is never imported here
    in-process; we shell out to `blender --background --python _bpy_worker.py`."""
    def __init__(self, blender_exe: str | None = None): ...
    def boolean_union(self, meshes: list[MeshData]) -> MeshData: raise NotImplementedError
    def remesh(self, mesh: MeshData, voxel_size: float) -> MeshData: raise NotImplementedError
    def decimate(self, mesh: MeshData, ratio: float) -> MeshData: raise NotImplementedError
# blender/_bpy_worker.py  -> the only file that imports bpy; executed by the Blender interpreter.
```

---

## 13. app (Omniverse Kit extension)

Thin binding of viewport input/rendering to Tooling. Lives under `app/exts/roadup.tool/`. The only
place `omni.*` / `carb.*` are imported. Python module name: `roadup_tool` (kept distinct from the
core `roadup` package to avoid path shadowing).

```toml
# app/exts/roadup.tool/config/extension.toml
[package]
title = "RoadUp Tool"
version = "0.1.0"
description = "Procedural OpenDRIVE road authoring in the Omniverse viewport."

[dependencies]
"omni.ui" = {}
"omni.usd" = {}
"omni.kit.viewport.utility" = {}
"omni.ui.scene" = {}

[[python.module]]
name = "roadup_tool"
```

```python
# app/exts/roadup.tool/roadup_tool/extension.py
import omni.ext

class RoadUpToolExtension(omni.ext.IExt):
    def on_startup(self, ext_id: str) -> None:
        # 1. Load/attach the OpenDriveModel; build the StageGenerator.
        # 2. Create RoadToolController(model).
        # 3. Wire ViewportInput -> controller; ManipulatorView <- controller.manipulators().
        # 4. Register UI panels.
        raise NotImplementedError
    def on_shutdown(self) -> None:
        raise NotImplementedError
```

```python
# app/exts/roadup.tool/roadup_tool/viewport_input.py
class ViewportInput:
    """Subscribe to cursor move / click / drag; hit-test; forward normalized events to the controller.
    Hover hit-test resolves the prim under the cursor -> usd.mapping.resolve_prim -> {kind, id}."""
    def __init__(self, controller, manipulator_view): ...
    def _on_mouse_moved(self, x: float, y: float) -> None:
        # hit = self._pick(x, y); model = controller.on_hover(hit); manipulator_view.sync(model)
        ...
    def _on_mouse_pressed(self, x: float, y: float, button: int, mods) -> None: ...
    def _on_mouse_dragged(self, x: float, y: float, mods) -> None: ...
    def _pick(self, x: float, y: float) -> dict | None: ...
```

```python
# app/exts/roadup.tool/roadup_tool/manipulator_view.py
from omni.ui import scene as sc

class ManipulatorView(sc.Manipulator):
    """Draws control points (node handles, spline points) from the tooling ManipulatorModel.
    Each handle is an sc.Arc/sc.Points with a HoverGesture (show on hover) and a DragGesture
    (-> controller.on_drag). Visibility comes straight from ManipulatorModel.visible."""
    def on_build(self) -> None: raise NotImplementedError
    def sync(self, model) -> None:
        """Update the drawn handles to match the tooling manipulator state, then invalidate()."""
        ...
```

```python
# app/exts/roadup.tool/roadup_tool/panels.py
import omni.ui as ui

class RoadUpPanel:
    """omni.ui panel: road-type preset picker, lane-count steppers, marking-preset dropdowns.
    Edits issue tooling Commands (SetLaneCount, SetLaneMarking, ...)."""
    def __init__(self, controller): ...
    def build(self) -> None: raise NotImplementedError
```

---

## 14. userData extension payloads

OpenDRIVE cannot express our editing intent or material choices. We store them under
`<userData code="roadup">…</userData>` as compact JSON so a read→edit→write cycle is lossless. The
sampled standard records (e.g. `paramPoly3`, `<width>`, `<roadMark>`) remain the canonical data for
any third-party OpenDRIVE consumer.

```jsonc
// On a connecting <road> (intersection connection spline):
{
  "kind": "connectionSpline",
  "isDefaultArc": false,
  "controlPoints": [
    { "id": "cp_001", "pos": [12.0, 0.0, 3.4], "outHandle": [13.5, 0.0, 3.4] }
  ]
}

// On a <lane> (width law + marking preset, when not fully recoverable from records):
{
  "kind": "lane",
  "widthLaw": { "kind": "spline", "control": [[0.0, 3.5], [20.0, 4.25]] },
  "markingPreset": "white_dashed"
}

// On a <road> (reference-line editing handles):
{ "kind": "referenceLine", "splineKind": "bezier", "controlPoints": [/* ... */] }
```

```python
# Round-trip helpers live in opendrive/io/userdata.py (§4):
#   encode(payload) -> str      # json.dumps, stable key order
#   decode(blob)    -> dict
```

---

*End of Code Reference v2.1.0 — architecture rationale in [ARCHITECTURE.md](ARCHITECTURE.md).*
