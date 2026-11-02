# Tasks

Ground rules:
- Edit only the files a task names.
- Copy every contract, constant, order and formula from design.md D1–D9 verbatim.
- Use `rng.random()` only.
- Never write files under `content/` of the real repository, except as manual evidence in task 6.2, which you revert.
- Add no `@covers_requirement` decorators for `settlement-graph-generation::*` (Workflow follow-up).
- Run tests as `uv run --locked python -m unittest tests.test_settlement_graph_generation`, standalone.

## 1. Role catalogue

- [ ] 1.1 Create `tools/settlement_synthesis/roles.py` with `PLACEMENTS`, `RoleEntry` and `DEFAULT_CATALOGUE`. `DEFAULT_CATALOGUE` is a tuple holding exactly the 25 rows of the D2 table, in table order, with `frozenset` classes using the full class names from D1. Add a module-level check that raises `ValueError` at import when two entries share a `slot_id` and their `classes` overlap. Check: `uv run --locked python -c "from tools.settlement_synthesis.roles import DEFAULT_CATALOGUE as c; print(len(c))"` prints `25`.

## 2. Generator core

- [ ] 2.1 Create `tools/settlement_synthesis/generate.py` with the D1 contracts: constants, `GenerationConfig`, `GenerationInput`, `Slot`, `GenerationResult`, `GenerationError` and `seed_for`. Implement the class, reach and morphology logic (D3) as private functions `_settlement_class(inp)` and `_morphology(inp, reach) -> tuple[str, target]`. Here `target` is `None`, a river `WaterContact`, the sea `WaterContact`, or the ford `PointFeature`.
- [ ] 2.2 Implement footprint growth (D4) as `_grow_footprint(inp, morphology, target, reach) -> tuple[frozenset[Cell], bool, bool, list[str]]`. The tuple holds the footprint, `water_contact`, `river_contact` and the warnings.
- [ ] 2.3 Implement the frame, envelope and candidates (D5) and node placement (D6), in exactly the D6 step order and with exactly the documented `rng` draw points.
- [ ] 2.4 Implement roads and directions (D7) and document data (D8), then `generate_settlement` itself, which calls them in order and runs the final validation and lint.

  Check: a scratch snippet generates a 10-node `human_town` on a 30×30 all-land `GridTerrain` and prints `len(result.data["nodes"]) == 10` and an empty lint error list.

## 3. Generator tests (synthetic)

- [ ] 3.1 Create `tests/test_settlement_graph_generation.py` with the D10 helpers. They build `GridTerrain` windows (open plain, river column, coast, northward slope), a `SettlementRef`, `analyse_site`, a synthetic `BudgetConfig` and catalogue, and `_input(...)`.
- [ ] 3.2 `DeterminismTests` covers the two scenarios:
  - serialise twice with `serialize_document(document_from_data(path, data), None)`, compare the bytes, then re-parse with `parse_document` and serialise again for the same bytes;
  - the ids `site_a` and `site_b` produce different coordinate sets.
- [ ] 3.3 `MorphologyTests` covers the six-site selection order and the dry port. The dry port's error message contains the map id and `water_gap`.
- [ ] 3.4 `FootprintTests` covers open ground (5 cells, 4-connected by BFS, midpoint equal to the location), blocked cells with river reach (no blocked cell in the footprint; some footprint cell is 8-adjacent to a river cell) and the corridor (all cells west of the location walkable, east blocked; the warning `footprint_location_offset` is present).
- [ ] 3.5 `StructureTests`: for the open, river and coast sites, assert:
  - node count;
  - exactly one `anchor_room`, whose `anchor_key` is the location id;
  - that `rel_m` of the anchor slot is `(0, 0)`;
  - unique non-negative coordinates;
  - every road's reverse present;
  - unique `(source, direction)`;
  - degree ≤ 6;
  - BFS connectivity;
  - the loop count `len(roads)/2 - (n-1)` equals `round(ratio*(n-1))`, or a `loop_shortfall` warning names the deficit;
  - no `lint_settlement` error;
  - every direction within 2 octants (`octant_distance`) of its segment bearing, or a `direction_deviation` warning.
- [ ] 3.6 `GateTests` covers the forced `s`, the capital to the north, the blocked eastern approach and the gate budget 3, expecting bearings `s`, `n`, `w`. It also checks the gate-node dot product with the bearing vector is ≥ 0.
- [ ] 3.7 `RoleTests` covers the class and budget filter, the dry versus river site for a `requires: "river"` entry (with the 600 m check through `point_to_cell_distance`), uphill (a `high_ground` slot with `rel_m.y > 0`) and the downstream river flowing east (the `water_downstream` slot has the maximum `x` among that site's water candidates; recompute the candidates in the test from D5 independently).

  Check: the module passes in under 60 seconds.

## 4. Workspace and CLI

- [ ] 4.1 Add `blocked_cells`, `write_atomic` and `settlement_path` to `tools/settlement_synthesis/workspace.py` (D9). Check: `uv run --locked python -c "from pathlib import Path; from tools.settlement_synthesis.workspace import load_workspace; v=load_workspace(Path('.')); print(len(v.blocked_cells('town_scarp')) > 0)"` prints `True`.
- [ ] 4.2 Add the `generate` subcommand to `tools/settlement_synthesis/__main__.py` exactly as D9 describes: arguments, report JSON, refusal of existing files, `--plan-only`, the `--missing --nation` order with a reload per location, and the exit codes.
- [ ] 4.3 Add `CommandTests` to the test module, covering the existing-document and the plan-only-and-batch scenarios:
  - Generating `synthetic_place` exits 1 with `exists:`, and the digest is unchanged.
  - `generate --missing --nation nat_a --plan-only` exits 0 and leaves the digest unchanged.
  - `generate --missing --nation nat_a` exits 0 and writes `synthetic_burg.yaml` before `synthetic_hamlet.yaml`. Assert from the printed reports' order. The two footprints, recomputed from the written YAML through `parse_document` and `wilderness_geometry`, are disjoint.
  - `lint --root tmp` afterwards exits 0.
- [ ] 4.4 Add `"tests.test_settlement_graph_generation"` to shard `index` 4 `labels` in `.github/top-level-shards.json`. Check: `tests.test_evennia_test_optimization_contract` passes, run as in the `settlement-terrain-fit` task 5.4 command.

## 5. Documentation

- [ ] 5.1 In `docs/development/settlement-synthesis.md`, add a section "Generation" summarising D3–D8: classes, morphologies, footprint growth, placement order, roads and directions, and output. Append the D9 checklist items to "Human review".
- [ ] 5.2 In `.agents/skills/map-data-authoring/references/settlements.md` § "Creating a new local map", add the alternative "For a national settlement, generate it: `uv run --locked python -m tools.settlement_synthesis generate <location_id> --plan-only`, then without `--plan-only`; the generator never overwrites, and the prose pass is described in `settlement-rework-and-prose`'s documentation." Use the Edit tool. Check: `grep -n "settlement_synthesis generate" .agents/skills/map-data-authoring/references/settlements.md` prints a line.

## 6. Gates and manual evidence

- [ ] 6.1 Run `tools.test_data_lint check`, `tools.spec_traceability check`, `tools.contract_gate` and `openspec validate settlement-graph-generator --strict`. Check: all succeed.
- [ ] 6.2 Manual evidence, not committed:
  - run `uv run --locked python -m tools.settlement_synthesis generate town_scarp --plan-only` and `... generate port_white_sail --plan-only`, and record their morphologies and warnings in the hand-off;
  - then run `generate town_scarp` for real, then `lint town_scarp`, which must exit 0, and `check_map_sources.py`, which must report no structure error and no game-adoption problem other than `stale_partition`;
  - then `rm content/maps/settlements/town_scarp.yaml`.

  Check: `git status --porcelain content` prints nothing.

## Workflow follow-up

- At archive, decorate the D10 test classes' methods with their `settlement-graph-generation::*` IDs and rerun `tools.spec_traceability check`.
