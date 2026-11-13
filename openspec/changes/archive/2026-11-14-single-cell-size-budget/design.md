# Design

## Context

`tools/settlement_synthesis/`:

- `budget.py`: `NATIONAL_KINDS = ("capital", "city", "town", "port")`; `size_budget` rejects any other kind; `BudgetConfig.min_footprint_cells` must be at least 2.
- `workspace.py`: `WorkspaceView` holds the loaded world of one checkout root.
- `fit_lint.py`: `lint_settlement(document, location_cell, terrain)` returns findings; it sets `multi_cell = bool(footprint)` and checks containment and gates for a footprint.
- `__main__.py`: the `budget` and `lint` commands.

`single-cell-footprint-entry` provides the `single_cell_footprint` entry field, so a one-`#` mask can be a physical footprint. The committed road artifact is decoded with `elosern_map_core.roads_codec.decode_road_network`, whose `roads` are `(first, second, cells)`.

## Goals / Non-Goals

**Goals:**

- `budget` answers for a village and a hamlet.
- `lint` reports a one-cell map whose gates differ from the roads touching its cell.

**Non-Goals:**

- No generator change. `generate` keeps refusing the two kinds; `single-cell-settlement-layout` owns that.
- No change to the budget of any national kind.
- No check of the road artifact's freshness.
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

`BudgetConfig` gains `single_cell_nodes: Mapping[str, int]`, placed last, with the value `{"village": 4, "hamlet": 2}` in `DEFAULT_BUDGET`. `__post_init__` requires its keys to equal `set(SINGLE_CELL_KINDS)` and every value to be at least 2.

`size_budget` for a kind in `SINGLE_CELL_KINDS`: the area and the envelope radius come from the existing formula; `footprint_cells = 1`; `node_count = config.single_cell_nodes[kind]`; `gate_count = 0`; `loop_ratio = 0.0`. A missing or non-positive population is rejected as today. A kind outside `BUDGET_KINDS` is rejected as today. `min_footprint_cells` keeps its meaning and its floor of 2 for the national kinds.

`NATIONAL_KINDS` keeps its value. `tools/settlement_synthesis/site.py` and the `generate` command keep using it, so site analysis still lists only capitals, cities, towns and ports as neighbours. That is deliberate.

### D2. Road contacts

`WorkspaceView` gains:

```python
def road_contacts(self, cell: Cell) -> tuple[Cell, ...]:
    """The road cells that precede or follow ``cell`` on any road of the artifact."""
```

It decodes `<root>/world/maps/data/road_network.json` once per view. For every road and every index `i` with `cells[i] == cell`, it collects `cells[i - 1]` and `cells[i + 1]` when they exist. The result is sorted and unique. A missing file gives `()`. An undecodable file raises `WorkspaceError`. The artifact's freshness is not checked: writing a settlement document changes the artifact's source signature without moving any road.

### D3. Lint: entrances against road contacts

`lint_settlement` gains a keyword parameter `road_contacts: tuple[Cell, ...] | None = None`. When it is not `None` and the entry is a one-cell physical footprint:

- with contacts: the set of gate approach cells must equal the set of contacts, else one finding `fit_entrance_mismatch`, severity error, object `gates`, message listing the missing and the extra cells;
- with no contact: more than one gate is the same finding.

The `lint` command passes `view.road_contacts(cell)` for a document whose location kind is in `SINGLE_CELL_KINDS` and `None` otherwise.

### D4. Tests

`tests/test_settlement_terrain_fit.py`, synthetic workspaces only, built as the module already does. A synthetic road artifact is written with `encode_road_document` to `<root>/world/maps/data/road_network.json`.

- Budget: a village and a hamlet get one cell and the node counts of a synthetic `single_cell_nodes`; a town at the village's population still gets two cells and its tier's targets; `single_cell_nodes` with a missing kind or a value of 1 is rejected; an `elven_village` is still rejected.
- Contacts: an inner road cell has two contacts, a road's last cell has one, a cell on two roads has the union, a cell on no road and a workspace with no artifact have none, and a corrupt artifact raises.
- Lint: a village on a through road with gates on both contacts is clean; without one gate, and with an extra gate on a cell with no road, it reports `fit_entrance_mismatch` naming the cell; a hamlet with no contact is clean with one gate and reports with two; a town whose gates lie on cells with no road reports nothing.

The budget requirement is MODIFIED and keeps its identifier. Do not add `covers_requirement` for the ADDED lint requirement; list its tests in the hand-off.

### D5. Documentation

`docs/development/settlement-synthesis.md`:

- "Size budget": add the single-cell tier table (village 1 cell and 4 nodes, hamlet 1 cell and 2 nodes), and replace the statement that no supported settlement is ever a single cell with one limited to capitals, cities, towns and ports.
- "Terrain-fit lint" table: add `fit_entrance_mismatch`.

## Risks / Trade-offs

- [`budget` answers for a village while `generate` still refuses it] → Intended for the gap between this change and `single-cell-settlement-layout`. No village exists in the shipped data yet.
- [The road artifact is older than a placement] → The lint then reports a mismatch after the next regeneration, which is the purpose of the check.
