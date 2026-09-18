## 1. Provenance precondition

- [x] 1.1 Confirm `divine-veil-cast-path` has landed the provenance record and its snapshot
      registration; this change reads it and adds no storage of its own.

## 2. Typed effect

- [x] 2.1 Add the reveal dataclass in `world/skills/effects.py` carrying its strength, with the two
      closed grammar forms in `parse_effect`; every other payload raises `ValueError`.
- [x] 2.2 Test: both forms parse to the right strength and `reveal_disguise:everything` raises.

## 3. Reveal primitive and handler

- [x] 3.1 Add the provenance-scoped reveal write to `world/rules/skill_effects.py`.
- [x] 3.2 Add `_handle_reveal_disguise` in `world/rules/action.py` and register the prefix with
      `frozenset({"traits"})` and an empty required event context.
- [x] 3.3 Test: a reveal that clears a veil clears its provenance record in the same operation, and a
      rolled-back reveal restores both byte-equal.
- [x] 3.4 Tests: mundane strength lifts a mundane veil; mundane strength leaves a divine veil and all
      state untouched and does not reject; true-name strength lifts a divine veil; either strength
      against an unveiled target is a clean no-op.
- [x] 3.5 Test: a reveal reads and writes nothing but the layer and its provenance — no true trait,
      identity, or persona access.

## 4. Boundary parity

- [x] 4.1 Run the existing disguise boundary tests and confirm the writer ledger still matches without
      a new entry (both writes stay in `world/rules/skill_effects.py`).
- [x] 4.2 Confirm the mundane appraisal lineage is untouched: `true_sight_appraisal` still cannot lift
      a divine veil.

## 5. Behavior contract tests

- [x] 5.1 Put the new tests in `world/rules/tests/test_divine_veil_reveal.py`, composed from synthetic
      skill definitions only — no shipped-content skill names, no data-contract tagging.
- [x] 5.2 Annotate with `covers_requirement` using IDs from
      `uv run --locked python -m tools.spec_traceability list`.
- [x] 5.3 Register the module in exactly one shard of `.github/evennia-shards.json`.

## 6. Verification

- [x] 6.1 Run the focused label
      `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_divine_veil_reveal`
      with `MUD_TEST_SETTINGS=1` passed through the tool's `env` input.
- [x] 6.2 Run the focused labels `world.rules.tests.test_disguise_boundary`,
      `world.skills.tests.test_effects` and the veil-cast module from `divine-veil-cast-path`.
- [x] 6.3 Run `uv run --locked python -m tools.spec_traceability check` and
      `uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`.
- [x] 6.4 `openspec validate divine-veil-reveal --strict`.

## 7. Main-spec truthfulness

- [x] 7.1 Note for the archive phase: the delta's ADDED `skill-handler` requirement ("The disguise
      layer has a provenance-scoped reveal primitive") is not in the main index until the archive
      sync, so the reveal behavior tests annotate only pre-existing main requirement IDs they
      substantively exercise (`skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass`,
      `disguised-stats-boundary::the-disguise-layer-records-the-provenance-of-the-veil-it-holds`,
      `action-resolution-pipeline::the-effect-resolution-registry-is-open-prefix-keyed-and-every-handler-declares-its`,
      `action-resolution-pipeline::resolution-is-atomic-a-failure-at-any-step-leaves-zero-state-mutated`,
      `effect-context-validation::effect-handlers-declare-their-required-event-context`). At sync the
      archive step must add `covers_requirement("skill-handler::the-disguise-layer-has-a-provenance-scoped-reveal-primitive")`
      to the direct-primitive test (`RevealPrimitiveTests.test_mundane_strength_lifts_an_authored_mundane_veil`)
      so the ADDED requirement is covered and the traceability gate stays green post-archive (the
      conferral-revocation precedent re-pointed its annotations at sync).
