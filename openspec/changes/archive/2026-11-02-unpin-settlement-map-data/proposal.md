# Proposal

## Why

The planned settlement work adds 59 settlement maps for the national cities, towns and ports and reworks `capital_altoria`, whose node positions are unresearched development data. Several specs and tests still copy that settlement data. They pin the settlement roster (`["capital_altoria", "village_ciaran"]`), Altoria node coordinates such as `(3050, 150)` and `(3500, 2850)`, the 40-cell capital mask, its `(847, 1020)` origin, the 21 room and 52 exit counts, walk durations (724 s, 811 s, 394 s) and a gate-to-plaza key chain (南門 → 南大道 → 大道北段 → 中央廣場). Any new settlement document or moved Altoria node breaks them. Specs and tests have to state logic, not game data. Otherwise every later data change also needs a spec or test edit.

## What Changes

- Rewrite the pinned tests so that each expected value comes from the authored settlement documents or a synthetic fixture. Expected values are never copied literals. The pins fall into these classes:
  - registry rosters → the set of discovered settlement documents;
  - local coordinates, entrance coordinates and knowledge keys → read from the document's nodes;
  - mask cell count and origin → derived from the document's `wilderness_entry`;
  - room and exit counts → the document's node and road counts;
  - mask shape, anchor and approach cells, and gate counts → the document geometry and `gate_approach_cell`;
  - durations → a bracketing relation between the charged seconds and the authored polyline metres;
  - the walk chain → a shortest route from the city-gate node to the anchor.
- Make the metric-cutover seeding in `world/maps/tests/test_bootstrap.py` seed only the maps and nodes its historical table lists. Adding a settlement then no longer raises `KeyError`.
- Remove the coordinate pins from the scenarios of four requirements. The behaviour stays the same:
  - `sample-city-altoria`: entrance and wilderness-gate rooms;
  - `grid-room-sync`: Limbo bridge destination;
  - `wilderness-gateway`: registry roster and return-exit destinations, two requirements.
- Prove the change with a canary step, as evidence only. Add one throwaway settlement document and perturb Altoria: move two nodes, add one node and a road pair, add two gates whose return directions are `s` and `e`, and shift its location cell by one. Run the affected test modules, then restore the data. Nothing from the canary is committed.
- No production code, content, docs or shard manifest changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `sample-city-altoria`: "The sample city connects to the rest of the world through exactly one bridging exit". The entrance becomes the authored `city_gate` node, and wilderness-gate rooms carry one city exit per authored road. Neither keeps a fixed coordinate or a fixed single westward link.
- `grid-room-sync`: "A single authored, idempotent Exit bridges Limbo and the sample city". The bridge targets the city-gate node's current coordinate.
- `wilderness-gateway`: "WILDERNESS_ENTRY_REGISTRY links a grid-placed anchor to an authored wilderness footprint and gates" now holds one entry per settlement document that declares an entry, with no fixed roster, cell count or origin. "WildernessReturnExit routes every registered approach-cell-and-direction pair back to the grid" returns to the gate node's current coordinate.

## Impact

- Tests, edited in place with their requirement IDs kept:
  - `world/lore/tests/test_anchor_placement.py`
  - `world/lore/tests/test_wilderness_entry.py`
  - `world/maps/tests/test_bootstrap.py`
  - `world/maps/tests/test_city_walkthrough.py`
  - `world/maps/tests/test_city_movement_cost.py`
  - `world/maps/tests/test_city_wilderness_roundtrip.py`
  - `world/maps/tests/test_geography_source.py`
  - any further module the canary run shows failing because of a copied settlement value.
- Traceability: only MODIFIED requirements, with names unchanged, so every `covers_requirement` ID stays valid.
- Test-data ledger: the `Data-contract test:` first docstring lines stay unchanged.
- Residual data assumptions are kept on purpose and documented in design.md D4. Tests still find the capital's gates with `gate_for("n")` and `gate_for("w")`, and its anchor node is still `central_plaza`. `altoria-capital-river-rework` keeps both properties.

## Batch:

- depends-on: none
- conflicts: none with other changes in this batch at file level. It edits only `world/**/tests/*.py` and `openspec/specs` deltas, which no other change in the batch touches.
- must land before: `altoria-capital-river-rework`, `grandia-settlement-maps`, `altoria-settlement-maps` and `valhalla-settlement-maps`. Each of them adds or moves settlement data that the current pins reject.
