## 1. Contract and implementation

- [ ] 1.1 Confirm prerequisite changes and the shared interfaces in ../light-spell-catalog/design.md; inspect current source and exported references before editing, and verify no predecessor contract remains unimplemented. Do not substitute a stub or move required behavior to the catalog slice.
- [ ] 1.2 Implement mutually exclusive fixed/recovery rate validation and persistent caster snapshots in the existing buff owner/application path; verify malformed policies reject and fixed-rate behavior is unchanged.
- [ ] 1.3 Implement live recipient-state tick amount plus exact timing/refresh/removal/refetch accounting; verify 10/20/30 ticks, equal split advances, no revive, caster deletion and no replay.
- [ ] 1.4 Verify timed defense via a synthetic marker and existing combat rules; verify expiration and refresh alter real damage without activating inert bounds globally.
- [ ] 1.5 Remove the per-key test correspondence checker and its requirement, retaining useful behavior tests; verify behavior-based test collection and no new light data-freeze exemptions.

## 2. Behavioral evidence and integration

- [ ] 2.1 Implement or adapt the synthetic behavior tests for every scenario in this change's delta specs, using the smallest suitable fixture. Keep only assertions on outcomes, boundaries, transitions, persistence, immunity or rollback; verify a second synthetic configuration uses the same generic mechanism. No light-data contract, exact catalog tuple, source-string assertion or new data-freeze exception.
- [ ] 2.2 Register any newly introduced non-browser test modules in exactly one .github/evennia-shards.json shard and verify tests.test_evennia_test_optimization_contract with MUD_TEST_SETTINGS=1 in the tool environment. Keep manifest mutations serialized with the integration owner.
- [ ] 2.3 Exercise the changed actual engine path with a disposable offline scenario and capture observable results; delete it only after successful proof. Use a real command/OOB path when cast availability changes, not just a test-file invocation.
- [ ] 2.4 Run the focused test labels below after implementation editing has stopped. Where logging/state paths change, run tools.observability_lint check in the same final batch and verify normal action/clock boundaries use facade events with available identifiers in context; remove adopted files from the shrink-only freeze list, never add one.
- [ ] 2.5 Run tools.test_data_lint check, tools.spec_traceability check and openspec validate light-sustained-recovery --strict. For main-spec synchronization in the separately authorized workflow, obtain IDs using tools.spec_traceability list and annotate only tests that establish those requirements; verify no unknown IDs or uncovered main requirements are hidden. Keep all tasks unchecked until their described proof exists.

### Focused invocation

```sh
uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_recovery_profiles world.rules.tests.test_buffs world.rules.tests.test_status_display
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.test_data_lint check
uv run --locked python -m tools.spec_traceability check
openspec validate light-sustained-recovery --strict
```

Pass `MUD_TEST_SETTINGS=1` through the tool environment, never a shell prefix.
New test labels above are intended behavior modules owned by this change, not
existing-test claims. The shared integration design governs registration and
scope. No full local browser/evidence/aggregate-coverage run or command above ten
minutes. No apply, archive, main-spec sync or branch merge in the proposal turn.
