# Design

## Context

See proposal.md (Why). The tools come from `settlement-terrain-fit`, `settlement-graph-generator` and `settlement-rework-and-prose`, all landed:

- `uv run --locked python -m tools.settlement_synthesis {site,budget,lint,generate,brief,prose}`;
- `place_sites.py`;
- `check_map_sources.py`;
- `regenerate_partition.py`;
- `capture_map.py`.

`generate --missing --nation grandia` processes the roster in `(-population, id)` order and reloads the workspace between maps, so each footprint avoids the ones written before it.

Proposal-time observations from the site probe show distances in cells, Euclidean. They are guidance only, because the generator's own reach test decides:

- `capital_grandia`: river 4–5, ford (1953, 1268).
- Ports:
  - `port_golden_sheaf`: sea 4;
  - `port_south_cape`: sea 5;
  - `port_east_bay`: river 2, sea 3;
  - `port_dawnlight`: sea 2;
  - `port_tide_wind`: sea 2.

## Goals / Non-Goals

**Goals:**
- Every Grandia national settlement has a lint-clean, prose-complete local map.

**Non-Goals:**
- city gates from the starting room;
- interiors;
- Python lore;
- fine fitting;
- the other nations.

## Decisions

### D1. Order of work

Plan everything first and relocate where needed. Then generate the batch, write the prose, and verify. Relocations happen before any generation, so every footprint is grown from the final cells.

### D2. Relocation rule (explicit; no other location edit is allowed)

There are two triggers:

- (a) `generate <id> --plan-only` fails with `water_gap` for a port;
- (b) `capital_grandia`'s plan morphology is not `river_crossing`.

For a triggered location `L`, the target cell `T` is:

- for (a), `site L --radius 12`'s `sea.nearest_cell` when `sea` is present, else the first `rivers[0].nearest_cell`;
- for (b), the cell of the first `fords` entry whose waterway is `imperial_river`, from `site capital_grandia --radius 12`.

For `k = 1, 2, 3`:

1. Compute `c_k = L.cell + round_away(k * (T - L.cell) / max(|T.x - L.x|, |T.y - L.y|))`. `round_away` rounds halves away from zero.
2. Reject `c_k` if:
   - `place_sites.py` on a candidate file `[{"id": "<L>", "cell": [c_k.x, c_k.y]}]` (the cell is a two-item JSON list) reports `walkable=False` or `water_cell=True`;
   - the region or nation differs from `L`'s current values;
   - `c_k` equals any location or harbour cell.
3. Otherwise set the cell temporarily and rerun `generate L --plan-only`. Accept `c_k` when (a) no longer fails, or when (b) reports `river_crossing`. Otherwise restore the old cell and try the next `k`.

If no `k ≤ 3` is accepted, restore the cell. Then:
- for (a), report the location as an unresolved water gap. Do not generate it, and the hand-off lists it for the user.
- for (b), keep the original cell and the plan's morphology, and report it.

Record every accepted move as `id: old → new` in the hand-off.

### D3. Prose

Follow `docs/development/settlement-synthesis.md` § Prose pass for every node of every generated map. Grandia flavour comes from `docs/lore/settlement-locations.md`:

- an imperial, magic-research-heavy human nation;
- the capital is the only academy town, with the largest academy and temple;
- ports centre on merchant exchanges and the quay;
- plains towns are agricultural market towns.

Write one prose JSON per map in the scratchpad and apply it with `prose`.

### D4. Test-suite cost gate

About 230 new rooms spawn in every `sync_grid()` test. Record the `Ran N tests in X s` line of `world.maps.tests.test_bootstrap` before generation (baseline) and after the batch.

- If `X_after > 2.5 * X_baseline`, or `X_after > 600`, stop before committing and report both numbers.
- The data change is then blocked on a follow-up change: either test-scoped settlement publication or faster synchronization. Design that follow-up then.

## Risks / Trade-offs

- [A batch member fails generation for a reason other than a water gap, such as `footprint_short` or `envelope_full`] → Report it and leave it ungenerated. Do not hand-author a replacement in this change.
- [A relocation crosses a district boundary] → Accepted. The partition is regenerated, and the hand-off lists the move for user review.
- [Monster sites or quest anchors near a moved cell] → `check_map_sources.py` and the adoption test run in task 4. A failure there blocks the commit.

## Migration Plan

Pre-release: there is no migration. Rollback is `git revert` of the data commit followed by partition regeneration.
