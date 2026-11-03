# Design

## Context

See `proposal.md` for the approved trigger and historical baseline. The code at `61835b0db4c3d00f3bd4ef8411246695dd5e0dba` has three separate boundaries.

`world/tests/geography_fixture.py::publish_shipped_map_world()` calls `runtime.adopt()` only when no world is published. `publish_shipped_settlements()` also adopts that complete world. `GeographyPublicationMixin.setUpClass()` invokes the guarded publication helper before its cooperative parent. Neither helper creates persistent rooms. `test_bootstrap.py` publishes at module import and does not inherit that mixin.

`world/maps/bootstrap.py::sync_grid()` calls `runtime.ensure_published()` and full static-reference validation, snapshots every `SETTLEMENT_GRAPHS` value, plans every graph before any write and applies all plans in one transaction. Room art, forward city gates and legacy display cleanup also range over the complete authored world. `_apply_graph_plan()` performs the room/road convergence and knowledge remap; `_invalidate_plan_caches()` handles failure.

`world/maps/runtime.py::synchronize()` calls `sync_limbo()`, `sync_grid()` and `sync_interiors()` in one outer transaction and restores adoption/cache state on failure. Production startup calls this composition root. That root and its production ordering must remain unchanged.

## Measured Diagnosis

### Historical baseline

The completed synthesis batch measured the same 50-method bootstrap module at 147.381 s before the maps, 775 s after Grandia, 1,306 s after Altoria and 1,868 s after Valhalla. The roster grew from 2 to 60. Those are ground-truth records, not measurements repeated during this proposal. A full 1,868 s rerun would violate the repository's local ten-minute command limit.

### Focused current-checkout measurement

A temporary diagnostic module wrapped the real functions with `perf_counter()` and `try/finally`, retaining their arguments, return values and exceptions. It installed wrappers before importing `test_bootstrap`, recorded `unittest.TestResult.startTest/stopTest` phase boundaries, and loaded four existing methods through `load_tests`. It did not replace a planner, writer or fixture. The temporary module and its bytecode were removed after recording evidence. No production source changed.

The guarded command used the normal Evennia runner, retained test database, no coverage and one process:

```text
uv run --locked --env-file=/tmp/settlement-sync-probe.env evennia test --settings test_settings.py --keepdb --noinput --timing --durations 0 openspec.changes.scope-test-settlement-sync.timing_probe
```

The env file contained `MUD_TEST_SETTINGS=1`; its extra `PYTHONPATH` did not make an external module importable, so the successful probe lived temporarily under this change directory. An initial `--testrunner` attempt was refused by the guard and an external-module discovery attempt failed before running real tests. Neither attempt supplies timing evidence.

All four selected methods passed. Django reported 141.854 s for test execution, 0.687 s database setup and 150.405 s total run. Wrapper totals are inclusive, so nested rows must not be added to `sync_grid` again.

| Existing method | Method duration | Grid calls | Grid inclusive | Graph plans | Plan total | Graph applies | Apply total | Art total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `GridBootstrapTests.test_single_call_on_fresh_grid_spawns_all_thirty_one_rooms` | 43.089 s | 1 | 42.774410 s | 60 | 0.037831 s | 60 | 41.399056 s | 1.335077 s |
| `GridBootstrapTests.test_sync_grid_is_idempotent_and_preserves_dbid` | 54.318 s | 2 | 53.972501 s | 120 | 1.589222 s | 120 | 50.561757 s | 1.805809 s |
| `WildernessBootstrapTests.test_sync_wilderness_is_idempotent` | 44.094 s | 1 | 42.857954 s | 60 | 0.039225 s | 60 | 41.474651 s | 1.334097 s |
| `GridBootstrapTests.test_at_server_start_calls_sync_grid_after_sync_all` | 0.341 s | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

The first full grid pass inside the idempotence method took 42.823995 s and the second took 11.148505 s. The wilderness method's two `sync_wilderness()` calls together took 0.784281 s. Cold adoption during module discovery happened once and took 6.279501 s; its nested static-reference validation took 0.001382 s. Four grid calls plus the wilderness calls found an already published bundle, with six measured `ensure_published()` invocations totaling under 0.000006 s. No captured grid convergence or adoption occurred at a class boundary. Method durations include `setUp` through cleanups; class boundaries are outside them. `measurements.json` retains the recorded function aggregates.

The dominant measured work is repeated graph application inside each method. It is not a once-per-class full publication. Every sampled fresh pass applied 60 graphs. Even the unchanged second call still planned and applied all 60. The samples establish the suspected driver without claiming an exact decomposition of the historical 1,868 s into function totals.

An AST census of the existing module found:

| Class | Test methods | Direct `sync_grid` call sites | Real startup call sites |
|---|---:|---:|---:|
| `GridBootstrapTests` | 24 | 28 | 2 |
| `WildernessBootstrapTests` | 17 | 12 | 1 |
| `SparseSettlementSyncTests` | 4 | 1 | 0 |
| `MetricCutoverTests` | 5 | 5 | 1 |

There are 46 direct grid call sites and four startup call sites. Some rejection tests intentionally fail before graph application. This is a static call-site count, not a claim that 50 complete successful passes executed.

### Expected effect supported by the measurement

The measured fresh pass spent 38.808390 s applying the 58 graphs outside the capital/village pair, versus 2.590666 s applying that pair. The two-pass method spent 47.357538 s on those excluded graphs versus 3.204219 s on the pair. The wilderness sample spent 38.867554 s on excluded graph application versus 2.607098 s on the pair. Excluding those graphs removes those measured work units; filtered art and gate passes remove additional unrelated ORM work. The contract checks graph membership and persistent effects, not those durations.

These are measured costs of work that selection will omit, not post-implementation timing results or an exact prediction of a new module duration. The expected change is from per-call room/road convergence proportional to all published graphs to convergence proportional to declared graphs. Complete bundle publication, full reference validation and cheap registry filtering remain roster-dependent. Candidate-wide adoption tests intentionally still cover their declared full candidate. This proposal does not promise that every CPU instruction in the suite becomes independent of roster size.

## Goals / Non-Goals

**Goals.** Keep the complete immutable published world available to readers. Let a non-browser test declare the maps whose persistent rooms/gates it needs. Apply selection through the existing planner, shared writer and rollback journal. Make adding unrelated graphs leave the selected plan/apply membership unchanged. Preserve production's default full-world synchronization.

**Non-goals.** No partial runtime publication, synthetic production implementation, implicit class-global selection, fixture database caching, interior-selection API, authored content changes, browser-seed conversion, startup ordering change, performance CI threshold or compatibility/migration path. Do not remove existing data-contract tests or broaden the freeze lists to make this work pass. Human prose/visual quality is unchanged, so no new human-review document is required.

## Decisions

### 1. Explicit keyword selection on the existing synchronizers

Use these contracts verbatim in `world/maps/bootstrap.py`:

```python
def sync_grid(*, settlement_ids: Iterable[str] | None = None) -> SyncReport: ...
def sync_wilderness(*, settlement_ids: Iterable[str] | None = None) -> None: ...
def _selected_settlement_graphs(
    settlement_ids: Iterable[str] | None,
) -> tuple[SparseSettlementGraph, ...]: ...
def _clear_grid_display_maps(*, settlement_ids: frozenset[str]) -> None: ...
def _sync_grid_room_art(*, settlement_ids: frozenset[str]) -> None: ...
```

Import `Iterable` from `collections.abc`. `None` means every graph in the current registry's existing iteration order. An explicit iterable is consumed once, deduplicated and sorted by map ID; bare strings and non-string members raise `TypeError`. Resolve every requested ID against `SETTLEMENT_GRAPHS` before invoking any planner or persistent write. An unknown ID raises `KeyError` naming that ID. An explicitly empty iterable returns an empty `SyncReport` or `None` without persistent work, including pruning or reclamation registration. Omitted selection preserves the existing empty-roster behavior.

Keep `runtime.ensure_published()` and `validate_static_references()` at the normal composition boundary. Selection never edits, filters or republishes the bundle. The full-world preflight stays in force; invalid unrelated static references can still reject the world. Selection is a database-materialization boundary, not an adoption-validation exemption.

For nonempty selection, feed the resulting `graphs` directly into the existing `plans = tuple(_plan_settlement_graph(graph) for graph in graphs)`. Do not call `sync_settlement_graph()` in a loop, because that would produce separate transactions and lose all-plans-before-write semantics. Keep the existing transaction, knowledge journal, cache invalidation and event logic. `settlement_graphs_synchronized.context['maps']` reflects the graphs actually selected.

Use the selected ID set in display-registration cleanup, art iteration and forward bridge rows. Filter a city-gate row by `row.gate.map_id`, never its registry key. For wilderness, filter each gate by `gate.destination.map_id`, never `entry.anchor_key`; a settlement ID and location/anchor ID can differ. The wilderness script creation and retained-room refresh retain their existing behavior; the selected gate loop omits unselected gates without missing-room warnings. A selected missing gate retains its current warn/skip behavior.

Retain `_prune_exits_into(limbo)` as the global one-way invariant on every nonempty grid synchronization, including selected calls. An unrelated reverse exit into Limbo is invalid state and still converges away. Ordinary rooms, authored roads, art, display registrations and forward bridges of unselected maps remain untouched. This explicit exception avoids changing `limbo-one-way-gates` or introducing a second pruning policy. No-argument production behavior stays identical.

`runtime.synchronize()` and `server/conf/at_server_startstop.py::at_server_start()` receive no selector, flag, environment override or new signature. They continue to call full synchronization. The selector exists for explicit callers; no production entry point is changed to supply it.

### 2. Test declarations and real startup adapter

Extend the existing test-only `world/tests/geography_fixture.py`, preserving publication helpers and `GeographyPublicationMixin` unchanged:

```python
def sync_test_settlements(settlement_ids: Iterable[str]) -> SyncReport: ...
def sync_test_wilderness(settlement_ids: Iterable[str]) -> None: ...
@contextmanager
def selected_startup_settlements(settlement_ids: Iterable[str]) -> Iterator[None]: ...
```

Both direct helpers require their argument, tuple-materialize it once, publish through `publish_shipped_map_world()` if needed and call the real bootstrap function with `settlement_ids=ids`. They do not create fixtures or modify registry membership. Add them to `__all__`.

The context manager captures the real `bootstrap.sync_grid` and `bootstrap.sync_wilderness` bindings before patching, freezes and validates the explicit IDs, then uses `ExitStack` plus `patch.object` to adapt those two bootstrap bindings to pass that selection to the captured real functions. A no-argument invocation inside startup therefore executes the real selected planner/writer. Do not patch `runtime.synchronize`, `at_server_start`, publication, validation or any lower-level writer. Restore both bindings even if startup raises or context entry fails. Existing imported function aliases are outside this adapter; direct calls use the explicit helpers. Use the adapter only around tests whose subject is startup orchestration, never to claim evidence for the omitted-selector full-world contract.

Do not turn `GeographyPublicationMixin` into a materialization mixin. Publication remains class-level where it already is; synchronization retains each fixture's present lifecycle. Existing class-level database fixtures continue using `setUpClass`/`setUpTestData`, and per-method mutation tests keep isolated per-method database state.

### 3. Caller cutover is explicit and bounded

A source census found 119 direct `sync_grid` call sites in 47 non-browser test/support files. The table below is the closed migration surface at proposal time. Re-export-only imports in nearby `_support.py` files must follow the same helper names when the caller changes, without creating a second alias named `sync_grid`.

| Group | Files relative to repository root |
|---|---|
| Commands/server/typeclasses | `commands/tests/test_localized/test_xyz_grid_and_help.py`; `server/conf/tests/test_scene_flavor_service.py`; `typeclasses/tests/test_appearance.py`; `typeclasses/tests/test_exit_movement_cost.py`; `typeclasses/tests/test_exits.py` |
| Maps | `world/maps/tests/test_bootstrap.py`; `test_limbo_room.py`; `test_room_art_metadata.py`; `test_service_interiors.py`; `test_static_map_references.py`; `test_city_movement_cost.py`; `test_city_walkthrough.py`; `test_wilderness_destination.py`; `test_city_wilderness_roundtrip.py`; `test_movement_roundtrip.py`; `test_wilderness_population.py` (all unqualified names in this row are under `world/maps/tests/`) |
| Candidate-wide adoption | `world/maps/tests/test_runtime_adoption.py`; `world/maps/tests/test_editor_final_yaml_adoption.py` |
| Rules | `world/rules/tests/test_dialogue.py`; `test_npc_persona_fresh_bootstrap.py`; `test_npc_roster_validation.py`; `test_npc_schedule_runtime.py`; `test_phase4_integration.py`; `test_map_knowledge_integration.py`; `test_ground_reveal.py`; `test_party_follow.py`; `test_party_follow_possession.py`; `test_party_time_settlement.py`; `test_movement_settlement.py`; `test_travel_plan.py`; `test_guild_economy_sync/_support.py` (unqualified paths in this row are under `world/rules/tests/`) |
| Quests | `world/quests/tests/test_deadlines.py`; `world/quests/tests/test_escort_lifecycle.py`; `world/quests/tests/test_room_observation.py` |
| Actions | `web/webclient/actions/tests/test_node_ids.py`; `test_travel_actions.py`; `test_exploration_actions/test_move_and_look.py` (unqualified paths in this row are under `web/webclient/actions/tests/`) |
| Presentation | `web/webclient/presentation/tests/test_area_map.py`; `test_local_map/test_grid_gateways.py`; `test_local_map/test_presenter.py`; `test_local_map/test_per_gate_footprint.py`; `test_local_map/test_gate_capacity.py`; `test_local_map/test_wilderness.py`; `test_exploration_panel/test_presenter.py`; `test_exploration_panel/test_navigation_and_byte_stability.py`; `test_exploration_panel/test_wilderness_and_npc_titles.py`; `test_affordances/test_vocabulary.py` (unqualified paths in this row are under `web/webclient/presentation/tests/`) |

For each fixture, form `required_map_ids` from the targets that fixture already resolves. Apply the following deterministic derivation rules, with no new shipped IDs or roster copy:

| Existing fixture input | Declaration expression |
|---|---|
| One resolved grid coordinate | `(xyz[2],)` using its existing local coordinate variable |
| Several grid coordinates | `tuple(sorted({xyz[2] for xyz in fixture_coordinates}))` |
| A qualified node reference | `(reference.map_id,)` |
| A selected wilderness entry | `tuple(sorted({gate.destination.map_id for gate in entry.gates}))` |
| A selected graph or synthetic graph | `(graph.map_id,)` |
| A selected place/interior exterior | `(exterior.settlement,)`, resolved through the existing `interiors.exterior_for(place.room.object_id)` join |
| A fixture synchronizing every interior or service | Union of `exterior.settlement` for its actual published interior exteriors plus any separately traversed gate maps; do not include unrelated settlement graphs |
| A consumer with no grid target, such as `test_appearance`'s plain-room appearance case | Remove the unused grid synchronization; declare nothing and create no grid rooms |
| A candidate-wide runtime adoption test | `tuple(candidate.settlements.graphs)` declared adjacent to the synchronization; candidate-wide behavior is this test's subject |

Evaluate declarations after any synthetic registry/publication scope has been entered. The kit in `world/tests/synthetic_data/vocab.py` borrows runtime map identities; do not change its vocabulary or replace it with hard-coded capital/village IDs. For tests needing no persistent grid rooms, remove their unused sync call rather than selecting arbitrary data.

In `test_bootstrap`, use the capital gate coordinates/reference already resolved by the fixture for capital-only cases, the existing point-entry reference for village-only cases and their union for cross-settlement cases. Any test counting all synchronized nodes/roads must pass its declared IDs to `_declared_node_count(settlement_ids)` and `_declared_road_count(settlement_ids)`, so expected topology is limited to the declared scope. Existing production-data relationships stay in their data-contract role; new mechanism tests use invented graphs and independent expected effects. Remove obsolete numeric roster comments and rename misleading test methods such as `...all_thirty_one_rooms`; no module rename is needed.

For the four actual startup invocations in this module, declare the gate-map pair and enter `selected_startup_settlements(required_map_ids)` around the real `at_server_start()` call. The startup still executes real limbo/grid/interior/wilderness and service steps; it no longer materializes 58 unrelated settlements. Whole-registry checks that do not need persistent rooms retain their current read-only registry view. `SparseSettlementSyncTests` keeps its existing direct single-graph identity tests and changes the one shipped-capital `sync_grid()` call to a one-map declaration. Metric rollback tests declare both touched maps where they inject a failure into the second graph; declarations retain both graphs so rollback evidence is not reduced to a single-map test.

Candidate-wide `runtime.synchronize()` calls in the two adoption modules remain full-world calls and are documented as full-candidate declarations. Their baseline `bootstrap.sync_grid()` calls use `sync_test_settlements(tuple(candidate.settlements.graphs))`. Do not replace full-candidate adoption validation with subset validation. They intentionally test the full adopted candidate; this exception is visible and cannot spread to unrelated consumers.

For any companion `sync_wilderness()` in the migrated fixture, pass the same declared map IDs through `sync_test_wilderness`, preserving the real wilderness implementation. No browser file is changed. No new module is required; if a worker introduces or renames one, register its exact module label in `.github/evennia-shards.json` in the same commit.

### 4. Discoverable evidence, without timing gates

Add `SelectedSettlementSyncTests` to existing registered `world/maps/tests/test_bootstrap.py`. Reuse its `_synthetic_graph` construction pattern with invented map IDs, node identities and explicit roads. Publish complete readable fixture views through existing publication helpers and restore them with `addCleanup`; keep static-reference validation real. Where a synthetic graph is inserted into the bootstrap graph mapping for a default-roster test, preserve the original world's valid static-reference bindings and never assert that a partial snapshot is an adopted world.

The tests establish the following observable outcomes:

1. Selected A materializes, B does not, and spies wrapping the real planner/writer see only A. Add unrelated synthetic C/D and repeat; planner/writer membership remains A. Check persistent A rooms/roads, stable dbids and empty second report, not just mocks.
2. Request A plus an unknown ID; planner/writer calls remain empty and room/exit/tag state is unchanged. Repeated IDs apply A once. Explicit empty selection creates no rooms, art writes, forward bridges, script or reverse prune. A one-shot iterable has the same effect as its tuple.
3. After two selected maps are seeded, change A and inject failure in B's real apply path. Both database and cached coordinates, occupant/home/inbound reference and knowledge state retain the baseline. Reuse the existing sparse rollback assertions and knowledge-journal patterns.
4. Seed unselected B room/road/art/display/forward-bridge drift, then select A. B's ordinary managed state remains unchanged and no unselected-gate missing warning is emitted. Separately seed a reverse B-to-Limbo exit and verify global pruning still removes it, preserving the existing invariant.
5. Call no-argument `sync_grid()` against a small synthetic graph registry and verify every graph materializes through the same real planner/writer. Verify the unchanged production `runtime.synchronize()` invokes `sync_grid()` without a selector, and use existing startup boundary tests for orchestration. Do not run the startup adapter in this evidence case.
6. Select a synthetic wilderness gate whose anchor/registry key differs from `destination.map_id`; the selected destination is provisioned, the unselected one is untouched, and production no-argument provisioning still visits every declared gate.

Place fixture-adapter tests in `SelectedSettlementSyncTests` in the existing bootstrap module. Assert required-argument behavior, preservation of the published bundle, forwarding of a frozen declaration and binding restoration after injected startup failure. The production synchronizer tests above execute real writers; adapter wiring tests may spy/mock their boundary calls.

Obtain new canonical IDs from `tools.spec_traceability list` on an equivalent main-spec tree containing the delta. Before archive, temporarily map the new behavior tests to the existing `grid-room-sync` real-room requirement according to the traceability guide, then rebind to the tool-derived new ID when main specs are synchronized. Do not guess an ID or use a waiver. Existing requirement annotations remain on tests whose assertions still establish their claims.

## Rejected Alternatives

| Alternative | Reason rejected |
|---|---|
| Cache publication or move it to `setUpClass` again | The module already adopts once; the measured cost repeats inside methods and is dominated by graph application. |
| Class-cache all spawned settlement rooms | Mutation, fresh-grid and rollback tests need isolated database state; this also retains roster-sized construction. |
| Publish a partial map world | It breaks complete bundle and cross-domain reference contracts, including permanent interiors and external service/quest joins. |
| Loop over `sync_settlement_graph` in a test helper | It omits grid art/bridges and loses one transaction plus all-plans-before-write across selected maps. |
| Patch `SETTLEMENT_GRAPHS` down to two shipped maps for the whole suite | Other readers still see complete-world references and consumer bindings; a hidden global override conceals dependencies and can leak between classes. |
| Add selector parameters/environment configuration to production startup/runtime | Test setup should declare its inputs without introducing a production partial-startup mode. |
| More workers, timing assertions or a special test writer | They do not remove unrelated convergence; timing assertions are contrary to the approved batch decision, and a second writer loses production-path evidence. |

The narrow startup adapter is chosen over a registry patch because it modifies two call boundaries for one explicit test scope and still executes the original implementation. Its restoration tests are required.

## Dependency / Conflict Matrix

Only this change was active after creation; `openspec list --json` initially returned an empty active set. Main specifications describe current contracts and are not pending changes.

| Change or current capability | Dependency | Shared files / conflict | Disposition |
|---|---|---|---|
| Archived `unpin-settlement-map-data` | Required, satisfied | Bootstrap and movement tests | Build on the unpinned assertions; do not restore shipped count/coordinate pins. |
| Archived `settlement-terrain-fit` | None beyond current master | None | No synthesis tooling edits. |
| Archived `settlement-graph-generator` | None beyond current master | None | No graph generation changes. |
| Archived `settlement-rework-and-prose` | Required, satisfied | Development-guide subject only | Preserve its settlement-sensitive verification policy; no prose/tool changes. |
| Archived `altoria-capital-river-rework` | Transitive, satisfied | No authored files touched | Resolve current coordinates through existing references. |
| Archived `grandia-settlement-maps` | Required, satisfied | No source-file conflict | Published maps remain complete. |
| Archived `altoria-settlement-maps` | Required, satisfied | No source-file conflict | Same. |
| Archived `valhalla-settlement-maps` | Required, satisfied | No source-file conflict | Last timing record triggered this follow-up. |
| Other active changes | None present | None | No active scheduling edge. Recheck the active list before apply. |
| Current `grid-room-sync` | Delta owner | `bootstrap.py`, bootstrap tests | One added mechanism; existing default contract unchanged. |
| Current `map-runtime-adoption`, `map-settlement-sources`, `authored-registry-references` | Contract constraints | Adoption tests and shared validation path | Complete publication/validation and all-world startup unchanged; no deltas. |
| Current `limbo-one-way-gates`, `room-art-metadata`, `wilderness-gateway` | Contract constraints | Shared bootstrap helpers and consumer tests | Keep global reverse pruning; filter selected art/forward/gate work only. No production semantic change or delta. |
| Remaining current main spec set | No new ordering dependency | Some annotated consumer tests use the same fixture files | Preserve their assertions and requirement mappings; no changes to their capability contracts. |

## Risks / Trade-offs

A small explicit selection may expose a fixture's undeclared service frontage or companion gate. Resolve the existing referenced targets before synchronizing and union their map IDs using the rules above; do not fall back to every graph. Full reference validation still examines the published world. This is intentional and its small measured preflight cost is recorded separately from persistent convergence.

Global reverse-Limbo pruning is an explicit allowed effect outside selected maps. Restricting it would change an existing capability and is outside this workday slice. Wilderness retained-room refresh and permanent interiors also keep their existing semantics.

The largest mechanical surface is the 47-file direct caller cutover. Keep module paths/shard ownership unchanged, reuse current fixture lifecycles and execute focused batches only after all related edits land. `tools.contract_gate` and the two lints must pass without growing freeze/ignore lists. A post-apply diagnostic may record improved timing, but correctness acceptance uses bounded selected work and production default behavior, never a wall-clock threshold.
