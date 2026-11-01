# Design

## Context

See proposal.md for the motivation. Current state:

- `world/maps/tests/test_wilderness_geography_contract.py` is a `Data-contract test:` module. It is registered in `tools/test_data_freeze.json` and `tools/test_data_lint_seed.json` under the reason "authored continental terrain, waterway and anchor-region data contract". The first docstring line must stay byte-identical, or the ledger check fails.
- On clean master it fails `test_fords_lie_on_the_river_with_the_principal_on_the_capital_line` (43.1 > 5) and `test_anchor_relationships_to_the_forest_edge` (225 > 15).
- `tools.spec_traceability` indexes only `openspec/specs/*/spec.md`. A `@covers_requirement` ID that is not in a main spec is reported as `unknown-requirement-id`. An ID that no test names is reported as uncovered. Baseline: 2677 requirements, 0 uncovered, 0 errors.
- The OpenSpec CLI (1.14.1) refuses a MODIFIED block that drops a current scenario name. So a requirement whose scenario titles pin data must be REMOVED and ADDED under a new name, which changes its traceability ID.
- `elosern_map_core.schema.LOCATION_KINDS` and `world.lore.anchors.AnchorKind` hold the same six values today. `world/maps/geography.py::_compose_locations` reports a candidate problem for a schema kind that `AnchorKind` lacks, but no test pins that the two vocabularies agree.
- `web/webclient/presentation/world_map_geometry.py::_place_geometry` maps a kind to `hidden` for ELVEN_VILLAGE/DUNGEON, `capital` for CAPITAL and `settlement` otherwise, and maps harbour sites to `harbour`. The frontend (`web/webclient-app/lib/world_map_view.js`, `WorldMapGlyph.vue`, `map_panels.js` `PLACE_KINDS`) and `docs/development/map-panel-protocol.md` already accept `settlement`. No production change is needed.

Every probe below was checked against the shipped data at commit 16f1e0e4 with the map-core functions:
- every non-ford land cell of every rasterized waterway (8544 cells) is inland water and not walkable;
- every declared ford of every waterway is on its own route and walkable;
- every stem row 0..2000 is a closed wall at its centre (no passes are declared);
- the cells directly south and north of each border ford are walkable;
- with the `_RunComponents` row-run index, blocking the source column plus all three fords disconnects those two bank cells; each other blocking combination in the test keeps them connected, and so does every single remaining ford;
- the derived flip columns all show `western_hills_valleys`/`northwest_highland_forest` and `altoria`/`valhalla`;
- every stem vertex south of the forest edge classifies as `central_mountains` at its centre and not at centre ± (half_width + 1).

## Goals / Non-Goals

**Goals:**
- Turn every authored map value in the wilderness-geography contract into an invariant derived from the authored data itself.
- Make the anchor kind vocabulary and the world-map place classification explicit, tested logic.
- Keep traceability green at every commit on the feature branch.

**Non-Goals:**
- No production code, content YAML, protocol document, ledger or shard-manifest edit.
- No change to lore demographic pins (`test_nations.py`) or to `test_river_cells_block_steps_and_the_ford_permits_the_crossing`. Both are listed as open questions in proposal.md.

## Decisions

### D1. Delete a pin; do not loosen it

A test that only pins an authored position, share or count is deleted, or its assertion is removed. Widening a tolerance (for example 43 → 50) would still break on the next authoring edit. Deleted tests:
- `test_settlement_derived_anchor_cells_resolve_to_altoria_territory`
- `test_anchor_relationships_to_the_forest_edge`
- `test_effective_rule_targets_are_unchanged` (it copies the `NATION_REGISTRY` territory shares that `world/lore/tests/test_nations.py` already pins)

Assertions removed from surviving tests:
- the forest-edge mean ≈1920, the count of distinct edge rows and the 20 % share;
- the 0.43/0.30/0.27 nation shares;
- the "nation-less region spans >1 claim" check and the two named-region `nation_key is None` checks;
- the three-ford unpacking and the capital-line check;
- the capital-river and imperial-river mouth regions;
- the fixed probe cells `(900, 1042)`, `(900, 2350)`, `(700, 1960)`;
- `ridge_passes == ()` and the X1300..1520 band;
- the `ridge_center_x(100) != ridge_center_x(1200)` bend check.

### D2. Derive probes from the authored data

Where a pin stood in for logic, the probe now comes from the data. The exact code is in tasks.md.

- Flip columns: `range(mouth_x + 1, source_x, max(1, (source_x - mouth_x) // 6))`.
- Corridor rows: the stem vertex rows south of the forest edge, probed at centre ± (`mountain_corridor_half_width` + 1).
- Displayed-border junction row: `waterway_routes["border_river"][0][1]` instead of `1410`.
- Ridge barrier: every stem row outside the declared `ridge_passes` row ranges has `is_closed_ridge_cell((ridge_center_x(y), y))`.
- Crossing-only-at-fords: the bank cells `(fx, fy - 1)` and `(fx, fy + 1)` beside `waterway_fords["border_river"][0]` replace the two capitals.
- River water: every land cell of the full waterway raster that is not a declared ford of any waterway is inland water and invalid.

Alternative considered: keep the capital endpoints but drop only the line check. Rejected because "both capitals lie west of the river source and Valhalla lies north of the river" is itself a position pin.

### D3. The kind vocabulary is logic; using every kind is data

`test_every_supported_kind_appears_without_a_fixed_roster_count` asserted that shipped content uses every `AnchorKind`. It would fail if content dropped the last dungeon. It becomes `test_anchor_kinds_match_the_schema_location_kinds`, which checks that `{k.value for k in AnchorKind} == set(LOCATION_KINDS)` and that one synthetic location per schema kind composes with that kind. The synthetic locations reuse the cell of an existing shipped location, because `_validate_cells` only requires a mainland cell. So no new coordinate becomes a dependency.

### D4. Keep national-settlement reference checks; drop the magnitude comparison

`test_national_settlements_carry_nation_and_population` keeps:
- the nation is a `NATION_REGISTRY` key;
- the population is a positive int;
- `floors` is None.

These are reference and schema-integrity checks that `test-data-independence` permits. It drops "population < its capital's population" (an authored-magnitude comparison) and `assertTrue(settlements)` (it would require content to keep using these kinds).

### D5. World-map classification test enumerates the vocabulary explicitly

The test gets an explicit `{AnchorKind → (wire kind, visit-only)}` table plus `assertEqual(set(expected), set(AnchorKind))`. Adding a seventh kind then forces a classification decision in that test. The expected values are literals, not the production rule recomputed. A synthetic harbour site covers `harbour`.

### D6. Traceability ordering: old IDs during apply, re-anchor after sync

Four requirements change ID:

| Old ID | New ID |
|---|---|
| `wilderness-terrain::region-for-coordinates-is-a-pure-deterministic-function-covering-the-whole-bounded-map` | `wilderness-terrain::the-coordinate-classifier-is-a-pure-deterministic-function-over-the-whole-bounded-map` |
| `wilderness-terrain::terrain-and-political-control-follow-authored-geography` | `wilderness-terrain::terrain-and-political-control-derive-from-authored-geography` |
| `lore-registries::anchor-registry-covers-capitals-elven-villages-and-known-dungeons` | `lore-registries::anchor-registry-composes-every-declared-location-kind` |
| `continental-geography::the-known-continent-has-frozen-geographic-declarations` | `continental-geography::known-continent-geographic-declarations-are-frozen` |

During apply, the main specs still hold only the old IDs. So every surviving and newly added decorator uses the OLD ID, and `uv run --locked python -m tools.spec_traceability check` stays at 0 errors / 0 uncovered. The archive step syncs the delta, so the old IDs disappear and the new ones appear. Task group 5 then replaces each old literal with its new one. The full file list is in tasks.md: `world/maps/tests/test_wilderness_geography_contract.py`, `world/maps/tests/test_wilderness_provider.py`, `world/lore/tests/test_anchors.py`, `world/lore/tests/test_anchor_placement.py`, `world/lore/tests/test_wilderness_regions.py`. This follows the project's established "post-sync re-pin" practice (for example `2026-08-29-add-subrace-starting-kits`).

Rejected alternative: keep stale scenario titles under MODIFIED to avoid ID churn. Rejected because the titles themselves ("Nine geographic anchors", "capital_altoria's derived anchor cells…") are the data pins being removed.

## Risks / Trade-offs

- [Risk] Removing pins weakens detection of an accidental geometry edit, such as a mistyped forest-edge vertex. → Mitigation: authoring diagnostics, the editor preview and the remaining invariants (reachability, claim/region agreement, ford and water semantics, political-line derivation) still catch structural mistakes. A deliberate shape is reviewed by a person in the map editor, not by a test.
- [Risk] `_RunComponents` is built five times plus once per ford, as it is today. Runtime stays about the same as on master.
- [Risk] A weak worker updates decorators to new IDs during apply, and traceability reports `unknown-requirement-id`. → Mitigation: task 5 is explicitly post-sync and its own acceptance check names the expected counts.
- [Trade-off] `test_classifier_and_claims_flip_across_the_river` still names the regions `western_hills_valleys`/`northwest_highland_forest` and the nations `altoria`/`valhalla`. These are the border river's defined role in the classifier (code-owned `REGION_KEYS`) and in the requirement body, not authored coordinates.

## Migration Plan

None. The project is pre-release and only tests and specs change. Rollback is reverting the feature-branch commits.
