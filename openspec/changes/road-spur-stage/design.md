# Design

## Context

`packages/map-core/elosern_map_core/roads.py`:

- `road_input` builds a `RoadInput`. It collects the footprint of every settlement document as an unwalkable cell, makes a `RoadNode` of each location whose kind is in `node_kinds` and whose document has gates, and puts every non-node point anchor into `blocked`.
- `compute_roads` builds the cost field, keeps a relative neighbourhood graph with detour repair, and routes the kept pairs cheapest first. After each road it reprices every step between two road cells to `reuse_factor` times its base cost by writing `field.graph.data`.
- `verify_roads` re-derives the open cells and checks every road independently.
- `encode_roads` calls `roads_codec.encode_road_document`.

`roads_codec.py` writes one JSON row per road, `{"cells": [...], "first": "...", "second": "..."}`, and a fingerprint over `[first, second, flat_cells]` rows. `RoadNetwork.roads` is a tuple of `(first, second, cells)`.

Two facts of the current code conflict with the tiers design and are resolved here:

1. A node needs a settlement document with gates. The placement procedure regenerates roads before any village map exists, and the village map's entrances are derived from the roads. So a village must be a spur endpoint without a document (D2).
2. A settlement footprint is an obstacle, and a non-node point anchor is blocked. A hamlet placed on a road cell would push the road off its own cell at the next regeneration. So village and hamlet cells must stay open (D3).

`content/maps/road_network.yaml` is part of the artifact's source signature. Any edit to it changes the committed bytes, so this change adds no parameter.

## Goals / Non-Goals

**Goals:**

- One spur per village, chosen and routed deterministically.
- Stage-one roads are identical with and without villages and hamlets.
- The committed artifact stays current with no regeneration.

**Non-Goals:**

- No change to stage one's cost field formula, topology, routing order or parameters.
- No new field in `content/maps/road_network.yaml`, and no bump of `FORMAT_VERSION` or `ROAD_ALGORITHM_VERSION`.
- No spur for a hamlet. A hamlet is never a road endpoint.
- No runtime change: road speed and the published road fact keep reading the cell set.
- No village or hamlet is authored here.

## Decisions

### D1. Kind constants live in the generator

```python
#: Kinds routed in stage two: one spur each.
SPUR_KINDS = ("village",)
#: Kinds whose cells stay open to roads in both stages.
OPEN_CELL_KINDS = ("village", "hamlet")
```

They are module constants of `roads.py`. `road_input` raises `RoadGenerationError` with the problem `content/maps/road_network.yaml: node_kinds lists <kind>, which is a spur or open-cell kind` when `node_kinds` contains any of them.

Alternative considered: two new lists in `road_network.yaml`. Rejected, because the file's fingerprint is in the source signature, so adding a field would change the committed artifact with no village in the input.

### D2. Spur endpoints

`RoadInput` gains `spur_nodes: tuple[RoadNode, ...] = ()`, placed last. `road_input` fills it with one `RoadNode(key, (cell,))` for every location of a kind in `SPUR_KINDS`, sorted by key, whether or not a settlement document exists. The village's own cell is its single approach.

### D3. Open cells

In `road_input`, a settlement entry whose location kind is in `OPEN_CELL_KINDS` is skipped entirely when collecting `footprints`, `blocked` and `point_gateways`. Its cell is then an ordinary cell of the cost field. No other entry changes.

Consequence: stage one never reads a village or a hamlet, so its roads are the same set of cells whether they exist or not.

### D4. Stage two

Stage two runs inside `compute_roads`, after the stage-one loop and on the same `field`, `on_road` and `reused` values, so every trunk cell already carries the reuse price.

```text
targets = {stage-one node key: its approach indices}
for village in spur_nodes, in key order:
    source = the field index of the village cell
    reach, predecessors = dijkstra(field.graph, directed=True, indices=[source], return_predecessors=True)
    for each key in targets: cost[key] = min(reach[index] for index in targets[key])
    best = the key with the smallest (cost[key], key)
    if targets is empty or cost[best] is infinite: problem "node <village>: has no road"
    end = the index in targets[best] with the smallest (reach, y, x)
    path = walk predecessors from end back to source, then reverse
    record Road(min(village, best), max(village, best), cells, spur_of=village),
        with cells ordered from the first key's end to the second's
    mark the path cells on_road and reprice, exactly as stage one does
    targets[village] = [source]
```

- "Lowest walking cost" is measured on the graph as repriced by every road routed so far. One search then gives both the chosen node and the route, and they cannot disagree.
- Ties between nodes resolve by key; ties between approach cells resolve as `_route` does today.
- Problems are collected for all villages and raised once as `RoadGenerationError`.
- `Road` gains `spur_of: str | None = None`, placed last.
- The returned tuple stays sorted by `(first, second)`. A spur always has a village end and a trunk never does, and a village originates exactly one spur and can only be targeted by later villages, so no two roads share a pair.

Alternative considered: choose the node by raw terrain cost, then route with reuse. Rejected: the chosen node could differ from the node the routed path is cheapest to.

### D5. Input check and self-check

`_check_input`: for each spur node, the cell must be in frame and open, else `node <key>: village cell <cell> is off the cost field`. A key present in both `nodes` and `spur_nodes` is `node <key>: duplicate node key`. A cell in a forbidden region is not open, so a village in a forbidden region is refused here.

`verify_roads`:

- `approaches` and the union-find cover `nodes` and `spur_nodes` together, so the existing end, connectivity and "has no road" checks apply to villages.
- For a road with `spur_of` set: `spur_of` must be one of its two keys and a spur node, else `road <a>--<b>: spur owner <key> is not a village end`.
- Each spur node must own exactly one spur, else `node <key>: owns <n> spurs`.
- A road with `spur_of` unset must have no spur node as an end, else `road <a>--<b>: trunk ends at village <key>`.

### D6. Artifact

A spur row carries one extra key; a trunk row is unchanged:

```json
{"cells":[3,4,4,4],"first":"town_a","second":"village_b","spur_of":"village_b"}
```

`roads_codec.py`:

- `encode_road_document` gains a keyword parameter `spur_owners: Mapping[tuple[str, str], str] | None = None`. For a pair in the mapping the row gains `"spur_of"`; the value must be one of the pair's two keys, else `RoadDocumentError`.
- `road_fingerprint` gains the same parameter. A spur row contributes `[first, second, flat_cells, owner]`; a trunk row contributes the current three-element list. With no spur, the digest equals today's.
- `RoadNetwork` gains `spur_owners: Mapping[tuple[str, str], str]`, placed last, an empty mapping when no row is marked. `roads` and `cells` are unchanged, so `world/maps/road_network.py` needs no edit.
- `decode_road_network` reads an optional `spur_of`: it must be a string equal to the row's `first` or `second`, else `RoadDocumentError`. It passes the owners to `road_fingerprint`.
- `nodes` holds stage-one nodes and villages together, sorted.
- `FORMAT_VERSION` and `ROAD_ALGORITHM_VERSION` stay 1. A bump would change the committed bytes; the format grows by one optional key that an artifact without villages never contains.

`encode_roads` passes `nodes` from `inp.nodes` and `inp.spur_nodes`, and the owners from the roads.

### D7. Adapter

`tools/road_network.py`:

- the summary line counts `len(inp.nodes) + len(inp.spur_nodes)` nodes;
- `write_preview` draws a road whose pair is in `network.spur_owners` with a new colour `_SPUR = (230, 120, 20)`, after the trunks, and draws each spur node's cell like a node approach;
- `Road` values for the preview are rebuilt with `spur_of` from `network.spur_owners`.

### D8. Tests

All in the existing modules, on synthetic rasters of at most 64 cells a side, with `noise_amplitude` 0 where costs are compared. Assert legality, ends and cost, never exact cell sequences on uniform ground.

`tests/test_road_network_generation.py`:

| Scenario | Shape of the test |
| --- | --- |
| One spur per village | Two towns and one village off their road: exactly one road has `spur_of`, it starts on the village cell and ends on a gate approach of a town |
| The cheapest node is chosen | A village nearer to town A in cells but separated from it by a costly band: the spur goes to town B |
| A spur reuses a trunk | A village beside a trunk far from both towns: the spur shares cells with the trunk, and with `reuse_factor` 1 it shares fewer |
| Fixed order and village targets | Villages `v_a` and `v_b` in a line beyond a town: with the nearer village sorting first, the farther village's spur ends on the nearer village's cell; with the farther village sorting first, its spur ends on a gate approach of the town, because an unprocessed village is not a candidate |
| No settlement document needed | A village location with no document gets a spur |
| Open cells | A hamlet with a point-entry document and a village with a two-cell footprint document on the straight line between two towns: the trunk passes through the hamlet cell and a village footprint cell. The test uses no `single_cell_footprint` field, so it does not depend on `single-cell-footprint-entry` |
| Stage one is independent | The trunk rows generated with and without the villages and hamlets are equal |
| No village keeps the bytes | With no village, `generate_road_network` output contains no `spur_of` and equals `encode_road_document` called with the stage-one roads and no owners |
| Refusals | A village walled off from every node, a village on an unwalkable cell, and `node_kinds` listing `village`, each raise naming the village or the kind |
| Hand-built invalid spurs | `verify_roads` reports a wrong owner, a village with two spurs and a trunk ending at a village |

Use `LOCATION_KINDS[1]` as the node kind as the module already does. Name the village and hamlet kinds through `SPUR_KINDS[0]` and the member of `OPEN_CELL_KINDS` that is not in `SPUR_KINDS`.

`tests/test_road_network_format.py`: a round trip with one spur row; byte equality of a spur-free network encoded with and without an empty owner mapping; rejection of a `spur_of` that is not an end of its row and of a non-string value.

The MODIFIED requirements keep their identifiers. Do not add `covers_requirement` for the ADDED requirements; list those tests in the hand-off.

### D9. Documentation

`docs/development/road-network.md`:

- "What a node is": add that a village is a spur endpoint by kind and cell, with no document, and that village and hamlet cells stay open to roads.
- Add a section "Spur stage" after "How a parameter reaches the roads", with the procedure of D4 in prose and the trunk and spur distinction of D6.
- In the parameter table note for `node_kinds`: spur and open-cell kinds are refused.

## Risks / Trade-offs

- [The committed artifact changes although no village exists] → Task 3.1 runs `--check` on the committed file with no regeneration. A failure stops the change.
- [A road cell on a one-cell footprint is not wilderness at run time] → Intended: a traveller following the road enters the village or hamlet at the gate on that side and leaves by the other. `single-cell-settlement-layout` derives the gates from these road cells.
- [Adding a village that sorts earlier can move a later village's spur] → Accepted by the tiers design, which fixes identifier order. The spacing validation and the settlement lint report a hamlet or an entrance that a moved spur leaves behind.
- [Generation time grows by one search per village] → Informational only. No test asserts time.
