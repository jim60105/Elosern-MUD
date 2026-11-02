# Settlement synthesis

`tools/settlement_synthesis/` answers three questions about a settlement before
any street graph is drawn or edited:

- **Where does it sit?** `site` derives the rivers, sea, fords, harbour sites,
  relief and neighbour bearings around one location.
- **How big is it?** `budget` turns a population into a built-up area, a
  wilderness footprint, a metre envelope and a gameplay tier.
- **Does the drawn graph fit?** `lint` checks authored nodes, roads and gates
  against the terrain in world metres.

All three are read-only. They live in the game environment because they join
`world.lore.anchors.ANCHOR_LORE` for nation and population; they need no Django
setup and write no file. `--lore FILE` replaces that join with a JSON override,
which is how the tests stay off shipped lore.

## Scales

The wilderness is a grid of 1 km cells whose centre lies at
`(1000X + 500, 1000Y + 500)` metres. Settlement streets are integer-metre
graphs, and their polyline lengths drive walking time at 1.25 m/s. The two
scales stay separate and both come from one built-up area:

- the **footprint** is wilderness occupancy, in whole 1 km cells: a cell becomes
  town instead of wilderness;
- the **envelope radius** is the metre extent of the street graph.

Rounding the footprint up to whole cells absorbs walls, suburbs and gardens,
while the street extent stays at the built-up size. A 6,000-person town is about
770 m across, a 10-minute walk; a 600,000-person capital is about 4 km across,
about 45 minutes gate to gate.

The lint links the scales in one direction: a node must stand inside a
footprint cell. A terrain window is clamped to the continent frame, and a window
boundary is not a coastline — an out-of-frame cell is neither land nor sea and
is not walkable. That is why a gate approach outside the frame is an error
rather than an empty neighbourhood.

## Size budget

Built-up area follows the Cesaretti et al. (2016, *PLOS ONE*) population–area
relation over 173 medieval European cities, `area ∝ population^0.714`.

**Density anchor.** The late-medieval walled-town literature describes roughly
100–250 inhabitants per hectare. The default anchors 10,000 people at
150 inhab/ha, which gives about 0.67 km². This is an accepted assumption for
this game, not a measured constant, and it is one tunable
`BudgetConfig` value rather than a scattered number. With exponent 0.714, density
rises as `population^0.286`.

The derivation, in order:

1. reference area = reference population / reference density / 100 (ha per km²);
2. area = reference area × (population / reference population) ^ exponent;
3. footprint cells = `max(2, ceil(area km²))`, so no supported settlement is
   ever a concealed single-cell entry;
4. envelope radius = `round(1000 × sqrt(area / π))`;
5. the tier is chosen from the table below, or the capital tier for a capital.

| Tier (minimum population) | Nodes | Gates | Loop ratio |
| --- | ---: | ---: | ---: |
| capital | 28 | 4 | 0.35 |
| 100,000 | 18 | 3 | 0.30 |
| 50,000 | 12 | 2 | 0.25 |
| 25,000 | 10 | 2 | 0.20 |
| 10,000 | 8 | 2 | 0.15 |
| below 10,000 | 6 | 2 | 0.15 |

The tiers grow log-like rather than linearly, because they budget gameplay
structure, not floor space.

Default output, for review:

| Population | Area km² | Footprint cells | Envelope radius m | Inhabitants/ha |
| ---: | ---: | ---: | ---: | ---: |
| 6,000 | 0.46 | 2 | 384 | 130 |
| 25,000 | 1.28 | 2 | 639 | 195 |
| 55,000 | 2.25 | 3 | 847 | 244 |
| 180,000 | 5.25 | 6 | 1,293 | 343 |
| 400,000 | 9.28 | 10 | 1,719 | 431 |
| 600,000 | 12.40 | 13 | 1,987 | 484 |
| 800,000 | 15.23 | 16 | 2,202 | 525 |

The three fantasy capitals sit at 430–525 inhabitants per hectare, above
historical walled-town norms. That is an explained constraint, not a
recomputation: the magical-era setting has multi-storey building and regional
supply, per the continental-geography "Large fantasy capitals" scenario. The
budget explains their size; it never changes their population.

A kind outside `capital`, `city`, `town` and `port`, or a population that is
missing or not positive, is rejected with an error naming the location. No
budget is produced.

## Site context

`site` reports, for one location and search radius:

- every waterway within the radius, with Euclidean distance in cells, the
  8-way bearing of the body's centroid, its nearest cell and, for a river, the
  downstream bearing of the route segment nearest that cell;
- the sea, when any sea cell is inside the radius, on the same terms;
- every ford and harbour site, with distance and bearing;
- the relief (band range) and uphill bearing over the walkable cells within
  three cells, plus the location cell;
- the nearest four national settlements, nearest first with ties by identifier;
- the bearing to the settlement's own capital, absent for a capital itself.

The search radius is a Chebyshev box; distances are Euclidean over cell
indices. A river's downstream bearing comes from its authored source-to-mouth
route, so flow direction is real data rather than a guess from geometry.

## Terrain-fit lint

Every check runs in world metres, resolving the settlement's local frame
through its location cell and its unique anchor node. A finding names the map
and the object; the lint never edits a coordinate, a direction or an
identifier.

| Code | Severity | Rule |
| --- | --- | --- |
| `fit_missing_anchor` | error | The map has no unique `anchor_room`, so its local frame cannot be placed. This is the only finding reported. |
| `fit_node_in_water` | error | The node's world position falls in an inland-water or sea cell. |
| `fit_water_role_dry` | error | A node whose identifier carries a water-edge word lies more than 600 m from any water in the window. No water in the window also triggers it. |
| `fit_unbridged_crossing` | error | A road's world-metre polyline enters an inland-water or sea cell while neither endpoint identifier carries a crossing word. |
| `fit_node_outside_footprint` | error | For a multi-cell footprint, the node's cell is not one of the footprint cells. |
| `fit_gate_approach_blocked` | error | For a multi-cell footprint, the gate has no approach cell, or the approach cell is not walkable. |
| `fit_gate_side` | warning | For a multi-cell footprint, the gate's destination node lies more than 90 degrees from the gate's outward bearing. |
| `fit_direction_drift` | warning | The authored road direction is more than one octant from the 8-way bearing of the road's first segment. |

The water-edge words are the whole underscore-separated tokens `quay`,
`wharf`, `dock`, `docks`, `pier`, `landing`, `riverbank` and `waterfront`; the
crossing words are `bridge`, `ford` and `ferry`. An identifier such as
`quayside` therefore claims no water-edge role, while `old_ford_lane` is a
crossing. Ford cells never count as water.

The 600 m water-edge limit exists because the wilderness raster is 1 km: a
stream inside a cell cannot be represented, so a water-edge role is allowed a
generous distance rather than an exact shoreline. Road polylines are sampled
every 50 m or less, endpoints included.

The terrain window is sized from every cell the lint reads: the map's nodes,
road bends, footprint cells and gate approaches. A window is a convex square, so
every sampled point of a segment whose endpoints are inside it is inside it too;
the whole of each road polyline is therefore checked, however far a bend
reaches.

Water is only known per 1 km cell, and the sampler tests points rather than
cell entries: a road that clips the corner of a water cell for less than the
50 m sample spacing can pass between two samples. That is a limit of the
approved sampling rule; the fix for a reported crossing is the same either way,
so it is documented rather than papered over.

Errors mean the graph contradicts its terrain. Warnings are review prompts:
they name a gate that faces inward or a road whose authored exit name drifts
from its drawn shape.

## Commands

Run from the repository root:

```console
uv run --locked python -m tools.settlement_synthesis site LOCATION_ID [--root DIR] [--lore FILE] [--radius N]
uv run --locked python -m tools.settlement_synthesis budget LOCATION_ID [--root DIR] [--lore FILE]
uv run --locked python -m tools.settlement_synthesis lint [MAP_ID ...] [--root DIR]
```

- `site` prints the `SiteContext` as JSON and exits 0. `--radius` is the water
  search radius in wilderness cells and defaults to 20 (a 20 km box); the
  relief neighbourhood is always three cells.
- `budget` prints the `SizeBudget` as JSON and exits 0. A location with no
  budget prints its reason to stderr and exits 1.
- `lint` prints one line per finding, `SEVERITY code map_id object_id:
  message`, then `fit: N errors, M warnings`. It exits 0 when no error-severity
  finding exists, 1 when any does, and 2 when the map sources do not load or a
  requested map id is unknown. Warnings alone still exit 0.
- `--root` defaults to the current directory. Nothing is written, so a run can
  never change the sources it inspects.

The lint is a workflow tool, not a CI gate over shipped data. It currently
reports `capital_altoria`'s dry `quay` and `riverbank_road` nodes, four of its
nodes outside the authored footprint mask, and nothing else; `altoria-capital-river-rework`
resolves the water mismatch.

## Human review

These qualities are reviewed by a person against this page, not tested:

- Does a two-cell town and a thirteen-cell capital look right on the continent
  capture?
- Do the walking times between the gates and the plaza feel right for the tier?
- Is the 150 inhabitants per hectare anchor acceptable for this setting?
- Do the loop ratios produce streets that feel connected rather than maze-like?
- Does every identifier with a water-edge word belong at the water, and every
  gate's outward bearing match the direction a traveller actually approaches
  from?
