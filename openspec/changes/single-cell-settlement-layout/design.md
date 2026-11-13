# Design

## Context

`tools/settlement_synthesis/`:

- `budget.py`: `NATIONAL_KINDS = ("capital", "city", "town", "port")`; `size_budget` rejects any other kind; `BudgetConfig.min_footprint_cells` must be at least 2.
- `workspace.py`: `analysis_input(view, location, ...)` builds a `GenerationInput`; `WorkspaceView.blocked_cells(map_id)` lists cells no footprint or approach may use.
- `generate.py`: `generate_settlement(inp)` grows a footprint, places catalogue roles, builds a Gabriel-graph street network, emits the document through `document_from_data` and refuses any terrain-fit lint error. `_settlement_class` rejects kinds outside the national four. `_gate_bearings(inp)` gives the gate bearing priority order.
- `fit_lint.py`: `lint_settlement(document, location_cell, terrain)`.
- `__main__.py`: `_generate_one` refuses a kind outside `NATIONAL_KINDS`; `--missing --nation` targets `NATIONAL_KINDS` rows with no document, largest population first.
- `geometry.py`: `OCTANTS`, `OPPOSITE`, `OCTANT_VECTORS`.

`single-cell-footprint-entry` provides the `single_cell_footprint` entry field. The committed road artifact is decoded with `elosern_map_core.roads_codec.decode_road_network`, whose `roads` are `(first, second, cells)`.

The placement procedure of the tiers design regenerates the roads before it generates any village or hamlet map, so the road cells touching a location cell are known when the map is generated.

## Goals / Non-Goals

**Goals:**

- `generate` produces a valid one-cell document for a village or a hamlet, deterministically.
- The entrances of that document are exactly the road contacts of its cell.

**Non-Goals:**

- No interior, shop, guild branch or church. The role node is an outdoor node only.
- No feature nodes (ferry, mine mouth). The tiers design allows one or two; they are added later by a person in the map editor.
- No use of the role catalogue, water morphology, approach streets, fillers or loops for the two kinds.
- No change to the output of any national kind.
- No `--replace` support for the two kinds: `generate --replace` on a village or hamlet is refused with `single_cell_replace`.
- No shipped settlement document.

## Decisions

### D1. Budget

`budget.py`:

```python
#: The kinds that receive a one-cell footprint and the single-cell layout.
SINGLE_CELL_KINDS = ("village", "hamlet")
#: Every kind with a size budget.
BUDGET_KINDS = NATIONAL_KINDS + SINGLE_CELL_KINDS
```

`BudgetConfig` gains `single_cell_nodes: Mapping[str, int]`, placed last, with the default `{"village": 4, "hamlet": 2}` in `DEFAULT_BUDGET`. `__post_init__` requires its keys to equal `set(SINGLE_CELL_KINDS)` and every value to be at least 2.

`size_budget` for a kind in `SINGLE_CELL_KINDS`: the area and the envelope radius come from the existing formula; `footprint_cells = 1`; `node_count = config.single_cell_nodes[kind]`; `gate_count = 0`; `loop_ratio = 0.0`. A missing or non-positive population is rejected as today. A kind outside `BUDGET_KINDS` is rejected as today. `min_footprint_cells` keeps its meaning and its floor of 2 for the national kinds.

### D2. Road contacts

`WorkspaceView` gains:

```python
def road_contacts(self, cell: Cell) -> tuple[Cell, ...]:
    """The road cells that precede or follow ``cell`` on any road of the artifact."""
```

It decodes `<root>/world/maps/data/road_network.json` once per view. For every road and every index `i` with `cells[i] == cell`, it collects `cells[i - 1]` and `cells[i + 1]` when they exist. The result is sorted and unique. A missing file gives `()`. An undecodable file raises `WorkspaceError`. The artifact's freshness is not checked: writing a settlement document changes the artifact's source signature without moving any road.

`GenerationInput` gains `road_contacts: tuple[Cell, ...] = ()`, placed last. `analysis_input` fills it for a kind in `SINGLE_CELL_KINDS` and uses `reach = 1` there.

### D3. Entrances

An entrance is an octant, the bearing from the location cell to a neighbouring cell. In order of precedence:

1. `inp.forced_gates`, when not empty.
2. One octant per road contact.
3. With no contact, for a hamlet: the first bearing of `_gate_bearings(inp)` whose neighbour cell is walkable and not in `inp.blocked`. None gives `GenerationError("<map>: no_gate")`.
4. With no contact, for a village: `GenerationError("<map>: no_road: no road cell touches the village cell")`.

Entrances are then sorted in the order `n, ne, e, se, s, sw, w, nw`.

### D4. Slots

`R = min(400, max(60, inp.budget.envelope_radius_m))` metres. A point "toward octant `o` at distance `d`" is `d` times the unit vector of `OCTANT_VECTORS[o]`. `<word>` is `OCTANT_WORDS[o]`. `Slot.role` values are the existing `"anchor"` and `"gate"` plus the new `"role"` and `"end"`.

Village:

| Slot id | Role | Position |
| --- | --- | --- |
| `village_green` | anchor | `(0, 0)` |
| `village_end_<word>` for each entrance | gate | toward the entrance at `R` |
| `village_end_<word>` of the opposite octant, only when there is one entrance | end | toward the opposite octant at `R` |
| `shrine_front` | role | toward the shrine octant at `R / 2` |

The shrine octant is the first octant, stepping clockwise from the octant two steps clockwise of the first entrance, that no other slot uses.

Hamlet:

| Slot id | Role | Position |
| --- | --- | --- |
| `crossing` | anchor | `(0, 0)` |
| `homestead_front` | role | toward the second entrance at `R`, or toward the opposite of the only entrance |
| `lane_<word>` for the third and each later entrance | gate | toward that entrance at `R` |

Gates:

- Village: one gate per entrance, `return_direction = OPPOSITE[entrance]`, destination the matching `village_end_<word>`.
- Hamlet: the first entrance's gate leads to `crossing`; the second entrance's gate leads to `homestead_front`; each later one leads to its `lane_<word>`.

A village therefore has `2 + max(2, entrances)` nodes and a hamlet `max(2, entrances)`, which are at least the budget's node counts. The anchor may be a gate destination: the lint's gate-side check skips a node at the anchor position.

Labels (`key_zh`) come from a new table in `roles.py`, keyed by kind and settlement class. They are role labels that the prose pass replaces, and no test reads them:

```python
SINGLE_CELL_LABELS = {
    ("village", "human_town"): {"anchor": "村中綠地", "role": "教堂前", "end": "{octant}村口"},
    ("village", "beast_town"): {"anchor": "圖騰場", "role": "祖靈祭壇前", "end": "{octant}寨口"},
    ("hamlet", "human_town"): {"anchor": "岔路口", "role": "農舍前", "end": "{octant}小徑"},
    ("hamlet", "beast_town"): {"anchor": "圖騰柱下", "role": "火塘邊", "end": "{octant}小徑"},
}
```

`{octant}` is filled from `OCTANT_ZH`.

### D5. Class and morphology

`_settlement_class` accepts the two kinds: a nation in `config.beast_nations` gives `beast_town`, any other gives `human_town`. The reported morphology is `tribal_ring` for `beast_town` and `crossroads` otherwise. This is how "reuse the tribal morphology at single-cell scale" is realised: the class selects the tribal vocabulary and label, and the geometry of D4 is shared, because one cell has no room for a ring of roles.

### D6. Roads and the document

Roads are a star: for each non-anchor slot, one road anchor → slot with `direction` the slot's octant, and one road slot → anchor with the opposite direction. Every non-anchor slot sits on its own octant, so no node has two outgoing roads in one direction.

`generate_settlement` branches at its top: a kind in `SINGLE_CELL_KINDS` calls a new `_generate_single_cell(inp)`, which builds the slots, calls the existing `_node_coordinates`, and emits a document with the same fixed fields as `_document_data` and this entry:

```python
"wilderness_entry": {
    "shape": ["#"],
    "offset": {"dx": 0, "dy": 0},
    "single_cell_footprint": True,
    "gates": gates,
},
```

It then runs `document_from_data` and `lint_settlement` exactly as the national path does and returns a `GenerationResult` whose `footprint` is the one location cell. No random number is drawn, so the output is deterministic.

### D7. Lint: entrances against road contacts

`lint_settlement` gains a keyword parameter `road_contacts: tuple[Cell, ...] | None = None`. When it is not `None` and the entry is a one-cell physical footprint:

- with contacts: the set of gate approach cells must equal the set of contacts, else one finding `fit_entrance_mismatch`, severity error, object `gates`, message listing the missing and the extra cells;
- with no contact: more than one gate is the same finding.

The `lint` command passes `view.road_contacts(cell)` for a document whose location kind is in `SINGLE_CELL_KINDS` and `None` otherwise. `_generate_single_cell` passes `inp.road_contacts` unless `forced_gates` is set.

### D8. Commands

- `_generate_one` accepts `BUDGET_KINDS`. With `replace=True` and a single-cell kind it prints `single_cell_replace: <location_id>` and returns 1.
- `--missing --nation NATION` targets `BUDGET_KINDS`. A new optional `--kind KIND`, valid only with `--missing`, narrows the batch to one kind; an unknown kind is an argument error. Order stays descending population, then identifier.

### D9. Tests

Synthetic workspaces only, built as the two modules already do. A synthetic road artifact is written with `encode_road_document` to `<root>/world/maps/data/road_network.json`.

`tests/test_settlement_terrain_fit.py`:

- budget: a village and a hamlet get one cell and the configured node counts from a synthetic `single_cell_nodes`; a town at the same population still gets two cells; `single_cell_nodes` with a missing kind or a value of 1 is rejected; an `elven_village` is still rejected.
- lint: matching gates pass; a missing gate, an extra gate, and two gates with no contact each give `fit_entrance_mismatch`; a national document is unaffected.

`tests/test_settlement_graph_generation.py`:

- through road: a village on a road cell has two gates whose approach cells are the two contacts, and four nodes; a hamlet there has two gates and two nodes;
- spur end: a village whose cell is the last cell of a road has one gate and four nodes;
- junction: three contacts give three gates, a village with five nodes and a hamlet with three;
- no road: a hamlet has one gate and two nodes; a village is refused with `no_road`;
- every generated document has a one-cell physical footprint on the location cell, loads through the codec, and has no lint error;
- determinism: two runs give identical bytes;
- beast nation: the class is `beast_town`, the morphology `tribal_ring`, and the node and gate counts equal the human case;
- batch: `--missing --nation` writes villages and hamlets, `--kind hamlet` writes only hamlets, and `--replace` on a village exits 1 with `single_cell_replace`.

Assert counts through the budget and the contact set, not through copied labels. Do not add `covers_requirement` for the ADDED requirements; the MODIFIED ones keep their identifiers.

### D10. Documentation

`docs/development/settlement-synthesis.md`:

- "Size budget": add the single-cell tier table (village 1 cell and 4 nodes, hamlet 1 cell and 2 nodes) and replace the sentence that no supported settlement is ever a single cell.
- Add a section "Single-cell layout" after "Generation" with D3 to D6.
- "Terrain-fit lint" table: add `fit_entrance_mismatch`.
- "Commands": add `--kind`.
- "Human review": add "Does a four-node village and a two-node hamlet give enough to do on arrival?" and "Do the entrances match the roads on the continent capture?".

`.agents/skills/map-data-authoring/references/settlements.md`, "Creating a new local map": state that a village or hamlet is generated with the same command after the road network is regenerated.

## Risks / Trade-offs

- [The road artifact is older than the placement, so a new village has no contact] → A village is refused with `no_road`; a hamlet gets one entrance, and the lint reports `fit_entrance_mismatch` once the roads are regenerated.
- [A later regeneration moves a spur and leaves a map with a stale gate] → The lint reports it. The fix is to regenerate that map by deleting its file and running `generate` again, then redoing its prose.
- [A road passing diagonally gives a diagonal gate] → Supported: gate directions are any of the eight octants, and the approach cell is the diagonal neighbour.
