## 1. Confirm the dependency surface this change reads

- [ ] 1.1 Confirm `sexual-act-seeds` has landed with `SHAME_ACTS` containing exactly `shame_hem_lift`
  and `world/rules/rulebook/sexual.yaml` containing `exposure_up_on_self_exposure`
  (`when: {event: self_exposure}`, `then: {field: exposure, delta: "+1"}`). If
  `exposure_up_on_self_exposure`'s event name differs from `self_exposure` at implementation time,
  update every `sexual_events` reference in this change's tasks accordingly before writing any row.
- [ ] 1.2 Confirm `world/rules/rulebook/combat_modifiers.yaml`'s `high_arousal_agility_accuracy_
  penalty` row (`{field: arousal, gte: 高度}` → `{agility: "-20%", accuracy: -15}`) is unchanged —
  design.md D-2's reuse claim for `shame_provocative_gaze` depends on it firing exactly as described.
- [ ] 1.3 Confirm `SexualState.exposure_act_count`/`watched_count`/`masturbation_count`/
  `hostile_act_count` and their sole mutators are unchanged in `world/rules/sexual_state.py`.
- [ ] 1.4 Confirm `_act_family()`'s structural requirement that a non-`SELF`/`NONE`, non-異種/神之秘法
  act declares a non-null `target_part` is unchanged — this proposal's three `AREA` rows depend on
  it (and on `target_part="腰腹"` being a valid `BODY_PARTS` member, which it already is).

## 2. `world/skills/sexual_acts/shame.py`: Tier 1 (three acts)

- [ ] 2.1 Extend `SHAME_ACTS`'s `_act_family("羞恥", ...)` call with the three Tier 1 rows from
  design.md D-1 (`shame_half_expose_chest`, `shame_half_expose_lower`, `shame_loosen_collar`), each
  `unlock={"exposure_act_count": 5}`, `target_spec=TargetSpec.SELF`, `actor_part=None`,
  `target_part=None`, `actor_pleasure_ratio=1.0`, `actor_counters=("exposure_act_count",)`,
  `participant_counters=()`, `sexual_events=("self_exposure",)`, `resistible=False`.

## 3. `world/skills/sexual_acts/shame.py`: Tier 2 (two acts)

- [ ] 3.1 Add `shame_full_expose` (`unlock={"exposure_act_count": 20}`, otherwise matching Tier 1's
  shape).
- [ ] 3.2 Add `shame_public_masturbation` (`unlock={"exposure_act_count": 20, "masturbation_count":
  25}`, `actor_counters=("exposure_act_count", "masturbation_count", "watched_count")`,
  `sexual_events=("self_exposure", "masturbation_climax")`).

## 4. `world/skills/sexual_acts/shame.py`: Tier 3 (two acts)

- [ ] 4.1 Add `shame_provocative_gaze` (`unlock={"watched_count": 10}`,
  `target_spec=TargetSpec.AREA`, `actor_part=None`, `target_part="腰腹"`,
  `actor_pleasure_ratio=0.4`, `actor_counters=("hostile_act_count",)`, `participant_counters=()`,
  `sexual_events=()`, `resistible=True`).
- [ ] 4.2 Add `shame_public_performance` (`unlock={"watched_count": 10, "exposure_act_count": 20}`,
  `target_spec=TargetSpec.AREA`, `actor_part=None`, `target_part="腰腹"`,
  `actor_pleasure_ratio=0.6`, `actor_counters=("watched_count", "exposure_act_count")`,
  `participant_counters=()`, `sexual_events=("self_exposure",)`, `resistible=True`).

## 5. `world/skills/sexual_acts/shame.py`: Tier 4 (two acts)

- [ ] 5.1 Add `shame_devoted_pose` (`unlock={"exposure_act_count": 50}`,
  `target_spec=TargetSpec.AREA`, `actor_part=None`, `target_part="腰腹"`,
  `actor_pleasure_ratio=0.5`, `actor_counters=("exposure_act_count",)`, `participant_counters=()`,
  `sexual_events=("self_exposure",)`, `resistible=True`).
- [ ] 5.2 Add `shame_shameless_declaration` (`unlock={"exposure_act_count": 50, "watched_count":
  30}`, `target_spec=TargetSpec.SELF`, `actor_part=None`, `target_part=None`,
  `actor_pleasure_ratio=1.0`, `actor_counters=("exposure_act_count",)`, `participant_counters=()`,
  `sexual_events=("self_exposure",)`, `resistible=False`).

## 6. Behaviour tests for the delta spec

- [ ] 6.1 Run `uv run --locked python -m tools.spec_traceability list` and note the canonical
  requirement IDs for `sexual-catalog-shame::*` from this change's delta spec.
- [ ] 6.2 Add `world/skills/sexual_acts/tests/test_shame_catalog.py` (new `EvenniaTest`-based module)
  covering each delta-spec scenario: a Tier 1 act absent below threshold and present at it;
  `shame_public_masturbation`'s compound gate; `shame_provocative_gaze` gated by `watched_count`
  alone; `shame_shameless_declaration`'s compound gate; every reusing act raising `exposure` by
  exactly one on cast; `shame_provocative_gaze` NOT raising `exposure`;
  `shame_public_masturbation`'s three-counter/two-event cast; `shame_public_performance`'s
  two-counter cast (`watched_count` and `exposure_act_count` both +1, target's counters unchanged);
  `shame_provocative_gaze` crediting `hostile_act_count` on the actor only, never the target; all
  three `AREA` acts declaring `target_part == "腰腹"`.
- [ ] 6.3 Add one test (not in the delta spec, a design.md D-2 regression) proving
  `shame_provocative_gaze` raises a target's `pleasure` — confirming the reuse path design.md D-2
  depends on is live, even though the resulting combat-modifier firing is probabilistic and not
  itself asserted here (that assertion belongs to `combat_modifiers.yaml`'s own existing test suite,
  unchanged by this proposal).
- [ ] 6.4 Apply `covers_requirement("sexual-catalog-shame::<id>")` (using the IDs from 6.1) to each
  test function whose assertions establish that requirement.
- [ ] 6.5 Run `uv run --locked python -m tools.spec_traceability check` and confirm every
  `sexual-catalog-shame` requirement is covered.

## 7. Full verification

- [ ] 7.1 Run `uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests
  world.rules.tests` and confirm the whole package suite passes, including
  `test_registry_structure.py` and `test_acceptance.py` against the now-ten-row `SHAME_ACTS` tuple.
- [ ] 7.2 Run `uv run --locked python -m compileall -q world`.
- [ ] 7.3 Run `openspec validate sexual-catalog-shame --strict` and resolve any reported issue.
- [ ] 7.4 Confirm no file outside `world/skills/sexual_acts/shame.py` and the new
  `world/skills/sexual_acts/tests/test_shame_catalog.py` was touched, matching the proposal's Impact
  list exactly — in particular, confirm `world/rules/rulebook/sexual.yaml` has zero diff from this
  change.
