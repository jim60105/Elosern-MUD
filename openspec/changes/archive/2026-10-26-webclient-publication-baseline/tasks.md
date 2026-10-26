# Tasks

All checkboxes are implementation work, not authorization to apply during proposal creation. Read this change design and completed dependency artifacts first. Each numbered implementation unit is 45-120 minutes; the whole slice is capped at one engineer-day. Write behavior tests before their owned implementation, then run focused verification once after all owned edits land. Do not run build/lint/tests/formatters against half-finished shared edits.

## 1. Isolated content comparison

- [x] 1.1 Add synthetic test_incremental_publication comparator/baseline cases before implementing publication.py JSON-category equality/copy and PublicationReceipt. Independently assert dictionary reorder suppressed, ordered list/bool-number change detected, 1/1.0 equal, nested presenter alias mutation isolated and unchanged references reused. Document owned-value semantics. (Done: `JsonValueSemanticsTests` plus the alias case assert every rule; `publication.py` documents owned-value semantics; the committed value is retained, and the diagnostic `committed_panels` read is a copy that cannot move it.)
- [x] 1.2 Implement coordinator.publish candidate expansion, eager unknown-scope comparison, explicit removals, metadata-only delta, unchanged receipt and fresh force_snapshot baseline. Tests count eager and unopened-map presenter calls, distinguish unavailable/removal and prove isolated sessions. Preserve action-local round context and staged dialogue consistency. (Done: `UnknownScopeTests` counts renders and never renders an unopened map; `test_unavailable_replacement_is_not_a_removal`; `test_unknown_scope_never_re_renders_an_explicit_removal`; the dispatcher still captures the frozen round record into the context factory; the dialogue companion is a compared candidate.)

## 2. One publication owner cutover

- [x] 2.1 Migrate every caller in the design inventory, remove duplicate _publish_presentation paths and use the ALWAYS-Deferred enqueue/semantic entry contract. Direct art_push and ingress sync must consume actual receipt callbacks; preflight/send failure errbacks, retirement None and queue overflow are explicit tests. Graphical success/domain rejection and text settlement compare; explicit sync/stale/error recovery force snapshot. Preserve no_presentation/sequence-retiring exceptions, request cache and original text callback/Failure. Extend existing coordinator_push/art_push/dispatcher tests and update publisher documentation. (Done: both `_publish_presentation` implementations are gone; art/ingress/dispatcher consume receipts and errbacks; `test_presenter_alias…`, `test_retired_intent_resolves_none`, `test_queue_overflow…` and the dispatcher overflow case are explicit; result-only intents are exempt from the bound so an admitted completion is still answered; `docs/development/webclient-synchronization.md` documents the contract.)
- [x] 2.2 Implement full plan/result prevalidation and serialized send boundary, monotonic issued revision distinct from successful baseline, failed-send invalidation, bounded reentrant intent ordering and specialized map revision reconciliation. Inject first/middle/final send faults, invalid later map frame and reentrant sync; assert zero preflight sends, no reused escaped target, snapshot after failure and result order. Register new Python module once in evennia-shards and traceability. (Done: `_publish_now` plans and validates every frame plus the result envelope before the first send; `_rev` bookkeeping and `_repair_required` covered by the preflight/middle-frame/overflow tests; reentrant ordering and map reconciliation by the reentrancy and map tests; the module is registered once in `webclient-presentation-a` and carries no delta-requirement annotations.)

## 3. Focused integrated verification

- [x] 3.1 Run B-PY below after edits, preserving existing text-input/async-push regression labels and contract_gate. Use the existing canonical state in both real registry and synthetic isolated fixtures; no performance counters/measurements or no-stutter claim. (Done: B-PY modules plus the wider presentation/dialogue/map/party/roster/skill/service/gallery/options/inventory/persona/context/watcher/dialogue-refresh suites and `tools.contract_gate` are green.)

## Verification commands

Run from the repository root. `.env.test` is an untracked local file containing `MUD_TEST_SETTINGS=1`, created at apply time only. Labels naming new tests above are proposed modules, all other paths are existing regressions. Use synthetic behavior fixtures, not shipped lore echoes. Register each new nonbrowser module or browser method in exactly one owning shard and retain meaningful requirement traceability. No command may expand to the CI-only full browser/evidence suite. If a batch exceeds local limits, run its named focused modules separately; do not replace functional coverage with a weaker test.

### B-PY

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_incremental_publication web.webclient.presentation.tests.test_coordinator_push web.webclient.presentation.tests.test_art_push web.webclient.actions.tests.test_dispatcher
```

### Repository contract gate

```text
uv run --locked python -m tools.contract_gate
```

These are planned implementation checks, with no runtime pass claim from proposal creation. Byte ceilings are functional protocol assertions. Performance measurement, benchmarking, profiling, latency comparisons and no-stutter evidence are explicitly excluded. No production compatibility shims or migrations.
