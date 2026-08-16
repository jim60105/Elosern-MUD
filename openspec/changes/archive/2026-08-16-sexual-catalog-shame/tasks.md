## 1. Confirm the dependency surface this change reads

- [x] 1.1 Confirm `sexual-act-seeds` has landed with `SHAME_ACTS` containing exactly `shame_hem_lift`
  and `world/rules/rulebook/sexual.yaml` containing `exposure_up_on_self_exposure`
  (`when: {event: self_exposure}`, `then: {field: exposure, delta: "+1"}`). If
  `exposure_up_on_self_exposure`'s event name differs from `self_exposure` at implementation time,
  update every `sexual_events` reference in this change's tasks accordingly before writing any row.
- [x] 1.2 Confirm `world/rules/rulebook/combat_modifiers.yaml`'s `high_arousal_agility_accuracy_
  penalty` row (`{field: arousal, gte: 高度}` → `{agility: "-20%", accuracy: -15}`) is unchanged —
  design.md D-2's reuse claim for `shame_provocative_gaze` depends on it firing exactly as described.
- [x] 1.3 Confirm `SexualState.exposure_act_count`/`watched_count`/`masturbation_count`/
  `hostile_act_count` and their sole mutators are unchanged in `world/rules/sexual_state.py`.
- [x] 1.4 Confirm `_act_family()`'s structural requirement that a non-`SELF`/`NONE`, non-異種/神之秘法
  act declares a non-null `target_part` is unchanged — this proposal's three `AREA` rows depend on
  it (and on `target_part="腰腹"` being a valid `BODY_PARTS` member, which it already is).

## 2. `world/skills/sexual_acts/shame.py`: Tier 1 (three acts)

- [x] 2.1 Extend `SHAME_ACTS`'s `_act_family("羞恥", ...)` call with the three Tier 1 rows from
  design.md D-1 (`shame_half_expose_chest`, `shame_half_expose_lower`, `shame_loosen_collar`), each
  `unlock={"exposure_act_count": 5}`, `target_spec=TargetSpec.SELF`, `actor_part=None`,
  `target_part=None`, `actor_pleasure_ratio=1.0`, `actor_counters=("exposure_act_count",)`,
  `participant_counters=()`, `sexual_events=("self_exposure",)`, `resistible=False`.

## 3. `world/skills/sexual_acts/shame.py`: Tier 2 (two acts)

- [x] 3.1 Add `shame_full_expose` (`unlock={"exposure_act_count": 20}`, otherwise matching Tier 1's
  shape).
- [x] 3.2 Add `shame_public_masturbation` (`unlock={"exposure_act_count": 20, "masturbation_count":
  25}`, `actor_counters=("exposure_act_count", "masturbation_count", "watched_count")`,
  `sexual_events=("self_exposure", "masturbation_climax")`).

## 4. `world/skills/sexual_acts/shame.py`: Tier 3 (two acts)

- [x] 4.1 Add `shame_provocative_gaze` (`unlock={"watched_count": 10}`,
  `target_spec=TargetSpec.AREA`, `actor_part=None`, `target_part="腰腹"`,
  `actor_pleasure_ratio=0.4`, `actor_counters=("hostile_act_count",)`, `participant_counters=()`,
  `sexual_events=()`, `resistible=True`).
- [x] 4.2 Add `shame_public_performance` (`unlock={"watched_count": 10, "exposure_act_count": 20}`,
  `target_spec=TargetSpec.AREA`, `actor_part=None`, `target_part="腰腹"`,
  `actor_pleasure_ratio=0.6`, `actor_counters=("watched_count", "exposure_act_count")`,
  `participant_counters=()`, `sexual_events=("self_exposure",)`, `resistible=True`).

## 5. `world/skills/sexual_acts/shame.py`: Tier 4 (two acts)

- [x] 5.1 Add `shame_devoted_pose` (`unlock={"exposure_act_count": 50}`,
  `target_spec=TargetSpec.AREA`, `actor_part=None`, `target_part="腰腹"`,
  `actor_pleasure_ratio=0.5`, `actor_counters=("exposure_act_count",)`, `participant_counters=()`,
  `sexual_events=("self_exposure",)`, `resistible=True`).
- [x] 5.2 Add `shame_shameless_declaration` (`unlock={"exposure_act_count": 50, "watched_count":
  30}`, `target_spec=TargetSpec.SELF`, `actor_part=None`, `target_part=None`,
  `actor_pleasure_ratio=1.0`, `actor_counters=("exposure_act_count",)`, `participant_counters=()`,
  `sexual_events=("self_exposure",)`, `resistible=False`).

## 6. Behaviour tests for the delta spec

- [x] 6.1 Run `uv run --locked python -m tools.spec_traceability list` and note the canonical
  requirement IDs for `sexual-catalog-shame::*` from this change's delta spec.
- [x] 6.2 Add `world/skills/sexual_acts/tests/test_shame_catalog.py` (new `EvenniaTest`-based module)
  covering each delta-spec scenario: a Tier 1 act absent below threshold and present at it;
  `shame_public_masturbation`'s compound gate; `shame_provocative_gaze` gated by `watched_count`
  alone; `shame_shameless_declaration`'s compound gate; every SELF reusing act raising the actor's
  `exposure` by exactly one on cast, and the two AREA reusing acts (公開表演, 獻身姿態) raising each
  *target's* `exposure` by exactly one while the actor's stays put (design.md D-6);
  `shame_provocative_gaze` NOT raising `exposure`;
  `shame_public_masturbation`'s three-counter/two-event cast; `shame_public_performance`'s
  two-counter cast (`watched_count` and `exposure_act_count` both +1, target's counters unchanged);
  `shame_provocative_gaze` crediting `hostile_act_count` on the actor only, never the target; all
  three `AREA` acts declaring `target_part == "腰腹"`.
- [x] 6.3 Add one test (not in the delta spec, a design.md D-2 regression) proving
  `shame_provocative_gaze` raises a target's `pleasure` — confirming the reuse path design.md D-2
  depends on is live, even though the resulting combat-modifier firing is probabilistic and not
  itself asserted here (that assertion belongs to `combat_modifiers.yaml`'s own existing test suite,
  unchanged by this proposal).
- [x] 6.4 Apply `covers_requirement("sexual-catalog-shame::<id>")` (using the IDs from 6.1) to each
  test function whose assertions establish that requirement.
- [x] 6.5 Run `uv run --locked python -m tools.spec_traceability check` and confirm every
  `sexual-catalog-shame` requirement is covered.

## 7. Collateral test-surface updates (shared with sexual-catalog-solo, section 6)

Pre-existing tests written while every registered act was unconditionally owned assert a fresh
entity's unlocked set as `sorted(SEXUAL_ACT_REGISTRY)` (or pin the SEXUAL_ACT category's key set).
Registering counter-gated acts breaks each one; each site must now read the unconditionally-unlocked
subset — the acts whose `unlock` mapping is empty. This mirrors exactly how `sexual-act-seeds`
updated its own collateral tests when it moved the registry from empty to seed-only.

- [x] 7.1 In `world/skills/sexual_acts/tests/test_registry_structure.py`, redefine
  `OwnershipDriftGuardTests._SEED_KEYS` as `sorted(key for key, act in SEXUAL_ACT_REGISTRY.items()
  if not act.unlock)` (keeping the class docstring's "unconditionally-unlocked" intent) and update
  the `test_owned_keys_resolves_without_a_sexual_attribute` expectation the same way.
- [x] 7.2 In `world/skills/tests/test_handler.py`, `world/skills/tests/test_inventory.py`,
  `world/rules/tests/test_combat_session.py`, `world/rules/tests/test_combat_view.py`, and
  `web/webclient/presentation/tests/test_character_panel.py`, replace every
  `*sorted(SEXUAL_ACT_REGISTRY)` fresh-entity expectation with the same empty-unlock subset
  expression, updating the adjacent comments where they count "the seven seed acts".
- [x] 7.3 In `world/rules/tests/test_status_query.py`, redefine `_SEED_KEYS` with the same
  empty-unlock filter (its comment already says "the unconditionally-owned seed acts").
- [x] 7.4 In `world/skills/tests/test_registry.py`, extend the pinned `SkillCategory.SEXUAL_ACT`
  key set in `test_per_category_key_sets_match_the_d4_classification_table` with this change's nine
  keys (matching `test_registry_structure.py`'s key/registry agreement check).

## 8. Full verification

- [x] 8.1 Run `uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests
  world.rules.tests` and confirm the whole package suite passes, including
  `test_registry_structure.py` and `test_acceptance.py` against the now-ten-row `SHAME_ACTS` tuple.
- [x] 8.2 Run `uv run --locked python -m compileall -q world`.
- [x] 8.3 Run `openspec validate sexual-catalog-shame --strict` and resolve any reported issue.
- [x] 8.4 Confirm no file outside `world/skills/sexual_acts/shame.py`, the new
  `world/skills/sexual_acts/tests/test_shame_catalog.py`, the section-7 collateral test files, and
  this change's own artifacts (`proposal.md`/`tasks.md` edits and the synced
  `openspec/specs/sexual-catalog-shame/spec.md`) was touched, matching the amended proposal Impact
  list exactly — in particular, confirm
  `world/rules/rulebook/sexual.yaml` has zero diff from this change.
