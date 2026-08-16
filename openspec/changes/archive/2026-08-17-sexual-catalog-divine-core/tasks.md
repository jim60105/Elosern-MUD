## 1. Confirm the dependency surface this change reads

- [x] 1.1 Confirm `world/skills/sexual_acts/divine.py` still ships `DIVINE_ACTS = ()`, pre-declared and
  empty.
- [x] 1.2 Confirm `_step1_divine_arts_gate` (`world/rules/action.py`) and `RaceProfile.
  can_use_divine_arts` (`world/lore/races.py`, currently `True` only for `elf`) are unchanged.
- [x] 1.3 Confirm `divine_sexual_mastery` and `reincarnation_boon_yuna` (`world/skills/registry.py`)
  still carry `SexualMasteryEffect` and are unaffected by this change. **This change adds** the
  divine line's blanket-unlock exclusion to `unlocked_act_keys_for` (`world/skills/sexual_acts/
  __init__.py`): the shipped mastery branch returns `frozenset(SEXUAL_ACT_REGISTRY)` — the entire
  registry — which would include these three acts once registered. The delta spec's
  "SexualMasteryEffect ownership alone does not unlock any of the three" scenario and design doc
  §1.1 ("The 性魔法主宰 blanket unlock does not reach them") require the mastery branch to exclude
  `requires_divine_arts=True` acts. Verified empirically before planning: a mastery holder owns an
  injected divine act under the shipped code.
- [x] 1.4 Confirm `world/skills/sexual_acts/__init__.py`'s `_register_rows()` still accepts any
  `(SkillDef, SexualActDef)` pair regardless of construction path (no `_act_family()`-provenance
  check).
- [x] 1.5 Confirm `_apply_pleasure_gain` (`world/rules/action.py`) and `SexualState.
  stage_climax_extension` (`world/rules/sexual_state.py`) are unchanged from the versions traced in
  design.md D-2/D-3.
- [x] 1.6 Confirm `test_registry_structure.py`'s `check_external_acts_declare_a_target_part` still
  exempts `skill.group in ("異種", "神之秘法")` by name.
- [x] 1.7 Confirm `world/rules/action.py::_step4b_sexual_resist_gate` (shipped by the already-merged
  `sexual-resist-cast-wiring` change) is unchanged: it rolls `resist_verdict()` per non-actor target of
  any `resistible=True` sexual act, drops resisted targets before `_step5_effect_resolution`, and keeps
  (does not drop) an actor present in `targets` — the exact behaviour design.md D-1/D-6 depend on.
- [x] 1.8 Confirm `world/rules/targeting.py::expand_target_shorthand`'s `"all"` branch still has no
  self-exclusion (unlike `"all-enemies"`/`"all-allies"`), the fact design.md D-1 cites for why 絕頂律令's
  handler must filter the actor explicitly.

## 2. `world/skills/sexual_acts/__init__.py`: the mastery-branch divine exclusion

- [x] 2.1 Amend `unlocked_act_keys_for`'s mastery branch to exclude every act whose paired `SkillDef`
  declares `requires_divine_arts=True`: the mastery result becomes
  `frozenset(key for key, act in SEXUAL_ACT_REGISTRY.items() if not SKILL_REGISTRY[key].
  requires_divine_arts)`. The counter-driven branch is unchanged — `unlock={}` acts stay owned by
  everyone, matching the shipped "empty unlock mapping is always present" scenario and the delta
  spec's "no counter threshold gates it" claim.
- [x] 2.2 Keep the docstring's guard-order warning intact: the `if key in SKILL_REGISTRY` clause in
  the mastery `any()` comprehension must remain immediately after its `for key in owned_keys` clause
  (the `test_pure_query_guard_precedes_the_registry_dereference` source-inspection test pins the
  order of the first occurrences). The new dereference iterates `SEXUAL_ACT_REGISTRY` keys only,
  which are all present in `SKILL_REGISTRY` by the registration agreement invariant.

## 3. `world/skills/effects.py`: three new typed effect dataclasses

- [x] 3.1 Add `DivinePleasureMaxEffect` (frozen dataclass, no fields — the target set comes from the
  cast's resolved targets, not the effect string).
- [x] 3.2 Add `ClimaxExtensionStageEffect(count: int)`.
- [x] 3.3 Add `SexualDrainEffect` (frozen dataclass, no fields).
- [x] 3.4 Register all three in `parse_effect`'s dispatch table. The effect strings carry the act's
  Chinese label as a decorative payload (`divine_pleasure_max:絕頂律令`, `divine_drain:神域搾取` —
  validated as a single non-empty argument, not stored), except `divine_climax_extension_stage:<count>`
  whose suffix parses as `int`.

## 4. `world/rules/action.py`: three new effect handlers

- [x] 4.1 Add `_handle_divine_pleasure_max(actor, targets, effect_id, context, scale)`: for each entity
  in `targets` **explicitly excluding any entity that is `actor`** (`if entity is actor: continue` —
  do not rely on `targets` already excluding the actor; see design.md D-1), stage one
  `PendingEffect` whose `apply()` calls `_apply_pleasure_gain(entity, 100)` then
  `_apply_pleasure_gain(entity, 0)`, in that order, per target. An empty or partial `targets` list
  (from resisted targets already dropped) is an ordinary outcome — no rejection.
- [x] 4.2 Add `_handle_climax_extension_stage(actor, targets, effect_id, context, scale)`: parse `count`
  from `effect_id` (`divine_climax_extension_stage:<count>`), then for each entity in `targets`
  excluding `actor` (same explicit filter as 4.1), stage one `PendingEffect` calling
  `entity.sexual.stage_climax_extension(count)`. Empty/partial `targets` is an ordinary outcome.
- [x] 4.3 Add `_handle_sexual_drain(actor, targets, effect_id, context, scale)`: if `targets` is empty
  (a successfully-resisted sole target — `TargetSpec.SINGLE`'s "exactly one" guarantee is checked at
  targeting time, before the resist gate runs), return `[]` — an ordinary no-op, not a rejection.
  Otherwise, for the single entity in `targets`, read the stored `pleasure` value **without
  materializing the sexual handler** (`_stored_pleasure_value`: constructing `entity.sexual` writes
  `sexual_traits` at effect-planning time, before the commit snapshot, breaking the all-or-nothing
  boundary on a rejected cast — the same no-create discipline `_sensitivity_level`/
  `_stored_sexual_level` follow; an unmaterialized target reads as the 0 floor, a no-op drain), and
  stage **two** `PendingEffect`s (one per mutated entity, so the commit's per-entity
  snapshot/rollback covers both): one on the `actor` adding the amount to `actor.traits.mp.current`,
  `actor.traits.sp.current`, `actor.traits.hp.current` (each trait's own existing bound enforcement
  clamps at its own maximum — no new clamping logic), and one on the `target` setting
  `target.sexual.pleasure.base = 0`. The actor-side effect uses the no-log `divine_drain_actor`
  description kind so the EventLog carries exactly one `divine_drain` entry targeting the drained
  entity (an actor-targeted entry would misnarrate the caster draining themselves). Reject (via
  `RejectedAction`) only if `targets` contains more than one entity — that case stays structurally
  unreachable for `TargetSpec.SINGLE` regardless of resist and would indicate a genuine caller error.
- [x] 4.4 Register `"divine_pleasure_max"` (surfaces `{"sexual"}`), `"divine_climax_extension_stage"`
  (surfaces `{"sexual"}`), and `"divine_drain"` (surfaces `{"traits", "sexual"}`) in
  `_EFFECT_HANDLERS`, each with `requires_event_context=frozenset()`.
- [x] 4.5 Add `_ENTRY_TEMPLATES` kinds for the new handlers' `PendingEffect` descriptions:
  `divine_pleasure_max`, `divine_climax_extension`, `divine_drain` (Traditional Chinese templates),
  and `divine_drain_actor` (empty template, emitted as no `EventEntry` like `combat_kill_xp`/
  `knocked_out_mark`) — `_entries_from_effect` requires every description's first part to name a
  registered template kind.

## 5. `world/skills/sexual_acts/divine.py`: the three hand-built acts

- [x] 5.1 Add `絕頂律令` (`key="divine_extreme_climax_command"` or similar; `TargetSpec.AREA`,
  `requires_divine_arts=True`, `unlock={}`, `target_part=None`, `resistible=True`,
  `actor_counters=()`, `participant_counters=()`, `effects=["divine_pleasure_max:絕頂律令"]` — no
  `pleasure:`/`sexual_counter:` entries).
- [x] 5.2 Add `時姦` (`TargetSpec.SINGLE`, same shared fields,
  `effects=["divine_climax_extension_stage:3"]`).
- [x] 5.3 Add `神域搾取` (`TargetSpec.SINGLE`, same shared fields, `effects=["divine_drain:神域搾取"]`).
- [x] 5.4 Populate each `SexualActDef`'s required-but-unused pleasure fields with clearly-documented
  placeholder values (`base_pleasure=1`, `actor_pleasure_ratio=0.0`, `actor_part=None`) and a one-line
  comment noting no `pleasure:` effect ever reads them.
- [x] 5.5 Assemble `DIVINE_ACTS` as the tuple of the three hand-built `(SkillDef, SexualActDef)` pairs.

## 6. Update the existing tests this change breaks by design

- [x] 6.1 In `world/skills/sexual_acts/tests/test_registry_structure.py`, update
  `test_every_line_module_is_importable_with_only_divine_empty`: add `(sexual_acts.divine,
  "DIVINE_ACTS")` to the loop of modules asserted non-empty, and **remove** the trailing
  `self.assertEqual(sexual_acts.divine.DIVINE_ACTS, ())` assertion, since `DIVINE_ACTS` is now
  non-empty too. Rename the test (e.g. `test_every_line_module_is_importable_and_non_empty`) to match
  its new, fully-populated assertion.
- [x] 6.2 In `world/skills/sexual_acts/tests/test_seed_acts.py`, update
  `test_interspecies_and_divine_gain_no_seed`: its trailing `self.assertEqual(DIVINE_ACTS, ())`
  assertion becomes false once this change fills `DIVINE_ACTS` — assert the tuple now carries the
  three divine acts instead (e.g. `len(DIVINE_ACTS) == 3`).
- [x] 6.3 In `world/rules/tests/test_sexual_unlock.py`, update
  `test_direct_mastery_ownership_unlocks_the_entire_catalogue`: its assertion
  `unlocked_act_keys() == frozenset(SEXUAL_ACT_REGISTRY)` fails once the registered divine acts are
  excluded from the mastery result — assert the mastery result equals the registry minus every
  `requires_divine_arts=True` act (the synthetic patched act stays included, since it declares no
  such requirement).
- [x] 6.4 In `world/skills/tests/test_skill_registry.py`, extend the pinned `SEXUAL_ACT` key set in
  `test_per_category_key_sets_match_the_d4_classification_table` with the three new act keys
  (`divine_extreme_climax_command`, `divine_timed_copulation`, `divine_realm_drain`) — the same
  pinned set the `sexual-catalog-interspecies` change extended for its seven acts.
- [x] 6.5 Run `uv run --locked python -m tools.spec_traceability list` and note the canonical
  requirement ID for `sexual-act-registry`'s updated "six line modules ship pre-declared and
  pre-imported" requirement; update the renamed test's `@covers_requirement(...)` tag to that ID.

## 7. Behaviour tests for the delta spec

- [x] 7.1 Run `uv run --locked python -m tools.spec_traceability list` and note the canonical
  requirement IDs for `sexual-catalog-divine-core::*`.
- [x] 7.2 Add `world/skills/sexual_acts/tests/test_divine_core_catalog.py` covering: the race gate
  rejecting all three regardless of counters; a divine-capable actor with zero counters owning all
  three; a mastery-only, non-divine-race entity owning the full counter-gated catalogue but none of
  these three (the design doc's "most important test" — made passable by task 2.1's exclusion).
- [x] 7.3 In the same module, cover 絕頂律令: a target starting below `極限`/`未達` reaches
  `pleasure=100`/`climax_phase="進行中"` in one cast; a target already `進行中` stays `進行中` and
  still reaches `pleasure=100`; the actor's own `pleasure` is never touched, including when cast via
  the `"all"` AREA shorthand (which resolves the actor into `targets` and must still be filtered by the
  handler, per task 4.1); `SkillDef.effects` names no `sexual_event:extreme_stimulus_applied` entry; a
  partial resist (one target resists, another doesn't) succeeds with the resisting target unaffected.
- [x] 7.4 Cover 時姦: casting it stages `pending_climax_extension=3`; a target already `進行中`
  consumes all three across three successive `climax_settlement_action()` calls returning `"extend"`
  each time; a target not `進行中` has the staged count discarded at the next settlement point,
  asserting `pending_climax_extension` reads `0` afterward and no `"extend"` is returned; a resisted
  target has nothing staged and the cast still succeeds (no `RejectedAction`).
- [x] 7.5 Cover 神域搾取: a mid-range target `pleasure` value drains one-to-one into caster `mp`/`sp`/`hp`
  and zeroes the target's `pleasure`; each resource clamps independently at its own maximum when
  headroom differs across the three; draining a `pleasure=0` target is a no-op; a resisted sole target
  drains nothing and the cast still succeeds, not rejects (asserting `_handle_sexual_drain` returns `[]`
  for an empty `targets` list rather than raising `RejectedAction`).
- [x] 7.6 Cover the three new `_EFFECT_HANDLERS` entries directly (not only through a full act cast),
  asserting none branches on `requires_divine_arts` or the caller's `SkillDef.group`.
- [x] 7.7 Apply `covers_requirement("sexual-catalog-divine-core::<id>")` (using the IDs from 7.1) to each
  test function whose assertions establish that requirement.
- [x] 7.8 Run `uv run --locked python -m tools.spec_traceability check` and confirm every
  `sexual-catalog-divine-core` requirement, and the updated `sexual-act-registry` requirement (task
  6.5), are covered.

## 8. Full verification

- [x] 8.1 Run `uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests
  world.rules.tests` and confirm the whole package suite passes, including the renamed
  `test_registry_structure.py` test against the now-three-row `DIVINE_ACTS` tuple,
  `test_seed_acts.py`'s updated divine assertion, `test_sexual_unlock.py`'s updated mastery
  assertion, and `test_sexual_transitions.py` (unaffected — this change adds no rulebook row and
  calls no rule requiring `apply_event`).
- [x] 8.2 Run `uv run --locked python -m compileall -q world`.
- [x] 8.3 Run `openspec validate sexual-catalog-divine-core --strict` and resolve any reported issue.
- [x] 8.4 Confirm no file outside `world/skills/sexual_acts/divine.py`,
  `world/skills/sexual_acts/__init__.py`, `world/skills/effects.py`, `world/rules/action.py`, and
  `world/skills/sexual_acts/tests/{test_divine_core_catalog.py, test_registry_structure.py,
  test_seed_acts.py}` plus `world/rules/tests/test_sexual_unlock.py` and
  `world/skills/tests/test_skill_registry.py` was touched, matching the
  proposal's Impact list exactly — in particular, confirm `world/skills/sexual_acts/_builder.py`,
  `world/rules/sexual_state.py`, `world/rules/sexual_resist.py`, and `world/rules/rulebook/sexual.yaml`
  all have zero diff from this change.
