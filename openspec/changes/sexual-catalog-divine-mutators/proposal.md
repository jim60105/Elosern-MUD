## Why

`sexual-catalog-divine-core` (`C7a`) is a separate, already-committed proposal for the three 神之秘法
acts the design doc (`docs/superpowers/specs/2026-08-15-divine-sexual-arts-design.md`) describes as
reusing existing mechanisms. Like every catalog proposal in this batch, `C7a`'s artifacts are committed
ahead of its implementation; its `tasks.md` is unchecked, and `DIVINE_ACTS` is still `()` in the current
tree. This proposal is written to apply **after** `C7a`'s implementation lands — it extends the same
`DIVINE_ACTS` tuple `C7a`'s own tasks.md fills to three entries, and its own tasks.md §1.1 confirms that
precondition rather than assuming it. It fills the remaining four acts, `C7b`: 感度創世, 恥辱剝奪,
絕對從屬, and 無垢回歸,
described there as each needing "one new, explicitly named mutator on `SexualState`. None weakens an
existing guard; each adds a separate, auditable door that no ordinary rule path can reach."

That framing holds at the `SexualState` layer, and this proposal adds exactly the four named mutators
(`saturate_sensitivity`, `clamp_shame_to`, `mark_submission`, `restore_purity`) with no surprises there.
It does not fully hold one layer up, the same layer `C7a` found gaps in: three of these four acts still
need a new `action.py` effect prefix (the same "hand-build outside `_act_family()`" pattern `C7a`
established, reused here rather than re-derived), and 絕對從屬 specifically needs a real change to
`world/rules/sexual_resist.py` — a file the design doc's stated Scope does not list, but which its own
described behaviour ("the resist contest consults it at the same point it consults the affinity
`auto_comply` flag") cannot be built without touching. `resist_verdict()` is a documented no-create, pure
function (`sexual-resist-contest`'s own shipped contract): consulting a new `submission_marks` set
without materializing `entity.sexual` — the same discipline `resist_verdict()`'s existing
`_climax_turn_short_circuit` helper already follows for `climax_turns` — is exactly what this proposal's
`sexual_resist.py` change does, and no more.

## What Changes

- **Add four mutators to `SexualState`** (`world/rules/sexual_state.py`), each the sole write path for
  its own new or newly-repurposed state, matching the design doc's naming exactly:
  - `saturate_sensitivity()`: sets every `BODY_PARTS` member's sensitivity to `SENSITIVITY_LEVELS[-1]`
    (`敏感異常`) for an ordinary entity, or `GENERIC_BODY_PART` alone for a `Monster` (mirroring
    `resolve_part`'s existing Monster collapse — a `Monster` only ever reads its one generic channel, so
    seeding named parts it can never resolve to would be dead state).
  - `clamp_shame_to(level)`: pins `shame`'s `min`/`max`/`value` all to the ordinal of `level` at once,
    using the exact `OrderedLevelTrait` bound-setter mechanism `SexualState.__init__` already uses to
    pin a `Monster`'s `shame` at the floor (`shame.min = shame.max = 0`) — this mutator pins it at the
    ceiling instead. Raises `ValueError` if the entity is a `Monster`: a `Monster`'s `shame` bounds are
    already pinned at the floor by construction (`sexual-state-handler`'s own shipped requirement), and
    re-pinning at the ceiling would contradict that shipped baseline rather than compose with it.
  - `mark_submission(caster_key)`: adds `caster_key` to a new, append-only `submission_marks` frozenset
    stored in the existing `sexual_state` attribute category, alongside `virgin` and `experience_types`
    — same category, same append-only discipline as `add_experience_type`, one new mutator.
  - `restore_purity()`: sets `virgin` back to `True` by writing the underlying attribute directly
    (`entity.attributes.add("virgin", True, category=...)`, bypassing the public `virgin` setter, which
    is unconditionally a no-op once `False` — see design.md D-4 for why a second, separately-named write
    path does not weaken the shipped one-way-setter guarantee). Does not touch `experience_types`. A
    no-op, not an error, when the entity is already virgin.
- **Add four acts to `world/skills/sexual_acts/divine.py`'s `DIVINE_ACTS` tuple**, extending the same
  tuple `C7a` started filling. Every one hand-built (not via `_act_family()`, for the same reasons `C7a`
  established: none needs the ordinary pleasure/counter/event triad, and `SexualDrainEffect`-style bespoke
  effects are the established pattern), `requires_divine_arts=True`, `unlock={}`, `target_part=None`,
  `resistible=True`, `actor_counters=()`, `participant_counters=()`:
  - **感度創世** (`TargetSpec.SINGLE`): one new effect, `divine_saturate_sensitivity:感度創世`, whose
    handler calls `target.sexual.saturate_sensitivity()` for the (post-resist) resolved target.
  - **恥辱剝奪** (`TargetSpec.SINGLE`): one new effect, `divine_clamp_shame:恥辱剝奪`, whose handler
    checks `isinstance(target, Monster)` eagerly (before staging anything) and raises
    `RejectedAction(RejectReason.EFFECT_RESOLUTION_FAILED, ...)` directly if so; otherwise stages
    `target.sexual.clamp_shame_to("成癮")` (matching the design doc's error table — see design.md D-3
    for why the check is eager rather than caught from inside a staged `PendingEffect`, which would
    surface as the wrong reject reason, `CommitFailed`, instead).
  - **絕對從屬** (`TargetSpec.SINGLE`): one new effect, `divine_mark_submission:絕對從屬`, whose handler
    calls `target.sexual.mark_submission(str(actor.id))` for the resolved target — `str(actor.id)`, not
    `_entity_key(actor)`/`.key`, because `.key` is confirmed non-unique across same-species `Monster`
    spawns (`world/maps/wilderness_population.py`) and this mark is permanent with no removal path; see
    design.md D-5.
  - **無垢回歸** (`TargetSpec.SINGLE`): one new effect, `divine_restore_purity:無垢回歸`, whose handler
    calls `target.sexual.restore_purity()` for the resolved target.
  - Every handler filters the actor out of the entities it acts on and tolerates an empty `targets` list
    (a fully-resisted `TargetSpec.SINGLE` cast) as a no-op, matching `C7a`'s established discipline for
    exactly the same reason: `_step4b_sexual_resist_gate` runs before these handlers and can legitimately
    empty `targets`.
- **Wires `submission_marks` into the resist contest** (`world/rules/sexual_resist.py`): adds a new
  no-create helper, `_submission_term(actor, resister) -> bool`, reading
  `resister.attributes.get("submission_marks", default=frozenset(), category="sexual_state")` directly
  (never materializing `entity.sexual`, exactly like the existing `_climax_turn_short_circuit`'s
  `climax_turns` read) and checking whether `str(actor.id)` is a member. `resist_verdict()`'s
  short-circuit condition becomes `affinity_auto_comply or
  submission_marked or _climax_turn_short_circuit(resister)`, one additional `or` term alongside the two
  that already exist.
- **Registers four new effect prefixes in `action.py`'s `_EFFECT_HANDLERS` table**:
  `divine_saturate_sensitivity:`, `divine_clamp_shame:`, `divine_mark_submission:`, and
  `divine_restore_purity:`, plus their typed `effects.py` dataclasses. Each is a general dispatch-table
  entry, following `C7a`'s established convention — no handler reads `requires_divine_arts` or branches
  on the caller's line.
- **Amends the design doc's stated Scope** (`divine.py`, `sexual_state.py`, `sexual.yaml`) to add
  `world/rules/action.py`, `world/skills/effects.py` (both already amended by `C7a`), and
  `world/rules/sexual_resist.py` (new to this proposal, for 絕對從屬). The design doc itself authorizes
  this: "the design document wins unless a change amends it explicitly" (§3, 無垢回歸).

## Capabilities

### New Capabilities
- `sexual-catalog-divine-mutators`: the four `C7b` 神之秘法 acts, their four new `SexualState`
  mutators, and the `submission_marks` resist short-circuit.

### Modified Capabilities
- `sexual-resist-contest`: `resist_verdict()`'s short-circuit condition gains a third term
  (`submission_marks` membership) alongside the existing affinity `auto_comply` and climax-turn terms.
- `sexual-state-handler`: gains four new mutators on `SexualState` (`saturate_sensitivity`,
  `clamp_shame_to`, `mark_submission`, `restore_purity`); the shipped `virgin` one-way-public-setter
  requirement is exercised, not weakened — see design.md D-4 for the explicit non-regression argument.

## Impact

- Code: `world/rules/sexual_state.py` (four new mutators, one new `submission_marks` attribute);
  `world/rules/sexual_resist.py` (`_submission_term` helper, one new short-circuit term in
  `resist_verdict()`); `world/skills/sexual_acts/divine.py` (extends `DIVINE_ACTS` from `C7a`'s three
  entries to seven — requires `C7a`'s implementation to have landed first, per tasks.md §1.1);
  `world/skills/effects.py` (four new frozen dataclasses); `world/rules/action.py` (four new handler
  functions plus their `_EFFECT_HANDLERS` registrations); a new test module,
  `world/skills/sexual_acts/tests/test_divine_mutators_catalog.py`.
- No change to `world/rules/rulebook/sexual.yaml` — none of the four acts emits a `sexual_event`.
- No change to `world/skills/sexual_acts/_builder.py`, `world/lore/races.py`, or
  `world/skills/registry.py` — the `_PARLESS_LINES`/forbidden-events rules, the race gate, and the
  line's three already-shipped skills are exercised, not changed.
- No change to `sexual-catalog-divine-core`'s three acts or their effect prefixes — this proposal only
  extends `DIVINE_ACTS`, never edits an existing entry.
- Completes the 神之秘法 line: after this proposal, all seven acts the source design doc specifies are
  shipped, with no further deferrals on this line.
