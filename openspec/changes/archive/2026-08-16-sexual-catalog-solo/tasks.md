## 1. Confirm the dependency surface this change reads

- [x] 1.1 Confirm `sexual-act-seeds` (this proposal's dependency) has landed with `SOLO_ACTS`
  containing exactly the three seed rows described in its design.md, and that `world/skills/
  sexual_acts/solo.py`'s import list (`SkillDef`, `SexualActDef`, `_act_family`) is unchanged. If
  `sexual-act-seeds` has not yet been implemented/merged, coordinate sequencing before starting task
  2 — this proposal's `SOLO_ACTS` tuple must extend, not replace, the seed rows.
- [x] 1.2 Confirm `_act_family()`'s row-tuple shape and validation (positive `base_pleasure`, no
  `GENERIC_BODY_PART`, part membership in `BODY_PARTS`) are unchanged from
  `sexual-catalog-solo/design.md`'s D-2 quoted excerpt. If `base_pleasure` has gained the ability to
  be negative or zero, re-open D-2/D-3's deferral decision before writing tasks 3-5 — the three
  deferred acts (快感控制, 寸止, 極限忍耐) may now be buildable.
- [x] 1.3 Confirm `SexualState.masturbation_count`/`toy_use_count` and their sole mutators
  (`record_masturbation()`, `record_toy_use()`) are unchanged in `world/rules/sexual_state.py`.
- [x] 1.4 Confirm `world/rules/rulebook/sexual.yaml`'s `masturbation_climax` event and its
  `experience_masturbation_added` rule are unchanged — this proposal needs no rulebook edit, and this
  step confirms that remains true.

## 2. `world/skills/sexual_acts/solo.py`: Tier 1 (five acts)

- [x] 2.1 Extend `SOLO_ACTS`'s `_act_family("獨處", ...)` call with the five Tier 1 rows from
  design.md D-1 (`solo_deep_touch`, `solo_both_hands`, `solo_finger_lick`, `solo_rear_touch`,
  `solo_nipple_play`), each `unlock={"masturbation_count": 10}`, `actor_counters=
  ("masturbation_count",)`, `participant_counters=()`, `resistible=False`. Only `solo_deep_touch` and
  `solo_both_hands` declare `sexual_events=("masturbation_climax",)`; the other three declare `()`.

## 3. `world/skills/sexual_acts/solo.py`: Tier 2 (three acts)

- [x] 3.1 Add the three Tier 2 rows (`solo_toy_vibrator`, `solo_toy_clamps`, `solo_toy_plug`), each
  `unlock={"masturbation_count": 25}`, `actor_counters=("masturbation_count", "toy_use_count")`,
  `sexual_events=()`.

## 4. `world/skills/sexual_acts/solo.py`: Tier 3 (three acts)

- [x] 4.1 Add the three Tier 3 rows (`solo_toy_advanced_link`, `solo_toy_advanced_full`,
  `solo_bound_masturbation`), each `unlock={"masturbation_count": 25, "toy_use_count": 15}` (the
  compound gate — design.md's note under D-1 on why `toy_use_count` alone is not used), `actor_counters=
  ("masturbation_count", "toy_use_count")`, `sexual_events=()`. Set `base_pleasure` to `24`
  (`solo_toy_advanced_link`), `26` (`solo_toy_advanced_full`), and `25`
  (`solo_bound_masturbation`) exactly — `solo_bound_masturbation` is deliberately mid-pack, not the
  tier's highest, per design.md D-4.

## 5. Behaviour tests for the delta spec

- [x] 5.1 Run `uv run --locked python -m tools.spec_traceability list` and note the canonical
  requirement IDs for `sexual-catalog-solo::*` from this change's delta spec.
- [x] 5.2 Add `world/skills/sexual_acts/tests/test_solo_catalog.py` (new `EvenniaTest`-based module,
  matching `sexual-act-seeds`'s `test_seed_acts.py` shape) covering each delta-spec scenario: a Tier
  1 act absent below threshold and present at it; a Tier 2 act gated by `masturbation_count` alone
  (present at `toy_use_count == 0`); a Tier 3 act gated by the **compound** threshold — absent at
  `toy_use_count == 15, masturbation_count == 24` and present once `masturbation_count` reaches `25`;
  a Tier 2/3 cast incrementing both counters by exactly one; only `solo_deep_touch`/`solo_both_hands`
  adding `"自慰"` to `experience_types`, with a control case (`solo_finger_lick`) proving the other
  nine acts add nothing.
- [x] 5.3 Apply `covers_requirement("sexual-catalog-solo::<id>")` (using the IDs from 5.1) to each
  test function whose assertions establish that requirement.
- [x] 5.4 Run `uv run --locked python -m tools.spec_traceability check` and confirm every
  `sexual-catalog-solo` requirement is covered.

## 6. Collateral test-surface updates (pre-existing pinned-registry expectations)

Pre-existing tests written while every registered act was unconditionally owned assert a fresh
entity's unlocked set as `sorted(SEXUAL_ACT_REGISTRY)` (or pin the SEXUAL_ACT category's key set).
Registering counter-gated acts breaks each one; each site must now read the unconditionally-unlocked
subset — the acts whose `unlock` mapping is empty. This mirrors exactly how `sexual-act-seeds`
updated its own collateral tests when it moved the registry from empty to seed-only.

- [x] 6.1 In `world/skills/sexual_acts/tests/test_registry_structure.py`, redefine
  `OwnershipDriftGuardTests._SEED_KEYS` as `sorted(key for key, act in SEXUAL_ACT_REGISTRY.items()
  if not act.unlock)` (keeping the class docstring's "unconditionally-unlocked" intent) and update
  the `test_owned_keys_resolves_without_a_sexual_attribute` expectation the same way.
- [x] 6.2 In `world/skills/tests/test_handler.py`, `world/skills/tests/test_inventory.py`,
  `world/rules/tests/test_combat_session.py`, `world/rules/tests/test_combat_view.py`, and
  `web/webclient/presentation/tests/test_character_panel.py`, replace every
  `*sorted(SEXUAL_ACT_REGISTRY)` fresh-entity expectation with the same empty-unlock subset
  expression, updating the adjacent comments where they count "the seven seed acts".
- [x] 6.3 In `world/rules/tests/test_status_query.py`, redefine `_SEED_KEYS` with the same
  empty-unlock filter (its comment already says "the unconditionally-owned seed acts").
- [x] 6.4 In `world/skills/tests/test_registry.py`, extend the pinned `SkillCategory.SEXUAL_ACT`
  key set in `test_per_category_key_sets_match_the_d4_classification_table` with this change's
  eleven keys (matching `test_registry_structure.py`'s key/registry agreement check).

## 7. Full verification

- [x] 7.1 Run `uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests
  world.rules.tests` and confirm the whole package suite passes, including
  `test_registry_structure.py` and `test_acceptance.py` against the now-fourteen-row `SOLO_ACTS`
  tuple.
- [x] 7.2 Run `uv run --locked python -m compileall -q world`.
- [x] 7.3 Run `openspec validate sexual-catalog-solo --strict` and resolve any reported issue.
- [x] 7.4 Confirm no file outside `world/skills/sexual_acts/solo.py`, the new
  `world/skills/sexual_acts/tests/test_solo_catalog.py`, the section-6 collateral test files, and
  this change's own artifacts (`proposal.md`/`tasks.md` edits and the synced
  `openspec/specs/sexual-catalog-solo/spec.md`) was touched, matching the amended proposal Impact
  list exactly.
