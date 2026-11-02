# Design

## Context

See proposal.md (Why). This change builds on `settlement-terrain-fit`, which is already landed: `geometry.py`, `terrain_view.GridTerrain`, `site.analyse_site` / `SiteContext` / `SettlementRef`, `budget.size_budget` / `SizeBudget`, `fit_lint.lint_settlement` / `WATER_EDGE_WORDS` / `CROSSING_WORDS`, `workspace.load_workspace` / `WorkspaceView` / `load_lore` and the CLI. Use their names exactly.

Facts that constrain the output:

- The settlement schema is listed by `uv run --locked --project packages/map-core python -m elosern_map_core schema`.
  - Every node needs `x_m`, `y_m` (int), `prototype_parent` (`grid_room` or `anchor_room`), `key` (non-empty string), `desc` (string, which may be empty), `anchor_key` (required for `anchor_room`, `None` otherwise), `typeclass` (nullable) and `scene_archetype` (nullable).
  - Node coordinates are unique pairs.
  - The `(source, destination)` pairs of roads are unique.
  - No node has two outgoing roads with the same `direction`.
  - `wilderness_entry` and `city_gate` are required keys whose value may be `None`.
- `scene_archetype: city_street` is a registered archetype. Settlement node ids are scoped per map.
- Gate approach rule: walk from the mask's anchor cell (the bounding-box midpoint) in the direction *opposite* `return_direction`, until leaving the footprint. In this design a gate's *bearing* `o` is outward, so `return_direction = OPPOSITE[o]` and the walk goes along `o`.
- `elosern_map_core.codec.document_from_data(path, data)` validates the data. `serialize_document(document, None)` emits it and re-parses it.

## Goals / Non-Goals

**Goals:** a pure `generate_settlement(GenerationInput) -> GenerationResult` that synthetic tests can establish, plus a thin CLI.

**Non-Goals:**
- replace or bind mode, prose and briefs (`settlement-rework-and-prose`);
- bends;
- interiors;
- city gates (always `None`);
- writing shipped data.

## Decisions

### D1. Contracts (`generate.py`). Copy them verbatim

```python
SETTLEMENT_CLASSES = ("human_capital", "human_town", "port", "beast_capital", "beast_town")
MORPHOLOGIES = ("tribal_ring", "harbour_crescent", "river_crossing", "waterside_linear", "hill_terraces", "crossroads")
OCTANT_WORDS = {"n": "north", "ne": "northeast", "e": "east", "se": "southeast",
                "s": "south", "sw": "southwest", "w": "west", "nw": "northwest"}
OCTANT_ZH = {"n": "北", "ne": "東北", "e": "東", "se": "東南", "s": "南", "sw": "西南", "w": "西", "nw": "西北"}
FALLBACK_BEARINGS = ("s", "n", "e", "w", "se", "sw", "ne", "nw")

@dataclass(frozen=True)
class GenerationConfig:
    beast_nations: frozenset[str] = frozenset({"valhalla"})
    water_edge_max_m: int = 600          # must equal fit_lint.LintConfig().water_edge_max_m
    margin_m: int = 100
    max_degree: int = 6

@dataclass(frozen=True)
class GenerationInput:
    map_id: str
    location: SettlementRef
    site: SiteContext
    budget: SizeBudget
    terrain: GridTerrain
    blocked: frozenset[Cell]             # never part of this footprint, never an approach cell
    catalogue: tuple[RoleEntry, ...]
    forced_gates: tuple[str, ...] = ()   # octants, highest priority first
    config: GenerationConfig = GenerationConfig()

@dataclass(frozen=True)
class Slot:
    slot_id: str
    role: str          # "anchor" | "gate" | "crossing" | "approach" | "filler" | catalogue slot_id
    key_zh: str
    rel_m: tuple[float, float]   # metres relative to the location cell centre (east, north)

@dataclass(frozen=True)
class GenerationResult:
    map_id: str
    settlement_class: str
    morphology: str
    footprint: frozenset[Cell]
    slots: tuple[Slot, ...]      # document node order
    data: Mapping[str, Any]      # complete settlement document data (D8)
    warnings: tuple[str, ...]    # sorted

class GenerationError(ValueError): ...

def generate_settlement(inp: GenerationInput) -> GenerationResult
def seed_for(map_id: str) -> int:
    return int.from_bytes(hashlib.sha256(f"settlement:{map_id}:v1".encode("utf-8")).digest()[:8], "big")
```

Randomness:
- Create `rng = random.Random(seed_for(map_id))` once per call.
- Call only `rng.random()`, never `randint`, `choice` or `shuffle`, whose algorithms change between Python versions.
- The order of draws is the order of the steps below.

Every set iteration whose order affects the output must go through `sorted()`. Sort cells as `(y, x)`.

### D2. Role catalogue (`roles.py`)

```python
PLACEMENTS = ("near_anchor", "high_ground", "periphery", "ring", "water_edge", "water_downstream")

@dataclass(frozen=True)
class RoleEntry:
    slot_id: str
    key_zh: str
    classes: frozenset[str]   # subset of SETTLEMENT_CLASSES
    placement: str            # one of PLACEMENTS
    priority: int             # lower first; ties by slot_id
    min_nodes: int            # included only when budget.node_count >= min_nodes
    requires: str | None      # None | "water" (river or sea contact) | "river"
```

For one class, `slot_id` values are unique. Two entries may share a `slot_id` when their `classes` are disjoint.

`DEFAULT_CATALOGUE` derives from the location-applicability matrix in `docs/lore/settlement-locations.md`. Class abbreviations: HC = human_capital, HT = human_town, P = port, BC = beast_capital, BT = beast_town.

| slot_id | key_zh | classes | placement | priority | min_nodes | requires |
| --- | --- | --- | --- | ---: | ---: | --- |
| quay | 碼頭 | P | water_edge | 5 | 0 | water |
| market_street | 市場街 | HC HT P BC BT | near_anchor | 10 | 0 | – |
| palace_forecourt | 王宮前庭 | HC | high_ground | 12 | 0 | – |
| tribal_hall | 部族議事廳前 | BC BT | ring | 12 | 0 | – |
| assembly_ground | 集會場 | BC BT | near_anchor | 13 | 0 | – |
| training_ground | 校場外 | BC BT | ring | 14 | 0 | – |
| harbour_office | 港務總管府前 | P | water_edge | 15 | 0 | water |
| guild_forecourt | 公會前 | HC HT P BC BT | near_anchor | 20 | 0 | – |
| river_quay | 河港碼頭 | HC HT | water_edge | 25 | 8 | river |
| temple_forecourt | 神殿前 | HC HT P | high_ground | 30 | 0 | – |
| ancestral_altar | 祖靈祭壇 | BC BT | high_ground | 30 | 0 | – |
| noble_quarter | 貴族區前 | HC | high_ground | 35 | 0 | – |
| inn_lane | 客棧巷 | HC HT P | near_anchor | 40 | 8 | – |
| tavern_lane | 酒館巷 | BC BT | near_anchor | 40 | 8 | – |
| riverbank | 河岸道 | HC HT P | water_edge | 45 | 10 | river |
| ferry_landing | 渡口碼頭 | BC BT | water_edge | 45 | 8 | river |
| exchange_forecourt | 商會前 | HC P | near_anchor | 45 | 10 | – |
| exchange_forecourt | 商會前 | HT | near_anchor | 45 | 12 | – |
| craft_alley | 工匠巷 | HC HT P BC BT | water_downstream | 50 | 8 | – |
| academy | 學院前 | HC | high_ground | 55 | 0 | – |
| manor_gate | 領主宅邸前 | HT | high_ground | 56 | 8 | – |
| training_ground | 校場外 | HC | periphery | 60 | 0 | – |
| training_ground | 校場外 | HT | periphery | 60 | 12 | – |
| bath_forecourt | 浴場前 | HC P | near_anchor | 65 | 10 | – |
| bath_forecourt | 浴場前 | HT | near_anchor | 65 | 12 | – |

These are coarse zoning choices. `craft_alley` (tanners and dyers) goes downstream when there is water, and on the periphery otherwise. Ports keep a harbour office instead of a manor. `inn_lane` and `tavern_lane` stand for the inn/tavern street. Shops stay interiors and are out of scope. Matching the lore is human-reviewed, never tested: the tests pass synthetic catalogues.

### D3. Class, reach and morphology

- **Settlement class:**
  - `location.nation in config.beast_nations` gives `beast_capital` when `kind == "capital"`, and `beast_town` otherwise;
  - otherwise `capital` gives `human_capital`, `port` gives `port`, and `city` or `town` gives `human_town`.
- `reach = math.ceil(math.sqrt(budget.footprint_cells) / 2) + 1`, in cells. `cheb(a, b) = max(|ax-bx|, |ay-by|)`.
- **River:** the first contact in `site.rivers` whose `cheb(location.cell, nearest_cell) ≤ reach`.
- **Sea:** `site.sea`, when `cheb(location.cell, site.sea.nearest_cell) ≤ reach`.
- **Ford:** the first entry in `site.fords` whose `feature_id == river.name` and `cheb ≤ reach`.
- **Morphology**, first match wins:
  1. A beast class gives `tribal_ring`. The water target is the river if there is one, else none.
  2. `port`: `harbour_crescent` (target: sea) if there is a sea; else `waterside_linear` (target: river) if there is a river; else raise `GenerationError(f"{map_id}: water_gap: no sea or river within {reach} cells")`.
  3. A river and a ford give `river_crossing`. The target is the ford cell.
  4. A river alone gives `waterside_linear`. The target is the river.
  5. `site.relief >= 2` gives `hill_terraces`.
  6. Otherwise `crossroads`.
- `water_vec` is the unit vector of `OCTANT_VECTORS[target.bearing]`. For `river_crossing` it is `bearing(ford - location)`. Without a target it is `None`. `uphill_vec` is the unit vector of `OCTANT_VECTORS[site.uphill]`, or `None`.

### D4. Footprint growth (cells)

Let `ok(c)` be `terrain.walkable(c) and c not in blocked and c not in F`.

1. If `location.cell` is not walkable, or is blocked, raise `GenerationError(f"{map_id}: location cell not walkable")`. Set `F = {location.cell}` and `N = budget.footprint_cells`.
2. **Reach:** only when there is a water target.
   - For a river or sea target, the target cell `W` is the walkable, unblocked cell with `cheb ≤ reach` that is 8-adjacent to one of the body's cells (`waterway_cells[name]` or sea cells). Choose the nearest by `(hypot, y, x)`. For a ford target, `W` is the ford cell.
   - BFS from `location.cell` to `W` over 4-neighbours, in the order E (1,0), N (0,1), W (-1,0), S (0,-1), keeping parent pointers. Add the path cells to `F` in path order.
   - If `W` is unreachable, or there is none: the target becomes none, and a `port` then raises the water-gap error.
   - If the path made `|F| > N`, add the warning `footprint_reach_overflow:{|F|-N}`.
3. **Fill:** while `|F| < N`:
   - Candidates are the 4-neighbours of `F` for which `ok` holds.
   - Score each with `(0 if midpoint(F|{c}) == location.cell else 1, (cx-gx)**2 + (cy-gy)**2, cy, cx)`. The growth centre `g` is `location.cell + 0.5*water_vec` for a water target, and `location.cell` otherwise.
   - Add the candidate with the minimal score. When there is no candidate, raise `GenerationError(f"{map_id}: footprint_short")`.
   - `midpoint(S) = ((min x + max x) // 2, (min y + max y) // 2)`.
4. If `midpoint(F) != location.cell`, add the warning `footprint_location_offset`.
5. **Contact:** `water_contact` is true when some cell of `F` is 8-adjacent to a water cell (`terrain.is_water`), or when the ford cell is in `F`. `river_contact` is true when some cell of `F` is 8-adjacent to a cell of the target river.

### D5. Metre frame, envelope and candidates

- **Coordinates:** relative metres `p = (east, north)`, measured from the location cell centre. The world position is `(1000*cx + 500 + px, 1000*cy + 500 + py)`, and `cell_of_rel(p)` is `cell_of(world)`.
- **Envelope:**
  - `R = budget.envelope_radius_m`.
  - For `river_crossing`, `waterside_linear` and `harbour_crescent` with a `water_vec`: centre `c0 = 0.25*R*water_vec`; major unit `u = (-water_vec.y, water_vec.x)`; minor unit `v = water_vec`; semi-axes `a = R*sqrt(2)`, `b = R/sqrt(2)`.
  - For `hill_terraces` with an `uphill_vec`: `c0 = (0,0)`, `u = (-uphill.y, uphill.x)`, `v = uphill`, and the same semi-axes.
  - Otherwise: a circle, `a = b = R`, `c0 = (0,0)`.
  - `in_envelope(p)`: `((p-c0)·u / a)**2 + ((p-c0)·v / b)**2 <= 1`.
- `in_town(p)` is `cell_of_rel(p) in F and not terrain.is_water(cell_of_rel(p))`, and `admissible(p)` is `in_town(p) and in_envelope(p)`.
- **Spacing:** `s = min(600, max(60, round(0.8 * R * math.sqrt(math.pi / budget.node_count))))`.
- **Candidates:**
  - Lay a grid of step `g = s / 2` over the metre bounding box of `F`, rows from south, then columns from west.
  - Jitter each point by `((rng.random()-0.5)*0.6*g, (rng.random()-0.5)*0.6*g)`. Draw the two values even for points that are rejected afterwards.
  - Keep the points where `admissible` holds.
- **Water candidates:** consider each pair of a footprint cell `f` and a water cell `w` that are 8-adjacent. Clamp `w`'s centre (relative metres) into `f`'s square, inset 50 m. The result is `x ∈ [x0+50, x0+950]` and `y ∈ [y0+50, y0+950]`, in relative metres. Keep the result when `in_town` holds and its distance to `w`'s square is at most `water_edge_max_m`. Order the list by `(y, x)` and remove duplicates.
- **Placement spacing:** a role or approach point must be at least `0.6*s` from every placed node, and a filler at least `s`.

### D6. Node placement order and rules

The steps run in this order. `nodes` is the list of placed slots.

1. **Anchor.** `Slot("central_plaza", "anchor", "中央廣場", (0.0, 0.0))`.
2. **Crossing.** Only for `river_crossing` when the ford is in `F`: `Slot("ford_crossing", "crossing", "渡口", <ford cell centre in relative metres>)`. This point may lie outside the envelope.
3. **Gates.**
   - Bearings are taken in priority order, removing duplicates while keeping the first occurrence:
     - `forced_gates`;
     - `site.capital_bearing`;
     - the neighbours' bearings in order;
     - the bearing from the location to each ford;
     - `FALLBACK_BEARINGS`.
   - For each bearing `o`, until `budget.gate_count` gates are accepted:
     1. Walk from the mask anchor cell `midpoint(F)` along `OCTANT_VECTORS[o]` while the cell is in `F`. The first cell outside is `a`.
     2. Accept `o` only when `terrain.walkable(a)`, `a not in blocked`, and `(a, OPPOSITE[o])` is unused.
     3. For an accepted `o`, march `t = 25, 50, …` up to `1.5*R` along `unit(OCTANT_VECTORS[o])` from `(0,0)`. Keep the last `t` where `in_town(p)` holds and `p` is at least `0.6*s` from every placed node.
     4. No such `t` rejects `o`. Otherwise emit `Slot(f"{OCTANT_WORDS[o]}_gate", "gate", f"{OCTANT_ZH[o]}門", p)`.
   - Fewer gates than budgeted adds the warning `gate_shortfall:{missing}`. Zero gates raises `GenerationError(f"{map_id}: no_gate")`.
4. **Approach streets.**
   - `chain_cap = 1 if node_count < 12 else 2 if node_count < 20 else 3`.
   - `remaining = node_count - len(nodes)`.
   - `chain_budget = remaining // 3`.
   - For each gate `G`, in gate order, while `chain_budget > 0`:
     - `k = min(chain_cap, int(dist(G, 0) // (2*s)), chain_budget)`;
     - for `i` in `1..k`: the target is `G + (i/(k+1))*(0 - G)`, plus `(rng.random()-0.5)*0.4*s` times the unit perpendicular `(-dy, dx)` of `G`;
     - take the nearest candidate within `s/2` of the target that keeps `0.6*s` spacing;
     - emit `Slot(f"{G.slot_id}_road_{i}", "approach", "大街", candidate)` and remove that candidate from the candidate list;
     - `chain_budget -= 1` per emitted slot. A target with no candidate is skipped.
5. **Catalogue roles.**
   - Eligible entries have the settlement class computed in D3 in `entry.classes`, `budget.node_count >= entry.min_nodes`, and their `requires` satisfied (`"water"` needs `water_contact`, `"river"` needs `river_contact`).
   - Process them sorted by `(priority, slot_id)` while `len(nodes) < node_count`:
     - `near_anchor`: the candidate with the smallest distance to `(0,0)`.
     - `high_ground`: maximise `(terrain.band(cell_of_rel(p)), p·h)`, where `h = uphill_vec`, else `-water_vec`, else `OCTANT_VECTORS[OCTANTS[int(rng.random()*8)]]` normalised. Draw `h` once, at the first `high_ground` entry, and reuse it.
     - `periphery`: maximise `p·q`, where `q = -water_vec`, else the negated unit vector of the first gate, else `(1,0)`.
     - `ring`: the `j`-th ring entry (`j = 0,1,…` over ring entries in processing order) targets angle `θ0 + j*2π/K` at radius `0.55*R`. `K` is the number of eligible ring entries, and `θ0 = rng.random()*2π` is drawn once at the first ring entry. Take the nearest candidate.
     - `water_edge`: the water candidate nearest `(0,0)`.
     - `water_downstream`: with a river `downstream`, the water candidate maximising `p·unit(OCTANT_VECTORS[downstream])`; with sea only, as `water_edge`; with no water contact, as `periphery`.
     - Each selection keeps `0.6*s` spacing and removes the used point from its list. An entry with no valid point is skipped and adds the warning `role_unplaced:{slot_id}`.
     - Emit `Slot(entry.slot_id, entry.slot_id, entry.key_zh, p)`.
6. **Filler.** While `len(nodes) < node_count`, choose the envelope candidate that maximises the minimum distance to the placed nodes, subject to that distance being `>= s`. If none qualifies, retry with `>= 0.6*s`. Ties break by `(y, x)`. Emit `Slot(f"lane_{n:02d}", "filler", "巷弄", p)` for `n = 1, 2, …`. With no candidate left, raise `GenerationError(f"{map_id}: envelope_full")`.

### D7. Roads and directions

- **Undirected candidates.** Take the Gabriel graph over all slots: `(i, j)` is an edge iff no third slot `k` has `|k - m|**2 < (|i - j| / 2)**2`, with `m` the midpoint. Remove every edge that `crosses_water`. An edge crosses water when some sample point lies in a water cell, with the polyline sampled every ≤50 m in relative metres. A crossing is allowed only when one endpoint id has a `CROSSING_WORDS` word.
- **Forced edges.** For each gate, the consecutive pairs of `G → G_road_1 → … → G_road_k → central_plaza` are forced, provided the pair does not cross water.
- **Spanning tree.** Run Kruskal over the forced edges first, then the candidates sorted by `(length, min(order), max(order))`, where `order` is the slot's position in `nodes`. Skip an edge that would raise either endpoint's degree above `max_degree`.
  - If the forest is disconnected, add the shortest candidate edges that join two components, ignoring the degree cap.
  - Still disconnected raises `GenerationError(f"{map_id}: graph_disconnected")`.
  - Any degree above 8 raises `GenerationError(f"{map_id}: degree_overflow")`.
- **Loops.** `L = round(budget.loop_ratio * (node_count - 1))`. Add the shortest non-tree candidates, in the same sort, whose endpoints both have degree `< max_degree`, until `L` are added. A shortfall adds the warning `loop_shortfall:{L - added}`.
- **Directions.**
  - Process each node `n` in `nodes` order. Sort its incident edges by the neighbour's order. Each edge has angle `θ = atan2(dy, dx)` from `n` to the neighbour.
  - Over every injective assignment of the edges to the 8 octants (`itertools.permutations(range(8), d)`), minimise the sum of `|wrap(θ - i*π/4)|`, where `wrap` maps into `(-π, π]`. Break ties by the lexicographically smallest index tuple.
  - When some assigned edge deviates by more than `3π/8`, remove the longest incident edge that is neither forced nor in the spanning tree, both directions, and recompute the affected nodes. If no edge is removable, add the warning `direction_deviation:{slot_id}`.
  - The road `n → m` gets `OCTANTS[index]` from `n`'s assignment, and `m → n` gets its direction from `m`'s assignment.

### D8. Document data

- **Coordinates:** `x = int(round(px))`, `y = int(round(py))`. Shift everything by `ox = margin_m - min(x)` and `oy = margin_m - min(y)`. When two nodes collide, add 1 to the later node's `x_m` until it is unique.
- **Mapping keys,** in this order: `version: 1`, `kind: "settlement"`, `id: map_id`, `location_ref: location.location_id`, `options: {"map_visual_range": 2, "map_mode": "nodes"}`, `exit_prototype: {"prototype_parent": "xyz_exit", "typeclass": "typeclasses.exits.CostedXYZExit"}`, `nodes`, `roads`, `wilderness_entry`, `city_gate: None`.
- **Nodes,** in slot order: `{x_m, y_m, prototype_parent: "anchor_room" if anchor else "grid_room", key: key_zh, desc: "", anchor_key: location_id if anchor else None, typeclass: None, scene_archetype: "city_street"}`.
- **Roads:** `{source, destination, direction}`, with no `bends`. Sort by `(order(source), order(destination))`.
- **`wilderness_entry`:**
  - `shape` is one row per `y` from `min_y` to `max_y` of `F`, south row first. Each row is `"".join("#" if (x, y) in F else "." for x in range(min_x, max_x + 1))`.
  - `offset = {"dx": min_x - cx, "dy": min_y - cy}`.
  - `gates` is `[{"return_direction": OPPOSITE[o], "destination_node": gate_slot_id}]` in gate order.
- **Final checks before returning:** `document_from_data(f"content/maps/settlements/{map_id}.yaml", data)` must succeed. `lint_settlement(document, location.cell, terrain)` must report no `error`; otherwise raise `GenerationError` listing the codes. `warnings` is `sorted(set(...))`.

### D9. Workspace, CLI and safety

- `workspace.WorkspaceView.blocked_cells(map_id: str) -> frozenset[Cell]` collects the cells of every settlement document other than `map_id`. For each one, `g = doc.wilderness_geometry(locations[doc.location_ref].cell)` contributes:
  - `g.mask_cells`;
  - each gate's `gate_approach_cell(g, rd)`;
  - every location cell except the location of `map_id`;
  - every `continent.harbor_sites[*].cell`;
  - every district landmark cell where `landmark.domain == "wilderness_cell"`.
- `workspace.write_atomic(path: Path, text: str) -> None` writes `path.with_suffix(".yaml.tmp")` with `newline="\n"`, then calls `os.replace`.
- `workspace.settlement_path(root, map_id) = root / "content/maps/settlements" / f"{map_id}.yaml"`.
- **CLI:**

  ```
  generate LOCATION_ID [--root DIR] [--lore FILE] [--gates OCTANT[,OCTANT...]] [--plan-only]
  generate --missing --nation NATION [--root DIR] [--lore FILE] [--plan-only]
  ```

  - `map_id = LOCATION_ID`. A kind outside `NATIONAL_KINDS` exits 1.
  - An existing `settlement_path` exits 1 with `exists: <relative path>`, and nothing is written.
  - The terrain window is `terrain_window(location.cell, max(reach + 6, ceil(1.5*R/1000) + 6, 10))`.
  - The site comes from `analyse_site(location, window, view.roster)`, and the budget from `size_budget(location)`.
  - `--plan-only` prints the report JSON, `{"map_id", "settlement_class", "morphology", "footprint_cells", "warnings", "slots": [{"id", "role", "key", "x_m", "y_m"}]}`, and writes nothing. A normal run prints the same report, then writes `serialize_document(document_from_data(path, data), None)` atomically.
  - `--missing`: the targets are roster rows with `nation == NATION`, `kind in NATIONAL_KINDS` and no settlement file, sorted by `(-population, location_id)`. Reload the `WorkspaceView` before each one, so blocked cells include the maps written earlier. Errors are printed per location and the batch continues. The exit status is 1 if any location failed, else 0.
  - `GenerationError` and `BudgetError` print to stderr and exit 1. `WorkspaceError` exits 2.
- **Human review** (append to `docs/development/settlement-synthesis.md` § Human review):
  - Does the layout read as grown, not gridded?
  - Do the approach streets converge on the plaza?
  - Is the quay on the water side, the temple uphill and the crafts downstream?
  - Are the gates plausible toward their neighbours?

### D10. Tests (`tests/test_settlement_graph_generation.py`)

- Use `unittest.TestCase` only, with in-memory `GridTerrain`, `SiteContext` from `analyse_site`, synthetic `BudgetConfig`, a synthetic catalogue and `GenerationConfig(beast_nations=frozenset({"beastland"}))`. No shipped ids.
- A helper `_input(...)` builds a `GenerationInput`.
- The structural checks reuse `elosern_map_core.codec.document_from_data` and `fit_lint.lint_settlement`, and check independently:
  - pair symmetry;
  - unique `(source, direction)`;
  - degree ≤ 6;
  - BFS connectivity;
  - the anchor at `rel (0,0)`.
- The CLI tests use `synthetic_workspace.write_workspace(tmp)` with an added town `synthetic_burg` at (34, 8) and a second town `synthetic_hamlet` at (34, 14), both of nation `nat_a`, written through `yaml_text(locations_data)` with edits. They use a `--lore` file and compare `tree_digest` values.

Requirement → test class mapping. The decorators are added at archive:

| Requirement ID | Test class |
| --- | --- |
| `settlement-graph-generation::generation-is-deterministic-and-seeded-by-location-identity` | `DeterminismTests` |
| `settlement-graph-generation::morphology-follows-the-site-and-a-dry-port-is-refused` | `MorphologyTests` |
| `settlement-graph-generation::generated-footprints-are-connected-walkable-masks-centred-on-the-location` | `FootprintTests` |
| `settlement-graph-generation::generated-graphs-satisfy-the-structure-rules-and-the-terrain-fit-lint` | `StructureTests` |
| `settlement-graph-generation::gates-face-their-neighbours-on-distinct-walkable-approaches` | `GateTests` |
| `settlement-graph-generation::roles-come-from-the-catalogue-and-are-placed-by-the-site` | `RoleTests` |
| `settlement-graph-generation::the-generator-never-overwrites-and-batches-in-a-fixed-order` | `CommandTests` |

## Risks / Trade-offs

- [Python `random` reproducibility across versions] → Only `random()` is used, and its output is stable for a given seed. The interpreter is pinned by `.python-version`.
- [Permutation search cost] → At most `P(8,6) = 20160` assignments per node and at most 28 nodes. That is under a second.
- [Gabriel plus water pruning may disconnect a split town] → The disconnected fallback adds the shortest joining edges. A remaining failure is a reported `GenerationError`, never a written file.
- [The generated layout looks mechanical] → Fine fitting is a human step in the editor (decision 4 of the brief). The review checklist covers it.
- [Blocked cells miss monster-site cells, which are Python lore] → `check_map_sources.py` and the game adoption remain the authority. The batch changes run them after generation.

## Migration Plan

None. This change adds tooling only.
