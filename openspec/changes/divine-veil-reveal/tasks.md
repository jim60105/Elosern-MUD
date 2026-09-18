## 1. Provenance precondition

- [ ] 1.1 Confirm `divine-veil-cast-path` has landed the provenance record and its snapshot
      registration; this change reads it and adds no storage of its own.

## 2. Typed effect

- [ ] 2.1 Add the reveal dataclass in `world/skills/effects.py` carrying its strength, with the two
      closed grammar forms in `parse_effect`; every other payload raises `ValueError`.
- [ ] 2.2 Test: both forms parse to the right strength and `reveal_disguise:everything` raises.

## 3. Reveal primitive and handler

- [ ] 3.1 Add the provenance-scoped reveal write to `world/rules/skill_effects.py`.
- [ ] 3.2 Add `_handle_reveal_disguise` in `world/rules/action.py` and register the prefix with
      `frozenset({"traits"})` and an empty required event context.
- [ ] 3.3 Test: a reveal that clears a veil clears its provenance record in the same operation, and a
      rolled-back reveal restores both byte-equal.
- [ ] 3.4 Tests: mundane strength lifts a mundane veil; mundane strength leaves a divine veil and all
      state untouched and does not reject; true-name strength lifts a divine veil; either strength
      against an unveiled target is a clean no-op.
- [ ] 3.5 Test: a reveal reads and writes nothing but the layer and its provenance — no true trait,
      identity, or persona access.

## 4. Boundary parity

- [ ] 4.1 Run the existing disguise boundary tests and confirm the writer ledger still matches without
      a new entry (both writes stay in `world/rules/skill_effects.py`).
- [ ] 4.2 Confirm the mundane appraisal lineage is untouched: `true_sight_appraisal` still cannot lift
      a divine veil.

## 5. Behavior contract tests

- [ ] 5.1 Put the new tests in `world/rules/tests/test_divine_veil_reveal.py`, composed from synthetic
      skill definitions only — no shipped-content skill names, no data-contract tagging.
- [ ] 5.2 Annotate with `covers_requirement` using IDs from
      `uv run --locked python -m tools.spec_traceability list`.
- [ ] 5.3 Register the module in exactly one shard of `.github/evennia-shards.json`.

## 6. Verification

- [ ] 6.1 Run the focused label
      `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_divine_veil_reveal`
      with `MUD_TEST_SETTINGS=1` passed through the tool's `env` input.
- [ ] 6.2 Run the focused labels `world.rules.tests.test_disguise_boundary`,
      `world.skills.tests.test_effects` and the veil-cast module from `divine-veil-cast-path`.
- [ ] 6.3 Run `uv run --locked python -m tools.spec_traceability check` and
      `uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`.
- [ ] 6.4 `openspec validate divine-veil-reveal --strict`.
