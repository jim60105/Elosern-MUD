## 1. Confirm the dependency surface this change reads

- [ ] 1.1 **Precondition, not a routine confirmation:** `sexual-catalog-divine-core` (`C7a`) must be
  *implemented* (not merely proposed) before any task below can proceed — `DIVINE_ACTS` must already
  have three entries, the three `divine_*` effect prefixes must already exist in `_EFFECT_HANDLERS`, and
  every handler there must already follow the actor-filter/empty-targets-no-op discipline this proposal
  reuses. As of this proposal's own authoring, `C7a` is committed as an OpenSpec proposal only —
  `DIVINE_ACTS` is still `()` and none of `C7a`'s handlers exist yet. If this check fails, stop and
  implement `C7a` first (or confirm it is being implemented in the same pass); do not attempt to build
  this proposal's four acts against an empty `DIVINE_ACTS`.
- [ ] 1.2 Confirm `_step4b_sexual_resist_gate` (`world/rules/action.py`) is unchanged.
- [ ] 1.3 Confirm `SexualState.__init__`'s `Monster` shame-pinning (`shame.min = shame.max = 0`) is
  unchanged — `clamp_shame_to`'s Monster rejection depends on this staying true.
- [ ] 1.4 Confirm `SexualState.virgin`'s public setter is still unconditionally a no-op once `False`
  (`if not self.virgin: return`) — `restore_purity()`'s non-regression argument (design.md D-4) depends
  on this exact shape.
- [ ] 1.5 Confirm `resist_verdict()`'s existing two short-circuit terms (affinity `auto_comply`,
  `_climax_turn_short_circuit`) and its no-create discipline (`resister.attributes.get(...)`, never
  `resister.sexual`) are unchanged.
- [ ] 1.6 Confirm Evennia objects expose a stable, unique `.id` (database primary key) —
  `world/rules/map_knowledge.py`'s `encode_room(int(location.id))` is the existing in-repo precedent for
  this. `mark_submission`'s caller and `_submission_term` both derive `str(entity.id)`, never
  `_entity_key`/`.key` (confirmed non-unique across same-species `Monster` spawns in `world/maps/
  wilderness_population.py`) — see design.md D-5.

## 2. `world/rules/sexual_state.py`: four new mutators

- [ ] 2.1 Add `saturate_sensitivity()`: iterate `BODY_PARTS` (non-`Monster`) or just
  `GENERIC_BODY_PART` (`Monster`), setting each to `SENSITIVITY_LEVELS[-1]` via the existing
  `sensitivity` proxy's `__setitem__`.
- [ ] 2.2 Add `clamp_shame_to(level)`: raise `ValueError` for a `Monster` entity without mutating
  state; otherwise set `self.shame.max = ordinal`, then `self.shame.min = ordinal` (design.md D-3's
  argued-safe order for `level` at the vocabulary maximum).
- [ ] 2.3 Add `mark_submission(caster_key)`: read the current `submission_marks` (default
  `frozenset()`) from `entity.attributes.get("submission_marks", default=frozenset(),
  category="sexual_state")`, write back the union with `{caster_key}` via `entity.attributes.add`.
  Add a matching `submission_marks` read-only property.
- [ ] 2.4 Add `restore_purity()`: write `entity.attributes.add("virgin", True, category="sexual_state")`
  directly — never call the public `virgin` setter.
- [ ] 2.5 Add all four to `SexualState`'s `__all__`-equivalent surface (public methods/property), no
  changes to `_build_from_baseline` or any existing mutator.

## 3. `world/rules/sexual_resist.py`: wire submission_marks into resist_verdict

- [ ] 3.1 Add `_submission_term(actor, resister) -> bool`: read
  `resister.attributes.get("submission_marks", default=frozenset(), category="sexual_state")`, return
  whether `str(actor.id)` is a member. No materialization of `resister.sexual`.
- [ ] 3.2 Change `resist_verdict()`'s short-circuit condition from `affinity_auto_comply or
  _climax_turn_short_circuit(resister)` to `affinity_auto_comply or _submission_term(actor, resister)
  or _climax_turn_short_circuit(resister)`.
- [ ] 3.3 Confirm no other line in `resist_verdict()` changes — same parameters, same return shape,
  same two pre-existing terms' behavior.

## 4. `world/skills/effects.py`: four new typed effect dataclasses

- [ ] 4.1 Add `SaturateSensitivityEffect`, `ClampShameEffect`, `MarkSubmissionEffect`,
  `RestorePurityEffect` (frozen dataclasses, no fields).
- [ ] 4.2 Register all four in `parse_effect`'s dispatch table.

## 5. `world/rules/action.py`: four new effect handlers

- [ ] 5.1 Add `_handle_saturate_sensitivity(actor, targets, effect_id, context, scale)`: for each
  entity in `targets` excluding `actor`, stage a `PendingEffect` calling
  `entity.sexual.saturate_sensitivity()`. Empty/partial `targets` is an ordinary outcome.
- [ ] 5.2 Add `_handle_clamp_shame(actor, targets, effect_id, context, scale)`: for each entity in
  `targets` excluding `actor`, **eagerly** (before staging anything) check `isinstance(entity, Monster)`
  and raise `RejectedAction(RejectReason.EFFECT_RESOLUTION_FAILED, ...)` directly if so — do NOT stage a
  `PendingEffect` whose `apply()` closure calls `clamp_shame_to` and relies on catching its `ValueError`
  from inside `_commit()`, which would surface as `RejectReason.COMMIT_FAILED` instead (design.md D-3).
  For a non-`Monster` entity, stage a `PendingEffect` calling `entity.sexual.clamp_shame_to("成癮")`.
- [ ] 5.3 Add `_handle_mark_submission(actor, targets, effect_id, context, scale)`: for each entity in
  `targets` excluding `actor`, stage a `PendingEffect` calling
  `entity.sexual.mark_submission(str(actor.id))`.
- [ ] 5.4 Add `_handle_restore_purity(actor, targets, effect_id, context, scale)`: for each entity in
  `targets` excluding `actor`, stage a `PendingEffect` calling `entity.sexual.restore_purity()`.
- [ ] 5.5 Register `"divine_saturate_sensitivity"`, `"divine_clamp_shame"`, `"divine_mark_submission"`,
  and `"divine_restore_purity"` in `_EFFECT_HANDLERS`.

## 6. `world/skills/sexual_acts/divine.py`: the four hand-built acts

- [ ] 6.1 Add `感度創世` (`TargetSpec.SINGLE`, `requires_divine_arts=True`, `unlock={}`,
  `target_part=None`, `resistible=True`, `actor_counters=()`, `participant_counters=()`,
  `effects=["divine_saturate_sensitivity:<key>"]`).
- [ ] 6.2 Add `恥辱剝奪` (same shared fields, `effects=["divine_clamp_shame:<key>"]`).
- [ ] 6.3 Add `絕對從屬` (same shared fields, `effects=["divine_mark_submission:<key>"]`).
- [ ] 6.4 Add `無垢回歸` (same shared fields, `effects=["divine_restore_purity:<key>"]`).
- [ ] 6.5 Populate each `SexualActDef`'s required-but-unused pleasure fields with the same documented
  placeholder convention `sexual-catalog-divine-core` established (`base_pleasure=1`,
  `actor_pleasure_ratio=0.0`, `actor_part=None`).
- [ ] 6.6 Extend `DIVINE_ACTS` to seven entries: the three existing pairs, unmodified, plus these four.

## 7. Behaviour tests for the delta specs

- [ ] 7.1 Run `uv run --locked python -m tools.spec_traceability list` and note the canonical
  requirement IDs for `sexual-catalog-divine-mutators::*`, the updated `sexual-resist-contest::*` IDs
  (the modified "ordinary contest" requirement and the new submission-mark requirement), and the four
  new `sexual-state-handler::*` mutator requirement IDs.
- [ ] 7.2 Add `world/skills/sexual_acts/tests/test_divine_mutators_catalog.py` covering: the race gate
  rejecting all four; `DIVINE_ACTS` growing to seven entries with the first three unchanged; each of
  the four acts' delta-spec scenarios (including each one's resisted-cast no-op); 恥辱剝奪 cast at a
  `Monster` target asserting the reject reason is specifically `EFFECT_RESOLUTION_FAILED`, not
  `COMMIT_FAILED`; 絕對從屬's mark keyed by `str(actor.id)`, including the two-entities-sharing-a-`.key`
  non-collision scenario.
- [ ] 7.3 Add or extend `world/rules/tests/test_sexual_state.py` (or the equivalent existing module)
  covering all `sexual-state-handler` scenarios for the four new mutators, including
  `clamp_shame_to`'s Monster rejection and `restore_purity`'s explicit non-regression scenario (the
  public setter's existing one-way test still passes unmodified after `restore_purity` exists).
- [ ] 7.4 Add or extend `world/rules/tests/test_sexual_resist.py` (or equivalent) covering the new
  `submission_marks` short-circuit: marked-caster auto-comply, unrelated-mark non-interference, and a
  direct inspection that the read never touches `resister.sexual`.
- [ ] 7.5 Apply `covers_requirement(...)` (using the IDs from 7.1) to each test function whose
  assertions establish that requirement, across all three delta specs.
- [ ] 7.6 Run `uv run --locked python -m tools.spec_traceability check` and confirm every requirement
  across `sexual-catalog-divine-mutators`, the modified `sexual-resist-contest` requirement, the new
  `sexual-resist-contest` requirement, and the four new `sexual-state-handler` requirements are covered.

## 8. Full verification

- [ ] 8.1 Run `uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests
  world.rules.tests` and confirm the whole package suite passes, including
  `sexual-resist-contest`'s existing tests (both pre-existing short-circuit terms still behave
  unchanged) and `sexual-catalog-divine-core`'s existing tests (its three acts unaffected).
- [ ] 8.2 Run `uv run --locked python -m compileall -q world`.
- [ ] 8.3 Run `openspec validate sexual-catalog-divine-mutators --strict` and resolve any reported
  issue.
- [ ] 8.4 Confirm no file outside `world/rules/sexual_state.py`, `world/rules/sexual_resist.py`,
  `world/skills/sexual_acts/divine.py`, `world/skills/effects.py`, `world/rules/action.py`, and the new
  `world/skills/sexual_acts/tests/test_divine_mutators_catalog.py` (plus the extended existing test
  modules from §7.3/7.4) was touched — in particular, confirm `world/skills/sexual_acts/_builder.py`,
  `world/rules/rulebook/sexual.yaml`, `world/lore/races.py`, and `world/skills/registry.py` all have
  zero diff from this change, and that `sexual-catalog-divine-core`'s three `DIVINE_ACTS` entries are
  byte-for-byte unchanged.
