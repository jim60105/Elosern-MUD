## 1. Contract and implementation

- [ ] 1.1 Confirm prerequisite changes and the shared interfaces in ../light-spell-catalog/design.md; inspect current source and exported references before editing, and verify no predecessor contract remains unimplemented. Do not substitute a stub or move required behavior to the catalog slice.
- [ ] 1.2 Implement immutable per-occurrence policy validation and named SkillDef/_spell authoring parameters after LSP references; verify synthetic malformed, repeated-prefix and identity-policy behavior.
- [ ] 1.3 Implement trusted resolver binding and pre-defense/pre-rounding potency in damage/heal/self-heal; verify differing coefficients, equipment composition, miss, HP-cap and no-revival scenarios.
- [ ] 1.4 Preserve sequential nonlethal projection, freeform cost/eligibility and transaction snapshots; verify forged context is ignored and late failure restores every affected entity.

## 2. Behavioral evidence and integration

- [ ] 2.1 Implement or adapt the synthetic behavior tests for every scenario in this change's delta specs, using the smallest suitable fixture. Keep only assertions on outcomes, boundaries, transitions, persistence, immunity or rollback; verify a second synthetic configuration uses the same generic mechanism. No light-data contract, exact catalog tuple, source-string assertion or new data-freeze exception.
- [ ] 2.2 Register any newly introduced non-browser test modules in exactly one .github/evennia-shards.json shard and verify tests.test_evennia_test_optimization_contract with MUD_TEST_SETTINGS=1 in the tool environment. Keep manifest mutations serialized with the integration owner.
- [ ] 2.3 Exercise the changed actual engine path with a disposable offline scenario and capture observable results; delete it only after successful proof. Use a real command/OOB path when cast availability changes, not just a test-file invocation.
- [ ] 2.4 Run the focused test labels below after implementation editing has stopped. Where logging/state paths change, run tools.observability_lint check in the same final batch and verify normal action/clock boundaries use facade events with available identifiers in context; remove adopted files from the shrink-only freeze list, never add one.
- [ ] 2.5 Run tools.test_data_lint check, tools.spec_traceability check and openspec validate light-effect-potency --strict. For main-spec synchronization in the separately authorized workflow, obtain IDs using tools.spec_traceability list and annotate only tests that establish those requirements; verify no unknown IDs or uncovered main requirements are hidden. Keep all tasks unchecked until their described proof exists.

### Focused invocation

```sh
uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_effect_potency world.rules.tests.test_damage_effect_handler world.rules.tests.test_heal_effect_handler
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.test_data_lint check
uv run --locked python -m tools.spec_traceability check
openspec validate light-effect-potency --strict
```

Pass `MUD_TEST_SETTINGS=1` through the tool environment, never a shell prefix.
New test labels above are intended behavior modules owned by this change, not
existing-test claims. The shared integration design governs registration and
scope. No full local browser/evidence/aggregate-coverage run or command above ten
minutes. No apply, archive, main-spec sync or branch merge in the proposal turn.
