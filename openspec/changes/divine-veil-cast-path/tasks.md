## 1. Derived veil recipe

- [ ] 1.1 Add a deterministic veil-recipe helper in `world/rules/skill_effects.py` returning the
      displayed combat five (`atk_phys`, `agility`, `defense`, `magic_power`, `hp`) at the ceiling of
      the mundane bands declared by `RACE_REGISTRY["human"]`; no numeric literal enters the code.
- [ ] 1.2 Test: the recipe returns integer values for exactly the five keys, and changing the registry
      band in a synthetic fixture changes the recipe's output.

## 1a. Provenance record

- [ ] 1a.1 Add the provenance attribute beside the disguise layer, written only by
      `world/rules/skill_effects.py`; an absent record reads as mundane.
- [ ] 1a.2 Register it everywhere `disguised_stats` already is: `_snapshot_entity_state` and
      `_restore_entity_state` in `world/rules/action.py`, and the explicit tuples in
      `world/rules/cast_settlement.py` and `world/rules/clock.py`.
- [ ] 1a.3 Extend the forbidden-module scan in `world/rules/tests/test_disguise_boundary.py` to
      name-check the new attribute, so a future combat-module read is caught the way a
      `disguised_stats` read already is. The per-file writer ledger needs no new entry.

## 2. Handler

- [ ] 2.1 Rewrite `_handle_set_disguise` in `world/rules/action.py` to use the recipe: apply to a
      non-actor target; when the target is the actor, clear only if the existing veil's provenance is
      divine, otherwise apply. Write divine provenance on every apply and clear it on every lift.
- [ ] 2.2 Re-register `set_disguise` with an empty `requires_event_context`.
- [ ] 2.3 Remove the now-dead `status_disguise` context special case from `commands/action.py`.
- [ ] 2.4 Tests: self-cast veils then lifts on a second cast; a self-cast over a pre-seeded MUNDANE
      veil refreshes to the derived values instead of stripping it (the shipped preset case);
      other-cast veils the target and leaves the caster's display alone; other-cast on an
      already-veiled target refreshes rather than lifts; true trait values never change on any path.

## 3. Preview and boundary parity

- [ ] 3.1 Test: the shared action preview reports no missing-effect-context failure for the disguise
      skill with an empty `event_context`.
- [ ] 3.2 Run the existing disguise boundary tests unchanged and confirm the writer ledger still
      matches (the write stays in `world/rules/skill_effects.py`, so no ledger entry is added).
- [ ] 3.3 Test: a rolled-back resolution restores `disguised_stats` AND the provenance record
      byte-equal together, for the apply path and the lift path.
- [ ] 3.4 The veil becomes castable in combat for the first time, so verify `disguised_stats` is
      snapshotted on the combat round path as well as the cast path; it is registered in
      `world/rules/cast_settlement.py` and `world/rules/clock.py` today, and the combat session
      snapshots by surface — confirm the `traits` surface's entity-state snapshot covers it and add it
      if it does not.

## 4. Behavior contract tests

- [ ] 4.1 Put the new tests in `world/rules/tests/test_divine_veil_cast.py`, composed from synthetic
      skill definitions only — no shipped-content skill names, no data-contract tagging.
- [ ] 4.2 Annotate with `covers_requirement` using IDs from
      `uv run --locked python -m tools.spec_traceability list`.
- [ ] 4.3 Register the module in exactly one shard of `.github/evennia-shards.json`.

## 5. Verification

- [ ] 5.1 Run the focused label
      `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_divine_veil_cast`
      with `MUD_TEST_SETTINGS=1` passed through the tool's `env` input.
- [ ] 5.2 Run the focused labels `world.rules.tests.test_disguise_boundary` and the command-side cast
      module covering `commands/action.py` to prove the ledger and the cast command still pass.
- [ ] 5.3 Run `uv run --locked python -m tools.spec_traceability check` and
      `uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`.
- [ ] 5.4 `openspec validate divine-veil-cast-path --strict`.
