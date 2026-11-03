# Tasks

The implementation is one engineer-day of selector plumbing and mechanical fixture cutover. Apply in the root-defined feature worktree later; this proposal itself changes no production code. All paths below are relative to the repository root. Do not run builds, tests, lints or formatters mid-edit; execute the acceptance checks together in section 5 after all edits land. Each task's acceptance describes the result that final verification must observe.

## 1. Keep one real synchronization path

- [x] 1.1 In `world/maps/bootstrap.py`, implement `sync_grid(*, settlement_ids: Iterable[str] | None = None) -> SyncReport`, `sync_wilderness(*, settlement_ids: Iterable[str] | None = None) -> None` and `_selected_settlement_graphs(settlement_ids: Iterable[str] | None) -> tuple[SparseSettlementGraph, ...]` exactly as design decision 1 defines. `None` retains the current full-roster order, explicit IDs deduplicate/sort, string/type errors and unknown IDs reject before planning/writing, and explicit empty selection performs no persistent work. Feed selection into the existing plan tuple and transaction; preserve real writers, journal, cache invalidation and full preflight. Do not change `runtime.py`, production startup, `sync_settlement_graph`, map sources or generated artifacts. Acceptance: `SelectedSettlementSyncTests` observes only the selected planner/apply calls, unknown-ID rejection before any such call, and unchanged real room/exit state on failure; its no-argument case materializes every graph in a small synthetic roster.
- [x] 1.2 In that same file, change `_clear_grid_display_maps(*, settlement_ids: frozenset[str])` and `_sync_grid_room_art(*, settlement_ids: frozenset[str])` to honor the resolved selection; filter bridge rows by `row.gate.map_id` and wilderness gates by `gate.destination.map_id`. Preserve the nonempty-call global reverse-Limbo prune and existing warning/events for selected failures. Leave retained-wilderness refresh and interiors unchanged. Acceptance: synthetic unselected room/road/art/display/forward-bridge drift survives, no omitted-gate warning occurs, selected destination-map gates provision even when anchor IDs differ, and a reverse exit into Limbo is still pruned with its existing event.

## 2. Add required test declarations

- [x] 2.1 In existing `world/tests/geography_fixture.py`, add `sync_test_settlements(settlement_ids: Iterable[str]) -> SyncReport`, `sync_test_wilderness(settlement_ids: Iterable[str]) -> None` and `selected_startup_settlements(settlement_ids: Iterable[str]) -> Iterator[None]` as a context manager, using the exact contracts in design decision 2. Direct helpers tuple-freeze the declaration and delegate to real selected synchronizers; startup adaptation uses `ExitStack`/`patch.object` on only the two bootstrap bindings, capturing originals before replacement. Export the helpers. Keep all publication helpers and `GeographyPublicationMixin` behavior unchanged. Acceptance: adapter tests in `SelectedSettlementSyncTests` observe required arguments, one-shot iterable forwarding, identical published bundle and restored function bindings after both successful and failing scopes; production startup outside the adapter still receives no selector.

## 3. Cut over the existing non-browser fixtures

- [x] 3.1 Migrate the 46 direct grid call sites and four real startup calls in `world/maps/tests/test_bootstrap.py` using design decision 3. Resolve declarations from existing gate coordinates/references; pass IDs into `_declared_node_count(settlement_ids)` and `_declared_road_count(settlement_ids)`. Use the capital/village pair for the four startup scopes and cross-map rollback cases, retain both graphs for second-graph fault injection, and use single-map selection for single-map consumers. Keep the sparse direct-graph identity tests, database isolation, asserted consumer effects and meaningful requirement annotations. Replace obsolete count comments and misleading method names, not module paths. Do not reclassify data tests or add game-data pins. For the four whole-roster assertions listed in design decision 3a, declare the registry ids the test already reads so the complete loop survives; derive each asserted count from the declared ids through the extended count helpers instead of a module constant. Acceptance: the existing four bootstrap classes pass, fresh-grid tests still start empty, rollback checks retain two-map observations, the four whole-roster assertions still visit every registry row, and spies on selected setup show no unrelated graph plan/apply work.
- [x] 3.2 Migrate every remaining direct caller in the closed 47-file table in design decision 3, including support-file imports. Replace no-argument grid/wilderness consumer calls with the explicit test helpers and derive `required_map_ids` using the table's coordinate/reference/entry/exterior rules after synthetic scope entry. Remove the unused plain-room appearance synchronization. For fixtures synchronizing all interiors/services, declare the union of their actual exterior maps and any traversed gates. Keep fixture class-vs-method lifecycle unchanged. Do not modify production modules, browser fixtures, synthetic vocabulary or tests outside the listed caller/support surface. Handle the two whole-roster assertion modules from design decision 3a explicitly: move `test_room_art_metadata`'s authored-node loop and `test_city_movement_cost`'s exit-count assertion onto the synthetic multi-map fixture with invented keys and independently known road counts, preserving each assertion at full strength. Acceptance: the focused consumer batches in section 5 pass without a fallback to the whole registry, no unclassified direct no-argument grid calls remain in non-browser consumer tests, and no expectation, loop bound or count was lowered to match a smaller fixture.
- [x] 3.3 In `world/maps/tests/test_runtime_adoption.py` and `test_editor_final_yaml_adoption.py`, declare `tuple(candidate.settlements.graphs)` for candidate-wide baseline materialization through `sync_test_settlements`. Keep their real `runtime.synchronize()` calls full-world and identify those as explicit full-candidate contract cases; keep candidate validation and rollback assertions unchanged. Preserve the direct no-argument call in the dedicated synthetic default-contract test. Acceptance: adoption and final-YAML contract classes still observe complete-world identities/rollback and production `runtime.synchronize()` continues invoking `bootstrap.sync_grid()` with no selector.

- [x] 3.4 Close the indirect execution surface in design decision 3b. In `world/maps/tests/test_limbo_room.py`, run the `runtime.synchronize()` ordering test inside `selected_startup_settlements(required_map_ids)` and install its recording wrapper over the adapted binding so the ordering observation and the selection both hold; run the `at_server_start()` rename test under the adapter too. In `world/maps/tests/test_instance_stage_wiring.py`, run `test_server_start_registers_instance_reclamation` under the adapter with the maps it touches. Record the classification of every further real startup or runtime caller the implementation census finds before editing it. Acceptance: a spy on the real synchronizers shows these three tests no longer apply the full roster, each test still asserts its original startup ordering, rename or registration outcome, and production `at_server_start()` outside the adapter still synchronizes the complete roster.

## 4. Add discoverable mechanism evidence and developer guidance

- [x] 4.1 Add `SelectedSettlementSyncTests` to existing registered `world/maps/tests/test_bootstrap.py` using the existing `_synthetic_graph` pattern and invented fixture identities. Implement all six evidence groups in design decision 4, including actual rooms/roads and state snapshots, unknown/empty/deduplicated/generator selections, unrelated-roster growth, two-map late-write rollback, ancillary isolation, default full-roster behavior and destination-map wilderness filtering. Within those groups establish the two evidence gaps explicitly: a reversed one-shot iterable with duplicates whose ordered planner/apply membership is map-id sorted, plus bare-string and non-string rejection before planning; and both-sides ancillary symmetry where selected drift converges while unselected drift survives and an unmaterialized unselected destination emits no missing-gate warning. Include the adapter forwarding/restoration cases from task 2.1. Spies wrap real planning/application; do not replace real writer outcomes with mocks, pin shipped contents or disable static-reference validation. Acceptance: the class passes and would fail if the selector were ignored, if application were per-map transactional, if selection preserved input order, if the ancillary pass were dropped, or if production default selection were narrowed.
- [x] 4.2 Update `docs/development/evennia-testing-guide.md` with the explicit declaration API, class-level publication versus materialization distinction, the documented whole-roster exception rule, the startup-adapter boundary and the measured diagnosis from `measurements.json`. Preserve its existing settlement-sensitive test guidance. Reuse existing test modules so `.github/evennia-shards.json` needs no change; if any module is introduced or renamed, register its exact label once in that manifest in the same implementation commit. Obtain requirement IDs using `uv run --locked python -m tools.spec_traceability list` against an equivalent spec tree with this delta. Before main-spec synchronization, apply the per-test mapping rule in design decision 4 and record each pre-synchronization annotation with its rationale in this file; leave mock-only adapter wiring, unknown-selection and empty-selection tests unannotated until the new ID exists, then rebind them to the generated added-requirement ID at archive. Do not invent IDs or change either lint's freeze/ignore lists. Acceptance: `tools.contract_gate` reports no uncovered current requirements or ownership errors, the two explicit lints pass, every pre-synchronization annotation is justified per test in this file, and no test carries an annotation whose assertions do not establish it.

## 5. Run final acceptance after all edits

Use a real env file containing `MUD_TEST_SETTINGS=1` and the single-token spelling `--env-file=<file>`. Each focused command must stay below 100 discovered tests and ten minutes. For modules/classes exceeding those limits, run their explicit classes separately. Do not run a CI shard command, full browser suite, full serial non-browser suite or evidence aggregation locally.

- [x] 5.1 Run `uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb --noinput --durations 0 world.maps.tests.test_bootstrap.SelectedSettlementSyncTests`, then the four existing classes as separate focused commands using the same prefix. Run `world.maps.tests.test_runtime_adoption`, each class in `world.maps.tests.test_editor_final_yaml_adoption`, `world.maps.tests.test_limbo_room` and `world.maps.tests.test_instance_stage_wiring` separately. Acceptance: every focused command reports `OK`; selected planner/writer membership is bounded by the declared fixture set even when unrelated synthetic graphs are added; the default-path tests cover all declared graphs; the whole-roster assertions still visit every registry row; and the two startup-boundary modules assert their original ordering, rename and registration outcomes under the adapter. Record informational post-apply durations alongside the proposal measurement, with no pass/fail timing threshold.
- [x] 5.2 Run focused classes for every migrated module from design decision 3, retaining each module's existing shard owner. Batch only while staying within the discovery/time limits. Include map/wilderness roundtrips, movement cost, service/interior setup, quest observation and the class-level presentation fixtures; these exercise the declaration dependency joins. Run `uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb --noinput tests.test_evennia_test_optimization_contract`. Acceptance: all changed consumer classes and the ownership contract report `OK`; no assertion or requirement annotation has been removed merely to accommodate a smaller fixture.
- [x] 5.3 Run `openspec validate scope-test-settlement-sync --strict`, `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate`. Acceptance: all exit zero with no OpenSpec warnings, uncovered current requirements, added freeze entries or shard-ownership errors. Confirm the default full-roster test and unchanged production call signature separately from the startup adapter's selected behavior; report only the tests and diagnostics actually exercised.

## Pre-synchronization annotation ledger

The added requirement `Explicit settlement selection bounds test synchronization`
normalizes (per `tools/spec_traceability.py`) to
`grid-room-sync::explicit-settlement-selection-bounds-test-synchronization`.
That ID does not exist in the main-spec tree until archive synchronization, so
no test carries it yet. Existing annotations remain only where the test's
assertions still establish that requirement.

| Test | Annotation | Rationale |
|---|---|---|
| `world.maps.tests.test_bootstrap.SelectedSettlementSyncTests.test_default_selection_materializes_every_graph_and_runtime_stays_selector_free` | `grid-room-sync::sync-grid-is-distinct-from-sync-all-and-instantiates-real-rooms-and-exits` | Its no-argument call materializes every graph in a synthetic registry through the real planner/writer, and the unchanged production `runtime.synchronize()` invocation is asserted with no selector: the modified requirement's default full-roster scenario. |

Every other new evidence test is deliberately unannotated before the archive
sync (mock-only adapter wiring, unknown/empty selection, ordering, ancillary
isolation and rollback establish the added mechanism, not an existing
requirement).

Hand-off (test -> delta requirement scenario):

- `test_selected_work_is_bounded_and_unrelated_growth_adds_nothing` -> Unrelated roster growth does not add selected graph work.
- `test_selection_is_deduplicated_sorted_and_one_shot` -> Selection is explicit and deterministic (map-ID order, deduplication).
- `test_unknown_and_malformed_selections_reject_before_planning` -> Malformed selection rejects before planning; unknown selection rejects atomically.
- `test_explicit_empty_selection_performs_no_persistent_work` -> Explicit empty selection performs no persistent synchronization.
- `test_selected_batch_failure_rolls_back_both_settlements` -> Selected batch failure preserves the prior state.
- `test_ancillary_work_respects_the_selection_and_global_prune_stays` -> Ancillary settlement work respects the selection; global reverse-entry pruning remains in force.
- `test_wilderness_selection_uses_destination_map_identity` -> Wilderness selection uses destination map identity.
- `test_default_selection_materializes_every_graph_and_runtime_stays_selector_free` -> Modified requirement: default full-roster path and production runtime invocation.
- `test_adapter_forwards_a_frozen_declaration_and_restores_bindings` -> Startup test selection retains the production writer; bindings restored after success/failure.
- `test_adapter_requires_an_argument_and_preserves_the_published_bundle` -> Explicit declaration requirement; published bundle preserved.
- `test_cold_process_default_sync_publishes_before_reading_the_registry` -> Modified requirement: publication precedes the registry read on a cold process.

## Informational post-apply durations (no pass/fail threshold)

Measured on the feature worktree with the focused labels above; compare with
the proposal's historical 147.381 s (2 settlements) to 1,868 s (60
settlements) for the 50-method bootstrap module. These are diagnostics, not
acceptance gates.

| Command | Tests | Duration |
|---|---:|---:|
| `SelectedSettlementSyncTests` | 10 | 5.428 s |
| `GridBootstrapTests` | 24 | 108.331 s |
| `WildernessBootstrapTests` | 17 | 116.356 s |
| `SparseSettlementSyncTests` | 4 | 2.788 s |
| `MetricCutoverTests` | 5 | 18.722 s |
| `test_runtime_adoption` | 7 | 364.787 s |
| `FinalYamlAdoptionTests` | 4 | 252.846 s |
| `test_limbo_room` | 22 | 77.201 s |
| `test_instance_stage_wiring` | 6 | 13.712 s |
| map consumer batch (movement/walkthrough/roundtrip/art/service) | 44 | 89.618 s |
| remaining map consumers batch | 88/51 (two runs) | 8.296 s / 12.208 s |
| rules party batch | 89 | 29.255 s |
| rules service/persona batch | 90 | 18.055 s |
| web presentation batch | 80 | 618.345 s |
| commands + server + typeclasses discovery batch | 42 | 164.749 s |
| typeclasses appearance/movement/exits batch | 89 | 52.179 s |
| web actions batch | 45 | 46.167 s |
| remaining presentation classes batch | 67 | 65.885 s |
| quests batch (primer first) | 83 | 60.398 s |
| rules reveal/knowledge/travel batch (primer first) | 85 | 90.984 s |
| rules npc schedule batch (primer first) | 54 | 9.489 s |
| guild support batch one (primer first) | 66 | 218.498 s |
| guild support batch two (primer first) | 56 | 178.528 s |
| movement settlement batch (primer first) | 30 | 25.068 s |
