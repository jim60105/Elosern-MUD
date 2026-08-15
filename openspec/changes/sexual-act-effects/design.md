## Context

`sexual-act-registry` ships `SexualActDef`/`SEXUAL_ACT_REGISTRY`/`_act_family()` with every act's
`effects` list empty, because the two prefixes this proposal defines do not exist yet. It also ships
`SkillHandler.owned_keys()` extended to include unlocked acts, and `SexualState.unlocked_act_keys()`.
`sexual-body-parts` (archived) shipped `BODY_PARTS`/`GENERIC_BODY_PART` as pure vocabulary constants.
`pleasure-gauge` (archived) shipped `PLEASURE_CONFIG` with validated `sensitivity_multipliers` and
`shame_multipliers` tables. `climax-settlement` (archived) shipped `climax_settlement_action()`,
`stage_climax_extension()`, and the `climax_turns`/`pending_climax_extension` bookkeeping — all
correct, all currently uncalled, because nothing yet produces a pleasure gain large enough to trigger
an extension.

This proposal is the module that finally calls the shipped-but-unused surfaces: it is where an act's
metadata becomes an actual state mutation.

`world/rules/sexual_act_effects.py` imports `PLEASURE_CONFIG` and `_apply_climax_phase_set` from
`world.rules.sexual_state` at ordinary top level (not deferred) — `sexual_state.py` never imports this
new module, so there is no cycle to guard against here, unlike the `Monster` import in D-4.
`_apply_climax_phase_set`'s leading underscore marks it as internal to hand-authored callers within
`world/rules/`, not as private to `sexual_state.py` alone: it is listed in that module's own `__all__`
and `decay_tick()` already calls it from the same module as a sanctioned cross-function call, which
this proposal's cross-module call continues.

## Goals / Non-Goals

**Goals:**
- Give every future catalog act exactly two new effect strings that, together, apply pleasure to
  every participant and increment every counter the act declares — with zero catalog-authored Python.
- Wire `stage_climax_extension()` to a real trigger for the first time, and make the full
  未達→接近→進行中 climax-phase progression and `wetness_follows_arousal`'s wetness gain reachable
  through the ordinary catalog-act path, not only through `divine_sexual_arts`'s pre-existing
  `sexual_event:stimulus_applied` cast.
- Make `SexualActDef.sexual_events` — validated by `sexual-act-registry` but never consumed by
  anything until this proposal — actually emit, for the subset of `sexual.yaml`'s events that do not
  target pleasure, wetness, or climax phase (the "narrative" events: sensitivity-frequency,
  experience-type recording, virginity, and shame-from-being-watched/shame-from-public-activity).
- Keep the generic gain formula (base × sensitivity × shame × participant-count) the single path
  every ordinary catalog act uses, so 62 acts across five lines share one formula implementation.

**Non-Goals:**
- No act content (catalog proposals).
- No resist contest — this proposal's handlers assume the act's cast already succeeded; whether it
  should have been resistible is `sexual-resist-contest`'s and `sexual-resist-turn-cost`'s territory.
- No divine-line effects. 絕頂律令 (set-to-100, bypassing every multiplier), 時姦 (bulk extension
  staging in one action), and 神域搾取 (pleasure-to-resource conversion) are bespoke and explicitly
  exempt from the D-4 self-pleasure invariant; they need their own effect prefixes, added by
  `divine-sexual-arts-reuse`. This proposal's `pleasure:`/`sexual_counter:` prefixes are the
  *ordinary* path only.
- No change to `PLEASURE_CONFIG`, `sexual_pleasure.yaml`, `sexual.yaml`, or any field/rule of
  `SexualState`/`sexual_transitions.py`. Every read against those is read-only, and the one existing
  effect prefix this proposal reuses (`sexual_event:`) is consumed exactly as `divine_sexual_arts`
  already consumes it, with no change to `_handle_sexual_event` or `apply_event()`.
- **Explicitly deferred, not silently missing**: no act in this proposal's scope can raise `exposure`
  or `shame` directly, or apply `direct_stimulus_applied`'s stimulus-specific wetness bonus.
  `sexual.yaml`'s only exposure-raising rule (`exposure_up_on_clothing_damaged`) is conditioned on
  `clothing_damaged_in_combat`, which is semantically wrong for a voluntary 羞恥線 act — that line's
  content proposal must add its own `sexual.yaml` row and event (e.g. `voluntary_exposure`), which is
  a `sexual.yaml` edit squarely out of this proposal's file ownership. See D-8 for exactly which
  events this proposal's acts *may* declare today, and why the exposure/shame-direct case is excluded
  from that list rather than solved here.

## Decisions

### D-1: Effect strings carry only the act's own key; every other parameter is read from the registry

`pleasure:<act_key>` and `sexual_counter:<act_key>` are the only two **new** prefixes this proposal
defines (D-8 adds a third string an act may carry, but it reuses the existing, unmodified
`sexual_event:` prefix). `PleasureEffect` and
`SexualCounterEffect` each carry one field, `act_key: str`, parsed with the existing
`_parse_single_arg` helper `effects.py` already uses for `passive_buff:<rule_key>` and
`divine_mystery:<name>`.

This was not the shape sketched in the original resolution design: a magnitude-bearing
`pleasure:<magnitude>` was considered and rejected, because `SexualActDef.base_pleasure` (already
shipped by `sexual-act-registry`) would then be a second, divergent source of the same number. Naming
the act's own key instead is the only way a handler — whose signature is fixed at
`(actor, targets, effect_id, context, scale)` with no `skill` or `skill.key` parameter — can find its
way back to `SEXUAL_ACT_REGISTRY[act_key]`, and it keeps every other value single-sourced from the
registry `sexual-act-registry` already validates.

### D-2: `participants()` reuses `_step3_targeting`'s existing SELF convention

```python
def participants(actor: Any, targets: list[Any]) -> list[Any]:
    return list(dict.fromkeys([actor, *targets]))
```

`ActionResolver._step3_targeting` already sets `candidates = [request.actor]` when a `SELF`-target
skill is cast with no explicit targets, so a solo act's `targets` argument arriving at the handler is
already `[actor]` — `participants()` just needs to de-duplicate, not special-case SELF. For a
`SINGLE`/`AREA` act aimed at others, `targets` does not include the actor, so `participants()`
prepends it. `dict.fromkeys` preserves actor-first order deterministically without importing a set
(sets do not preserve insertion order in a way this codebase relies on elsewhere).

### D-3: The gain formula, and where the participant-count table lives

```python
def compute_pleasure_gain(
    participant: Any, part: str, base_pleasure: int, ratio: float, participant_count: int,
) -> int:
    sensitivity = PLEASURE_CONFIG.sensitivity_multipliers[participant.sexual.sensitivity[part].level]
    shame = PLEASURE_CONFIG.shame_multipliers[participant.sexual.shame.level]
    crowd = _EFFECTS_CONFIG.participant_multiplier(participant_count)
    return round(base_pleasure * ratio * sensitivity * shame * crowd)
```

`ratio` is `1.0` for every recipient and `act.actor_pleasure_ratio` for the actor's own entry — the
D-4/D-9 self-pleasure split lives entirely in how the handler calls this function, not in the
function itself, so the formula has no special case for "am I the actor."

The participant-count multiplier is **not** added to `sexual_pleasure.yaml`/`PLEASURE_CONFIG`
(`pleasure-gauge`'s territory, already archived). It lives in a new, small, independently-validated
file, `world/rules/rulebook/sexual_act_effects.yaml`:

```yaml
participant_multipliers:
  "1": 1.0
  "2": 1.1
  "3+": 1.2
climax_extension_threshold: 20
```

loaded by this proposal's own `load_effects_config()` in `sexual_act_effects.py`, validated at import
(ascending values, `1`/`2`/`3+` keys present and no others, `climax_extension_threshold` a positive
integer) — following the same fail-closed-at-load discipline `pleasure-gauge` established for
`sexual_pleasure.yaml`, without editing that file or its loader. Keeping this table separate means
this proposal's entire diff against already-shipped modules is additive (two new dispatch branches,
two new handlers, one new line in `_act_family()`) — nothing in `sexual_state.py` changes, so a later
proposal that also touches that module (`divine-sexual-arts-mutators`) never has to reconcile with
this one.

### D-4: `resolve_part()` collapses both `Monster` entities and `None` to the generic channel

```python
def resolve_part(entity: Any, declared_part: str | None) -> str:
    if declared_part is None:
        return GENERIC_BODY_PART
    from typeclasses.monsters import Monster
    return GENERIC_BODY_PART if isinstance(entity, Monster) else declared_part
```

The `Monster` import is deferred inside the function body, matching `SexualState.__init__`'s existing
`from typeclasses.monsters import Monster` deferral (both exist to avoid a `typeclasses` ↔
`world.rules` import cycle; `world/rules/sexual_act_effects.py` is new but inherits the same
constraint every other `world/rules/` module touching `Monster` already works under).

`declared_part is None` collapsing to `GENERIC_BODY_PART` (rather than raising) is what lets an
異種 act's `target_part=None` (enforced by `sexual-act-registry`'s own structural invariant) resolve
cleanly against a `Monster` target without a special case in the handler: whether the `None` came
from "this line never declares a target part" or would-be `Monster`-collapse, the answer is the same
constant either way.

### D-5: The pleasure handler resolves parts per role, applies gain, replicates the two arousal-coupled cascade rules directly, then stages the extension trigger

**Which part and which ratio, per participant** (this subsection resolves a gap an earlier draft of
this document left implicit): for the acting entity, `part = resolve_part(actor, act.actor_part)` and
`ratio = act.actor_pleasure_ratio`; for every other participant, `part = resolve_part(participant,
act.target_part)` and `ratio = 1.0`. `participant_count = len(participants(actor, targets))`,
computed once per cast and reused for every participant's `compute_pleasure_gain()` call — it does
not vary per participant.

```python
def _handle_pleasure_effect(actor, targets, effect_id, context, scale):
    del context, scale
    act = _resolve_act(effect_id)
    everyone = participants(actor, targets)
    count = len(everyone)
    pending = []
    for participant in everyone:
        is_actor = participant is actor
        part = resolve_part(participant, act.actor_part if is_actor else act.target_part)
        ratio = act.actor_pleasure_ratio if is_actor else 1.0
        gain = compute_pleasure_gain(participant, part, act.base_pleasure, ratio, count)
        pending.append(_pleasure_pending_effect(participant, gain))
    return pending


def _apply_pleasure_gain(entity: Any, gain: int) -> None:
    pre_arousal_ordinal = entity.sexual.arousal.value
    was_at_critical_point = entity.sexual.climax_phase.level == "接近"

    entity.sexual.pleasure.base += gain

    if entity.sexual.arousal.value > pre_arousal_ordinal:
        entity.sexual.wetness.value += 1
    if entity.sexual.arousal.level == "極限":
        _apply_climax_phase_set(entity, "接近")
    if was_at_critical_point:
        _apply_climax_phase_set(entity, "進行中")

    if entity.sexual.climax_phase.level == "進行中" and gain >= _EFFECTS_CONFIG.climax_extension_threshold:
        entity.sexual.stage_climax_extension()
```

`entity.sexual.pleasure` is a `counter`-type trait with `max=100` (`pleasure-gauge`), so
`.base += gain` self-clamps — a participant already at 97 receiving a computed gain of 30 ends at
100, not 127. The extension check compares against `gain`, the **uncapped** computed value, not the
clamped result, matching the pleasure model design's explicit requirement: an entity already in
`進行中` sits at 85-100, so the *applied* delta is frequently near zero after clamping, and gating on
the applied delta would make extension fire almost never.

**Why climax-phase and wetness are replicated here instead of routed through `apply_event()`.** The
rubber-duck review that preceded this revision correctly identified that mutating `pleasure` outside
`apply_event()` makes `sexual.yaml`'s `field_changed`-conditioned rules unable to observe the change:
`apply_event()` takes an immutable snapshot of `entity.sexual` at the **start of its own call**, and
`field_changed` conditions detect only deltas produced by rules firing *within that same call*. If
`_apply_pleasure_gain` mutated `pleasure` and then separately called `apply_event(entity,
"stimulus_applied")`, that call's own snapshot would already reflect the *new* pleasure value, so
`wetness_follows_arousal` (`{field_changed: arousal, direction: up}`) would never fire, and routing
through the flat-delta `arousal_up_on_stimulus` rule at all would double-count the gain this
proposal's own scaled formula already computed.

The fix is not to route through `apply_event()` for these two rules at all, but to replicate their
exact, already-shipped semantics as plain Python, calling the **same sanctioned, already-public**
functions the rule engine itself would call:

- `wetness_follows_arousal`'s effect (`{field: wetness, delta: "+1"}` on an arousal-ordinal increase)
  becomes a direct `entity.sexual.wetness.value += 1`, guarded by comparing the arousal ordinal before
  and after the gain is applied. `OrderedLevelTrait.value`'s own setter clamps to
  `[self.min, self.max]`, so no separate bounds check is needed.
- `climax_gate` (未達→接近 when `arousal` reaches `極限`) and
  `climax_phase_critical_point_to_in_progress` (接近→進行中 on a further stimulus while already at
  接近) both become direct calls to `_apply_climax_phase_set(entity, target_level)` — the **sole
  sanctioned write path** for `climax_phase`, already exported in `sexual_state.py`'s `__all__` and
  already called directly by `decay_tick()` without going through `apply_event()`. Calling it directly
  here is not a new precedent; `decay_tick()` already established that this function is meant to be
  called from outside the rule engine.

The two-step 未達→接近→進行中 semantic (an entity must be stimulated once to reach 接近, then
stimulated *again* while still at 接近 to reach 進行中 — never both in one gain application) is
preserved by capturing `was_at_critical_point` **before** mutating `pleasure`: if this call's own gain
is what pushes arousal to `極限` for the first time, `was_at_critical_point` is `False` (the entity
was at `未達` a moment ago), so only the `接近` call fires — the `進行中` call is skipped on this same
invocation because it was captured before either transition ran. If the entity was already at `接近`
from a *prior* act, `was_at_critical_point` is `True`, `_apply_climax_phase_set(entity, "接近")`
no-ops (the valid edges from `接近` are `{進行中, 未達}`; `接近→接近` is not a listed edge), and the
`進行中` call succeeds. Both `_apply_climax_phase_set` calls are unconditionally safe to attempt
because the function itself no-ops on any edge outside `_VALID_CLIMAX_TRANSITIONS` — this handler adds
no additional guard beyond capturing `was_at_critical_point` at the right time.

This is a deliberate, narrow duplication of two rules' logic, not a general pattern: it exists only
for the two `sexual.yaml` rules whose conditions (`field_changed`, or a field-equals check this
proposal's own gain path can trigger) cannot observe a change made outside `apply_event()`. Every
other rule this proposal's acts need is reachable by actually emitting the underlying event through
the existing `sexual_event:` prefix (D-8) — no other rule needs replicating.

This is the one place this proposal's logic depends on evaluation order within a single
`PendingEffect.apply()` call: `pre_arousal_ordinal` and `was_at_critical_point` must be read **before**
`pleasure.base` is mutated, never derived from post-mutation state.

### D-8: `sexual_events` reuses the existing `sexual_event:` prefix verbatim, restricted to a forbidden list

`_act_family()` appends one `f"sexual_event:{name}"` string per entry in a row's `sexual_events` tuple
to the `SkillDef.effects` list it builds — alongside, not instead of, `pleasure:<key>` and
`sexual_counter:<key>`. This reuses `world/rules/action.py`'s existing `_handle_sexual_event` and
`world/skills/effects.py`'s existing `SexualEventEffect`/`sexual_event:` dispatch branch completely
unchanged; this proposal adds no new code for it.

An act's `sexual_events` tuple SHALL NOT contain any of:

```python
_FORBIDDEN_SEXUAL_EVENTS = frozenset({
    "stimulus_applied", "sustained_stimulus_applied", "extreme_stimulus_applied",
    "climax_ends", "climax_extended",
})
```

The first three target `pleasure` directly (`arousal_up_on_stimulus`,
`arousal_up_on_sustained_stimulus`, `arousal_extreme_stimulus_to_max`) and would double-count against
this proposal's own scaled `pleasure:` gain if emitted by the same act. The last two are exclusively
owned by the climax-settlement mechanism (`combat.py`/`clock.py`'s upkeep calls) and must never be
emitted by an individual act's cast. Every other currently-declared `sexual.yaml` event —
`frequent_stimulation` (sensitivity), `direct_stimulus_applied` (an *additional*, stimulus-specific
wetness bonus layered on top of, not instead of, the D-5 arousal-following wetness gain — legitimately
additive, not forbidden), `masturbation_climax`, `first_vaginal_penetration`,
`penetrative_sex_with_female`, `penetrative_sex_with_male`, `breast_sex_performed`,
`watched_during_activity`, `public_exposure`, `public_sexual_activity`, `sexual_activity_with_nonhuman`
— is declarable by a catalog act today, and resolves through the ordinary, unmodified `apply_event()`
cascade exactly as `divine_sexual_arts` already exercises for `stimulus_applied`.

A structural test (extending `sexual-act-registry`'s existing test module) asserts no act's
`sexual_events` intersects `_FORBIDDEN_SEXUAL_EVENTS`.

### D-6: The counter mutator table is explicit, not derived

`SexualState`'s eleven `record_*()` method names do not follow one mechanical transform of their
counter attribute names (`masturbation_count` → `record_masturbation` drops `_count`;
`climax_count` → `record_climax_count` keeps it, and is deliberately distinct from the pre-existing,
unrelated `record_climax()` for the daily `climax_today` counter). `sexual_act_effects.py` therefore
declares an explicit table:

```python
_COUNTER_MUTATORS: dict[str, str] = {
    "masturbation_count": "record_masturbation",
    "toy_use_count": "record_toy_use",
    "exposure_act_count": "record_exposure_act",
    "watched_count": "record_watched",
    "duo_act_count": "record_duo_act",
    "group_act_count": "record_group_act",
    "hostile_act_count": "record_hostile_act",
    "restraint_count": "record_restraint",
    "interspecies_act_count": "record_interspecies_act",
    "climax_count": "record_climax_count",
    "climax_extension_count": "record_climax_extension",
}
```

A structural test asserts this table's keys equal `sexual-act-registry`'s documented eleven counter
names exactly, and that every value names a real, callable `SexualState` method — so a future rename
of either side fails this test loudly rather than silently mis-wiring a counter.

### D-7: Counter application: `actor_counters` on the actor, `participant_counters` on every other participant

```python
def _handle_sexual_counter_effect(actor, targets, effect_id, context, scale):
    del context, scale
    act = _resolve_act(effect_id)
    all_participants = participants(actor, targets)
    others = [p for p in all_participants if p is not actor]
    pending = []
    for name in act.actor_counters:
        pending.append(_counter_pending_effect(actor, name))
    for other in others:
        for name in act.participant_counters:
            pending.append(_counter_pending_effect(other, name))
    return pending
```

A counter name present in **both** tuples (e.g. `duo_act_count` on a symmetric two-person act) is
applied once to the actor via the first loop and once to each other participant via the second — this
is how a duo act credits both sides without the schema needing an "applies to everyone including
actor" third category.

## Risks / Trade-offs

- **[Risk]** `resolve_part()`'s `None`-collapses-to-generic behaviour means a coding mistake that
  omits `target_part` on a non-異種, non-神之秘法 act (which `sexual-act-registry`'s invariants do
  *not* forbid — they only forbid a **non**-`None` target part for those two lines, not require one
  elsewhere) would silently train `GENERIC_BODY_PART` instead of failing loudly. → **Mitigation**:
  this proposal adds one more structural check to `sexual-act-registry`'s existing test module: every
  act whose line is *not* `異種`/`神之秘法` and whose `target_spec` is not `SELF`/`NONE` must declare
  a non-`None` `target_part`.
- **[Risk]** The participant-count table's `"3+"` bucket applies the same multiplier to a 3-person and
  a 30-person act, which may under- or over-reward very large groups once a group act with many
  participants ships. → **Mitigation**: the table is data or in the pleasure formula could add a
  `"5+"`/`"10+"` tier later; this proposal ships the three-tier table because no catalog act with more
  than three participants exists yet to calibrate against (`sexual-act-catalog`'s 群體服務 is the
  first, and is out of this proposal's scope).
- **[Risk]** `entity.sexual.pleasure.base += gain` and the extension check happen inside one
  `PendingEffect.apply()` closure per participant; if two acts somehow stage two pleasure effects for
  the same entity within one commit batch, order depends on `PendingEffect` list order, which is
  handler-registration order today (there is only one `pleasure:` handler per cast, so this cannot
  currently happen within a single act — flagged for awareness only, not a live risk in this
  proposal's scope).
- **[Risk]** D-5's direct replication of `wetness_follows_arousal` and the two `climax_gate`/
  `climax_phase_critical_point_to_in_progress` transitions is a second implementation of logic
  `sexual.yaml` also declares, so the two could drift if `sexual.yaml`'s versions are ever rebalanced
  (e.g. the wetness delta changed from `+1` to something else) without updating D-5's Python copy. →
  **Mitigation**: the two paths never fire for the same cast (an act either carries `pleasure:` and
  triggers D-5's direct replication, or is `divine_sexual_arts`'s pre-existing
  `sexual_event:stimulus_applied` path and triggers the rule engine's version — never both), so drift
  produces an inconsistency between the two paths' *magnitude*, not a double-application bug. A
  comment at both sites (D-5's implementation and the `wetness_follows_arousal` rule in `sexual.yaml`)
  cross-referencing the other is recommended at implementation time, though `sexual.yaml` itself is
  outside this proposal's file ownership and cannot be edited to add that comment by this proposal.
- **[Risk]** Exposure- and shame-raising acts (核心 to the 羞恥線 catalog line) cannot be expressed
  through this proposal's mechanisms at all — see the Non-Goals section's explicit disclosure. →
  **Mitigation**: this is disclosed, not silent; the 羞恥線 catalog proposal must add its own
  `sexual.yaml` row(s) and event(s) when it lands, which is normal for a proposal that both owns new
  content and needs a small rulebook addition to express it.

## Migration Plan

Additive only. No existing effect prefix, handler, or `SexualState`/`PLEASURE_CONFIG` field changes.
`_act_family()`'s new `effects` value only takes effect for acts a later catalog proposal adds — with
zero acts registered today, this proposal changes no runtime behaviour for any existing entity.

## Open Questions

None outstanding.
