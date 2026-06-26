# Test fixtures

Sample data shared by integration tests (and any unit test that needs a realistic model). Built in
the step-by-step build session; this README pins the intended set.

| Fixture | Description | Used by |
|---------|-------------|---------|
| `straight_2lane` | One straight road, 1+1 driving lanes, solid edges, dashed centre. | segment creation, USD generation |
| `width_taper` | One road whose right lane tapers via a `WidthLaw`. | lane-width round-trip |
| `cross_4way` | Four roads meeting at one node → a junction with default-arc connections. | intersection editing, connectivity |
| `edited_connection` | `cross_4way` with one connection spline carrying an extra control point (→ `paramPoly3`). | connection-spline round-trip |
| `mini_network` | 3 roads + 1 junction. | network/linkage, USD generation |

Curated `.xodr` / `.usda` sample files may be committed alongside builder functions; keep them small.
