## 1. Confirm the dependency surface this change reads and extends

- [ ] 1.1 Confirm `world/skills/sexual_acts/_builder.py`'s `_act_family()` row-tuple shape is still
  `(key, label, description, target_spec, unlock, base_pleasure, actor_part, target_part,
  actor_pleasure_ratio, actor_counters, participant_counters, sexual_events, resistible)` and its
  structural checks (forbidden events, non-zero `actor_pleasure_ratio` unless divine, no
  `GENERIC_BODY_PART`, part membership, no target part for 異種/神之秘法) are unchanged from
  design.md's description. If the row shape has moved, re-derive design.md's D-1 table against the
  new shape before writing any act row.
- [ ] 1.2 Confirm `SexualState`'s eleven counter attribute names and their sole mutators
  (`masturbation_count`→`record_masturbation()`, `exposure_act_count`→`record_exposure_act()`,
  `duo_act_count`→`record_duo_act()`, `hostile_act_count`→`record_hostile_act()`) are unchanged in
  `world/rules/sexual_state.py`.
- [ ] 1.3 Confirm `resolve_part()` in `world/rules/sexual_act_effects.py` still collapses `None` to
  `GENERIC_BODY_PART` unconditionally (design.md D-3's dependency) and that
  `world/lore/sexual_vocab.py::BODY_PARTS` still excludes any hand-adjacent part (design.md D-4's
  dependency — if a hand part now exists, revisit `partner_hand_hold`'s part choice before writing
  it).
- [ ] 1.4 Confirm `world/rules/rulebook/sexual.yaml`'s existing `shame_up_on_exposure_increase` rule
  (`{field_changed: exposure, direction: up}` → `{field: shame, delta: "+1"}`) and `FIELD_KINDS` in
  `world/rules/sexual_transitions.py` still include `exposure` as an ordered-level kind, so the new
  rule needs no `FIELD_KINDS` change.
- [ ] 1.5 Confirm `world/rules/tests/test_sexual_transitions.py`'s `test_every_rule_id_has_a_test()`
  and `world/skills/sexual_acts/tests/test_registry_structure.py`'s structural checks are still
  present and passing on the current worktree HEAD before adding any new row (a pre-existing failure
  here is out of this change's scope and must be reported, not silently worked around).

## 2. `world/rules/rulebook/sexual.yaml` and its test

- [ ] 2.1 Add the `exposure_up_on_self_exposure` rule row (design.md D-2) in the file's existing
  event-conditioned-rule style, placed near `exposure_up_on_clothing_damaged` for readability.
- [ ] 2.2 Add `test_rule_exposure_up_on_self_exposure` to
  `world/rules/tests/test_sexual_transitions.py`, mirroring `test_rule_exposure_up_on_clothing_
  damaged`'s shape: call `apply_event(entity, "self_exposure")` and assert `exposure`'s ordinal rose
  by exactly one.
- [ ] 2.3 Add a second test in the same module (or extend 2.2) asserting the cascade into `shame`
  within the same `apply_event()` call, per the delta spec's "cascades within the same call"
  scenario — construct an entity with `shame` below ceiling, call `apply_event(entity,
  "self_exposure")` once, and assert both `exposure` and `shame` moved.
- [ ] 2.4 Run `uv run --locked evennia test --settings test_settings.py --keepdb
  world.rules.tests.test_sexual_transitions` and confirm the whole module passes, not just the two
  new tests.

## 3. `world/skills/sexual_acts/solo.py`: the three solo seeds

- [ ] 3.1 Replace `SOLO_ACTS`'s empty tuple with `_act_family("獨處", <three rows>)` using design.md
  D-1's table for `solo_self_touch`, `solo_fondle_breasts`, and `solo_thigh_rub` verbatim (labels,
  descriptions, parts, `base_pleasure`, counters, events, `resistible=False`).
- [ ] 3.2 Confirm the module still imports only `SkillDef`/`SexualActDef`/`_act_family` (no new
  imports needed for plain data rows).

## 4. `world/skills/sexual_acts/shame.py`: the shame seed

- [ ] 4.1 Replace `SHAME_ACTS`'s empty tuple with `_act_family("羞恥", <one row>)` for
  `shame_hem_lift`, using `actor_part=None`, `target_part=None`, `sexual_events=("self_exposure",)`,
  per design.md D-1/D-3.

## 5. `world/skills/sexual_acts/partner.py`: the two partner seeds

- [ ] 5.1 Replace `PARTNER_ACTS`'s empty tuple with `_act_family("關係", <two rows>)` for
  `partner_caress` and `partner_hand_hold`, both `TargetSpec.SINGLE`, `resistible=True`, both parts
  `"腰腹"` per design.md D-1/D-4.

## 6. `world/skills/sexual_acts/combat.py`: the combat seed

- [ ] 6.1 Replace `COMBAT_ACTS`'s empty tuple with `_act_family("戰鬥", <one row>)` for
  `combat_tease`, `TargetSpec.SINGLE`, `resistible=True`, `actor_counters=("hostile_act_count",)`,
  `participant_counters=()`, per design.md D-1.

## 7. Behaviour tests for the delta spec

- [ ] 7.1 Run `uv run --locked python -m tools.spec_traceability list` and note the canonical
  requirement IDs generated for `sexual-act-seeds::*` from this change's already-written delta spec
  (`specs/sexual-act-seeds/spec.md`).
- [ ] 7.2 Add behaviour tests under `world/skills/sexual_acts/tests/` (new module, e.g.
  `test_seed_acts.py`, `EvenniaTest`-based since casting exercises `ActionResolver`) covering each
  delta-spec scenario: all seven seeds present in `owned_keys()` at zero counters;
  `interspecies`/`divine` stay `()`; each SELF seed's `resistible is False` and each SINGLE seed's
  `resistible is True`; `solo_*` increments `masturbation_count` on the actor only; only
  `solo_self_touch` adds `"自慰"` to `experience_types`; `partner_*` increments `duo_act_count` on
  both participants; `combat_tease` increments `hostile_act_count` on the actor only.
- [ ] 7.3 Apply `covers_requirement("sexual-act-seeds::<id>")` (using the IDs from 7.1) to the test
  function whose assertions establish each requirement — one test may cover more than one scenario
  under the same requirement heading; do not annotate an unrelated or assertion-free test.
- [ ] 7.4 Run `uv run --locked python -m tools.spec_traceability check` and confirm every
  `sexual-act-seeds` requirement is covered.

## 8. Full verification

- [ ] 8.1 Run `uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests
  world.rules.tests` and confirm the whole package suite passes, including
  `test_registry_structure.py` and `test_acceptance.py` against the now-non-empty registry.
- [ ] 8.2 Run `uv run --locked python -m compileall -q world` to catch any syntax error the above
  test run would not otherwise isolate cleanly.
- [ ] 8.3 Run `openspec validate sexual-act-seeds --strict` and resolve any reported issue.
- [ ] 8.4 Confirm no file outside `world/rules/rulebook/sexual.yaml`,
  `world/rules/tests/test_sexual_transitions.py`, `world/skills/sexual_acts/{solo,shame,partner,
  combat}.py`, and the new `world/skills/sexual_acts/tests/test_seed_acts.py` was touched — matching
  the proposal's declared Impact list exactly.
