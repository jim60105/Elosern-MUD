## 1. Confirm the dependency surface this change reads

- [ ] 1.1 Confirm `world/skills/sexual_acts/divine.py` still ships `DIVINE_ACTS = ()`, pre-declared and
  empty.
- [ ] 1.2 Confirm `_step1_divine_arts_gate` (`world/rules/action.py`) and `RaceProfile.
  can_use_divine_arts` (`world/lore/races.py`, currently `True` only for `elf`) are unchanged.
- [ ] 1.3 Confirm `divine_sexual_mastery` and `reincarnation_boon_yuna` (`world/skills/registry.py`)
  still carry `SexualMasteryEffect` and are unaffected by this change (this line's blanket-unlock
  exclusion is enforced by `unlocked_act_keys_for`'s counter-driven logic and by these three acts
  declaring `unlock={}`, not by any special-casing this change adds).
- [ ] 1.4 Confirm `world/skills/sexual_acts/__init__.py`'s `_register_rows()` still accepts any
  `(SkillDef, SexualActDef)` pair regardless of construction path (no `_act_family()`-provenance
  check).
- [ ] 1.5 Confirm `_apply_pleasure_gain` (`world/rules/action.py`) and `SexualState.
  stage_climax_extension` (`world/rules/sexual_state.py`) are unchanged from the versions traced in
  design.md D-2/D-3.
- [ ] 1.6 Confirm `test_registry_structure.py`'s `check_external_acts_declare_a_target_part` still
  exempts `skill.group in ("異種", "神之秘法")` by name.
- [ ] 1.7 Confirm `world/rules/action.py::_step4b_sexual_resist_gate` (shipped by the already-merged
  `sexual-resist-cast-wiring` change) is unchanged: it rolls `resist_verdict()` per non-actor target of
  any `resistible=True` sexual act, drops resisted targets before `_step5_effect_resolution`, and keeps
  (does not drop) an actor present in `targets` — the exact behaviour design.md D-1/D-6 depend on.
- [ ] 1.8 Confirm `world/rules/targeting.py::expand_target_shorthand`'s `"all"` branch still has no
  self-exclusion (unlike `"all-enemies"`/`"all-allies"`), the fact design.md D-1 cites for why 絕頂律令's
  handler must filter the actor explicitly.

## 2. `world/skills/effects.py`: three new typed effect dataclasses

- [ ] 2.1 Add `DivinePleasureMaxEffect` (frozen dataclass, no fields — the target set comes from the
  cast's resolved targets, not the effect string).
- [ ] 2.2 Add `ClimaxExtensionStageEffect(count: int)`.
- [ ] 2.3 Add `SexualDrainEffect` (frozen dataclass, no fields).
- [ ] 2.4 Register all three in `parse_effect`'s dispatch table, parsing `count` from the
  `divine_climax_extension_stage:<count>` suffix as `int`.

## 3. `world/rules/action.py`: three new effect handlers

- [ ] 3.1 Add `_handle_divine_pleasure_max(actor, targets, effect_id, context, scale)`: for each entity
  in `targets` **explicitly excluding any entity that is `actor`** (`if entity is actor: continue` —
  do not rely on `targets` already excluding the actor; see design.md D-1), call
  `_apply_pleasure_gain(entity, 100)` then `_apply_pleasure_gain(entity, 0)`, in that order, staged as
  `PendingEffect`s. An empty or partial `targets` list (from resisted targets already dropped) is an
  ordinary outcome — no rejection.
- [ ] 3.2 Add `_handle_climax_extension_stage(actor, targets, effect_id, context, scale)`: parse `count`
  from `effect_id`, then for each entity in `targets` excluding `actor` (same explicit filter as 3.1),
  call `entity.sexual.stage_climax_extension(count)`, staged as `PendingEffect`s. Empty/partial
  `targets` is an ordinary outcome.
- [ ] 3.3 Add `_handle_sexual_drain(actor, targets, effect_id, context, scale)`: if `targets` is empty
  (a successfully-resisted sole target — `TargetSpec.SINGLE`'s "exactly one" guarantee is checked at
  targeting time, before the resist gate runs), return `[]` — an ordinary no-op, not a rejection.
  Otherwise, for the single entity in `targets`, stage one `PendingEffect` that reads
  `target.sexual.pleasure.value`, adds it to `actor.traits.mp.current`, `actor.traits.sp.current`,
  `actor.traits.hp.current`, then sets `target.sexual.pleasure.base = 0`. Reject (via `RejectedAction`)
  only if `targets` contains more than one entity — that case stays structurally unreachable for
  `TargetSpec.SINGLE` regardless of resist and would indicate a genuine caller error.
- [ ] 3.4 Register `"divine_pleasure_max"`, `"divine_climax_extension_stage"`, and `"divine_drain"` in
  `_EFFECT_HANDLERS`.

## 4. `world/skills/sexual_acts/divine.py`: the three hand-built acts

- [ ] 4.1 Add `絕頂律令` (`key="divine_extreme_climax_command"` or similar; `TargetSpec.AREA`,
  `requires_divine_arts=True`, `unlock={}`, `target_part=None`, `resistible=True`,
  `actor_counters=()`, `participant_counters=()`, `effects=["divine_pleasure_max:<key>"]` — no
  `pleasure:`/`sexual_counter:` entries).
- [ ] 4.2 Add `時姦` (`TargetSpec.SINGLE`, same shared fields,
  `effects=["divine_climax_extension_stage:3"]`).
- [ ] 4.3 Add `神域搾取` (`TargetSpec.SINGLE`, same shared fields, `effects=["divine_drain:<key>"]`).
- [ ] 4.4 Populate each `SexualActDef`'s required-but-unused pleasure fields with clearly-documented
  placeholder values (`base_pleasure=1`, `actor_pleasure_ratio=0.0`, `actor_part=None`) and a one-line
  comment noting no `pleasure:` effect ever reads them.
- [ ] 4.5 Assemble `DIVINE_ACTS` as the tuple of the three hand-built `(SkillDef, SexualActDef)` pairs.

## 5. Update the one existing test this change breaks by design

- [ ] 5.1 In `world/skills/sexual_acts/tests/test_registry_structure.py`, update
  `test_every_line_module_is_importable_with_only_divine_empty`: add `(sexual_acts.divine,
  "DIVINE_ACTS")` to the loop of modules asserted non-empty, and **remove** the trailing
  `self.assertEqual(sexual_acts.divine.DIVINE_ACTS, ())` assertion, since `DIVINE_ACTS` is now
  non-empty too. Rename the test (e.g. `test_every_line_module_is_importable_and_non_empty`) to match
  its new, fully-populated assertion.
- [ ] 5.2 Run `uv run --locked python -m tools.spec_traceability list` and note the canonical
  requirement ID for `sexual-act-registry`'s updated "six line modules ship pre-declared and
  pre-imported" requirement; update the renamed test's `@covers_requirement(...)` tag to that ID.

## 6. Behaviour tests for the delta spec

- [ ] 6.1 Run `uv run --locked python -m tools.spec_traceability list` and note the canonical
  requirement IDs for `sexual-catalog-divine-core::*`.
- [ ] 6.2 Add `world/skills/sexual_acts/tests/test_divine_core_catalog.py` covering: the race gate
  rejecting all three regardless of counters; a divine-capable actor with zero counters owning all
  three; a mastery-only, non-divine-race entity owning the full counter-gated catalogue but none of
  these three (the design doc's "most important test").
- [ ] 6.3 In the same module, cover 絕頂律令: a target starting below `極限`/`未達` reaches
  `pleasure=100`/`climax_phase="進行中"` in one cast; a target already `進行中` stays `進行中` and
  still reaches `pleasure=100`; the actor's own `pleasure` is never touched, including when cast via
  the `"all"` AREA shorthand (which resolves the actor into `targets` and must still be filtered by the
  handler, per task 3.1); `SkillDef.effects` names no `sexual_event:extreme_stimulus_applied` entry; a
  partial resist (one target resists, another doesn't) succeeds with the resisting target unaffected.
- [ ] 6.4 Cover 時姦: casting it stages `pending_climax_extension=3`; a target already `進行中`
  consumes all three across three successive `climax_settlement_action()` calls returning `"extend"`
  each time; a target not `進行中` has the staged count discarded at the next settlement point,
  asserting `pending_climax_extension` reads `0` afterward and no `"extend"` is returned; a resisted
  target has nothing staged and the cast still succeeds (no `RejectedAction`).
- [ ] 6.5 Cover 神域搾取: a mid-range target `pleasure` value drains one-to-one into caster `mp`/`sp`/`hp`
  and zeroes the target's `pleasure`; each resource clamps independently at its own maximum when
  headroom differs across the three; draining a `pleasure=0` target is a no-op; a resisted sole target
  drains nothing and the cast still succeeds, not rejects (asserting `_handle_sexual_drain` returns `[]`
  for an empty `targets` list rather than raising `RejectedAction`).
- [ ] 6.6 Cover the three new `_EFFECT_HANDLERS` entries directly (not only through a full act cast),
  asserting none branches on `requires_divine_arts` or the caller's `SkillDef.group`.
- [ ] 6.7 Apply `covers_requirement("sexual-catalog-divine-core::<id>")` (using the IDs from 6.1) to each
  test function whose assertions establish that requirement.
- [ ] 6.8 Run `uv run --locked python -m tools.spec_traceability check` and confirm every
  `sexual-catalog-divine-core` requirement, and the updated `sexual-act-registry` requirement (task
  5.2), are covered.

## 7. Full verification

- [ ] 7.1 Run `uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests
  world.rules.tests` and confirm the whole package suite passes, including the renamed
  `test_registry_structure.py` test against the now-three-row `DIVINE_ACTS` tuple, and
  `test_sexual_transitions.py` (unaffected — this change adds no rulebook row and calls no rule
  requiring `apply_event`).
- [ ] 7.2 Run `uv run --locked python -m compileall -q world`.
- [ ] 7.3 Run `openspec validate sexual-catalog-divine-core --strict` and resolve any reported issue.
- [ ] 7.4 Confirm no file outside `world/skills/sexual_acts/divine.py`, `world/skills/effects.py`,
  `world/rules/action.py`, and `world/skills/sexual_acts/tests/{test_divine_core_catalog.py,
  test_registry_structure.py}` was touched, matching the proposal's Impact list exactly — in
  particular, confirm `world/skills/sexual_acts/_builder.py`, `world/rules/sexual_state.py`,
  `world/rules/sexual_resist.py`, and `world/rules/rulebook/sexual.yaml` all have zero diff from this
  change.
