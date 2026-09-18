## 1. Day identity

- [ ] 1.1 Add a deterministic absolute-day-ordinal helper in `world/rules/progression.py` derived
      from `WorldClock.calendar` and the `clock.yaml` constants (`days_per_season`,
      `seasons_per_year`); it reads no literal and no wall-clock time.
- [ ] 1.2 Test (`unittest.TestCase`): the ordinal is strictly monotonic across a day roll, a season
      roll and a year roll, and is stable within one day.

## 2. The cadence claim

- [ ] 2.1 Add the persisted claim store `entity.db.skill_practice_day` (`{skill_key: day_ordinal}`)
      with a read/write pair in `world/rules/progression.py`; tolerate a missing attribute.
- [ ] 2.2 Gate `grant_skill_practice_xp()` on the claim for `SkillCategory.DIVINE_MYSTERY` ACTIVE
      skills, evaluated **before** `_claim_practice`, returning `False` when the day is taken.
- [ ] 2.3 Record the day only on the path that actually awards, so a refused award never consumes it.

## 3. Rollback face

- [ ] 3.1 Register `skill_practice_day` beside `skill_proficiency` in all three of its real homes:
      `_snapshot_entity_state` and `_restore_entity_state` in `world/rules/action.py` (this is what
      backs the combat round path — `world/rules/combat_session.py` has no attribute tuple to edit),
      and the explicit tuples in `world/rules/cast_settlement.py` and `world/rules/clock.py`.
- [ ] 3.2 Test: after a rolled-back resolution, both `skill_proficiency` and `skill_practice_day` are
      byte-equal to their pre-action values and a same-day retry accrues.
- [ ] 3.3 Test the same rollback on the COMBAT round path, not only the out-of-combat cast path, since
      the two reach different snapshot mechanisms.

## 4. Behavior contract tests

- [ ] 4.1 New test module `world/rules/tests/test_divine_digestion_cadence.py` built on synthetic
      skill definitions (no shipped-content names, no data-contract tagging): second same-day use
      accrues nothing; next calendar day accrues; two different divine-mystery skills each hold their
      own day; a `requires_divine_arts` skill outside the category accrues twice in one day; a
      day-blocked call leaves the per-tick claim set untouched.
- [ ] 4.2 Annotate the new tests with `covers_requirement` using IDs from
      `uv run --locked python -m tools.spec_traceability list`; do not hand-write IDs.
- [ ] 4.3 Register the new module in exactly one shard of `.github/evennia-shards.json`.

## 5. Verification

- [ ] 5.1 Run the focused label
      `uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_divine_digestion_cadence`
      with `MUD_TEST_SETTINGS=1` passed through the tool's `env` input.
- [ ] 5.2 Run the focused existing lineage label
      `world.rules.tests.test_skill_lineage` to prove non-divine accrual is unchanged.
- [ ] 5.3 Run `uv run --locked python -m tools.spec_traceability check` and
      `uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`.
- [ ] 5.4 `openspec validate divine-mystery-digestion-cadence --strict`.
