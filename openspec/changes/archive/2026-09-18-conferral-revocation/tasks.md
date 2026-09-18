## 1. Typed effect

- [x] 1.1 Add a payload-free frozen revoke-grants dataclass in `world/skills/effects.py` and its
      bare-prefix branch in `parse_effect`; a payload raises `ValueError`.
- [x] 1.2 Test: the bare form parses into the dataclass and `revoke_grants:<anything>` raises.

## 2. Buff-side clear

- [x] 2.1 Add `clear_conferred_growth_rates(entity)` to `world/rules/buffs.py`, removing every
      `conferred_growth_rate` instance regardless of `instance_key`, through the buff handler rather
      than raw storage.
- [x] 2.2 Test: a target carrying two sources' growth-rate instances plus one unrelated buff keeps only
      the unrelated buff, and `growth_rate_multiplier()` returns `1.0` afterwards.

## 3. Revocation primitive

- [x] 3.1 Add the revocation write to `world/rules/skill_effects.py`, clearing
      `entity.db.skill_grants` and calling the buff clear.
- [x] 3.2 Test: the target's own owned passives still fold into `effective_value()` after revocation;
      a target with nothing conferred is a clean no-op.

## 4. Effect handler

- [x] 4.1 Add `_handle_revoke_grants` in `world/rules/action.py`, staging one pending effect that
      performs both writes, and register the prefix with `frozenset({"skill_grants", "buffs"})` and an
      empty required event context.
- [x] 4.2 Test: a cast of a synthetic skill declaring `revoke_grants` at a target strips grants and
      growth-rate buffs.
- [x] 4.3 Test: a resolution whose later pending effect fails restores both `skill_grants` and the buff
      store byte-equal.

## 5. Behavior contract tests

- [x] 5.1 Put the new tests in `world/rules/tests/test_conferral_revocation.py`, composed from
      synthetic skill definitions only — no shipped-content skill names, no data-contract tagging.
- [x] 5.2 Annotate with `covers_requirement` using IDs from
      `uv run --locked python -m tools.spec_traceability list`.
- [x] 5.3 Register the module in exactly one shard of `.github/evennia-shards.json`.

## 6. Verification

- [x] 6.1 Run the focused label
      `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_conferral_revocation`
      with `MUD_TEST_SETTINGS=1` passed through the tool's `env` input.
- [x] 6.2 Run the focused labels `world.skills.tests.test_effects` and the conferral-cast module from
      `conferral-grant-store` to prove the write side is unchanged.
- [x] 6.3 Run `uv run --locked python -m tools.spec_traceability check` and
      `uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`.
- [x] 6.4 `openspec validate conferral-revocation --strict`.

## 7. Main-spec truthfulness

- [x] 7.1 Note for the archive phase: the delta's ADDED `skill-handler` requirement is not in the main
      index until the archive sync, so the revocation behavior tests annotate only pre-existing main
      requirement IDs they substantively exercise (`skill-effect-model::parse-effect-classifies-every-...`,
      `skill-handler::effective-value-is-the-sole-resolution-time-multiplier-application-point-and-
      never-writes-to-entity-traits`, `action-resolution-pipeline::the-effect-resolution-registry-is-
      open-prefix-keyed-and-every-handler-declares-its`,
      `action-resolution-pipeline::resolution-is-atomic-a-failure-at-any-step-leaves-zero-state-mutated`,
      `effect-context-validation::effect-handlers-declare-their-required-event-context`). At sync the
      archive step must add `covers_requirement("skill-handler::the-conferral-store-has-a-revocation-
      primitive-reachable-from-a-skill")` to `RevocationPrimitiveTests.test_revocation_clears_both_halves_...`
      (the direct-primitive test) so the ADDED requirement is covered and the traceability gate stays
      green post-archive (the conferral-grant-store precedent re-pointed its annotations at sync).