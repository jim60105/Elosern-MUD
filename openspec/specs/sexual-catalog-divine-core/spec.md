# sexual-catalog-divine-core Specification

## Purpose

Register the three `C7a` 神之秘法 acts — 絕頂律令, 時姦, 神域搾取 — filling the divine line from its
pre-declared empty tuple. Each act is hand-built (not via `_act_family()`), declares
`requires_divine_arts=True` (so the shipped race gate is the line's containment), an empty `unlock`
mapping, `target_part=None` (神之秘法 is a parless line), `resistible=True`, and no counters. Each
introduces one new general-purpose `action.py` effect prefix
(`divine_pleasure_max:`, `divine_climax_extension_stage:`, `divine_drain:`). The mastery
blanket-unlock does not reach these acts: `unlocked_act_keys_for`'s mastery branch excludes
`requires_divine_arts=True` acts, so a mastery holder without a divine-capable race owns the full
counter-gated catalogue but none of the three.

## Requirements

### Requirement: Three hand-built acts are registered, gated exclusively by requires_divine_arts, with no counter unlock
`world/skills/sexual_acts/divine.py`'s `DIVINE_ACTS` tuple SHALL contain the three `(SkillDef, SexualActDef)` pairs (`絕頂律令`, `時姦`, `神域搾取`), each declaring the shared eligibility requirement for race capability `can_use_divine_arts`, `unlock={}`, `target_part=None`, `resistible=True`, `actor_counters=()`, `participant_counters=()`.

#### Scenario: A non-divine race cannot cast any of the three acts regardless of counters
- **WHEN** an actor whose race's `can_use_divine_arts` is `False` attempts to cast `絕頂律令`, `時姦`,
  or `神域搾取`, regardless of that actor's lifetime counter values
- **THEN** `the shared identity-eligibility gate` rejects the cast with the named identity-eligibility rejection

#### Scenario: A divine-capable actor can cast all three from zero counters
- **WHEN** an actor whose race's `can_use_divine_arts` is `True` and who owns the skill carrying
  the shared eligibility requirement for race capability `can_use_divine_arts` for one of these three acts is read via `SkillHandler.owned_keys()`,
  with every one of that actor's lifetime counters at `0`
- **THEN** the corresponding skill key is present in the returned set; no counter threshold gates it

#### Scenario: SexualMasteryEffect ownership alone does not unlock any of the three
- **WHEN** an entity directly owns a skill carrying `SexualMasteryEffect` but has no divine-capable
  race
- **THEN** `unlocked_act_keys()`/`owned_keys()` include the full counter-gated catalogue but none of
  `絕頂律令`, `時姦`, or `神域搾取`

#### Scenario: The three pairs are hand-built
- **WHEN** `divine.py`'s construction code is inspected
- **THEN** none of the three pairs is constructed via `_act_family()`

#### Scenario: Later tuple extension does not disturb these three pairs
- **WHEN** `sexual-catalog-divine-mutators` extends the same tuple to seven entries
- **THEN** this requirement pins the identity and fields of these three pairs and is not read as limiting the tuple size; none of the three pairs is modified or removed

### Requirement: 絕頂律令 sets every target's pleasure to its ceiling and walks climax_phase to 進行中 in one cast, never touching the actor
`絕頂律令` SHALL declare `TargetSpec.AREA` and one effect, `divine_pleasure_max:絕頂律令`. Its handler SHALL explicitly exclude the acting entity from the entities it applies to — even if the acting entity is present in the resolved `targets` list — and for every remaining entity SHALL call the existing `_apply_pleasure_gain` function twice in sequence: once with `gain=100`, once with `gain=0`.

#### Scenario: A target starting below the climax threshold reaches 進行中 in one cast
- **WHEN** `絕頂律令` is cast at an `AREA` of targets, one of whom starts at `climax_phase="未達"` and
  `pleasure` below the `極限` band's floor
- **THEN** that target's `pleasure` becomes `100` and its `climax_phase` becomes `"進行中"` by the end
  of the cast's effect resolution

#### Scenario: A target already in 進行中 is unaffected in climax_phase but still reaches pleasure 100
- **WHEN** `絕頂律令` is cast at a target already at `climax_phase="進行中"`
- **THEN** that target's `pleasure` becomes `100` and its `climax_phase` remains `"進行中"`

#### Scenario: The acting entity's own pleasure is never touched
- **WHEN** `絕頂律令` is cast by an actor whose own `pleasure` is any value before the cast
- **THEN** the actor's `pleasure` is unchanged by the cast

#### Scenario: 絕頂律令 does not emit extreme_stimulus_applied
- **WHEN** `絕頂律令`'s `SkillDef.effects` is inspected
- **THEN** it contains no `sexual_event:` entry naming `extreme_stimulus_applied`, and casting it does
  not invoke `world.rules.sexual_transitions.apply_event`

#### Scenario: The actor is excluded even when present in the resolved targets list
- **WHEN** `絕頂律令` is cast with the `"all"` AREA shorthand, which includes the casting actor's own
  roster entry among the resolved `targets`
- **THEN** the actor's `pleasure` and `climax_phase` are unchanged by the cast, while every other
  entity in `targets` is processed normally

#### Scenario: A partial resist shrinks the AREA without erroring
- **WHEN** `絕頂律令` is cast at an `AREA` in which one target's resist contest resolves `resisted=True`
  and another's resolves `resisted=False`
- **THEN** the cast succeeds, the resisting target's `pleasure`/`climax_phase` are unchanged, and the
  non-resisting target's `pleasure` becomes `100` per the scenarios above

#### Scenario: The actor exclusion does not rely on upstream mechanisms
- **WHEN** the resolved `targets` list is produced
- **THEN** the `"all"` AREA shorthand does not exclude the actor, and `_step4b_sexual_resist_gate` does not remove an actor present in `targets`, so the handler's exclusion does not rely on either upstream mechanism

#### Scenario: No pleasure effect is declared for the acting entity
- **WHEN** `絕頂律令`'s effects are declared
- **THEN** it declares no `pleasure:` effect for the acting entity

#### Scenario: An empty or partial targets list is an ordinary outcome
- **WHEN** the `targets` list is empty or partial (from resisted targets being dropped before this handler runs)
- **THEN** it is handled as an ordinary outcome, never a rejection

### Requirement: 時姦 stages three climax extensions on every target in one cast, never touching the actor
`時姦` SHALL declare `TargetSpec.SINGLE` and one effect, `divine_climax_extension_stage:3`. Its
handler SHALL call `target.sexual.stage_climax_extension(3)` for every entity in the resolved
`targets` list (never the actor), and SHALL declare no `pleasure:` effect for either participant.

#### Scenario: Casting 時姦 stages exactly three extensions
- **WHEN** `時姦` is cast at a target whose `pending_climax_extension` is `0` before the cast
- **THEN** the target's `pending_climax_extension` becomes `3` immediately after the cast

#### Scenario: A target already in 進行中 consumes all three staged extensions across settlement points
- **WHEN** a target at `climax_phase="進行中"` is staged for `3` extensions via `時姦` and then three
  consecutive settlement points elapse with no further staging
- **THEN** `climax_settlement_action()` returns `"extend"` for each of the first three settlement
  points, consuming one staged extension per point, and the fourth settlement point (if the target is
  still `進行中`) returns `"end"`

#### Scenario: A target not currently in 進行中 has the staged count discarded at the next settlement point
- **WHEN** a target whose `climax_phase` is not `"進行中"` is staged for `3` extensions via `時姦`, and
  `climax_settlement_action()` is then called once for that target
- **THEN** the target's `pending_climax_extension` becomes `0` and no `"extend"` action is returned —
  the staged count is discarded, unchanged shipped `climax_settlement_action()` behaviour

#### Scenario: A successful resist empties the SINGLE target and the cast still succeeds
- **WHEN** `時姦` is cast at a target whose resist contest resolves `resisted=True`
- **THEN** the cast succeeds (the resist verdict is logged), no `pending_climax_extension` is staged on
  that target, and no `RejectedAction` is raised

### Requirement: 神域搾取 converts one target's pleasure one-to-one into the caster's MP, SP, and HP, then zeroes the target's pleasure
`神域搾取` SHALL declare `TargetSpec.SINGLE` and one effect, `divine_drain:神域搾取`. Its handler SHALL read the resolved target's `pleasure.value`, add that amount to the caster's `mp`, `sp`, and `hp` traits (each independently clamped at that trait's own maximum), then set the target's `pleasure` to `0`.

#### Scenario: A mid-range target pleasure value is drained one-to-one into all three caster resources
- **WHEN** `神域搾取` is cast at a target whose `pleasure` is `62`, by a caster whose `mp`, `sp`, and
  `hp` each have at least `62` of headroom below their maximum
- **THEN** the caster's `mp`, `sp`, and `hp` each increase by exactly `62`, and the target's `pleasure`
  becomes `0`

#### Scenario: Each drained resource clamps independently at its own maximum
- **WHEN** `神域搾取` is cast by a caster whose `mp` has only `5` headroom below its maximum but whose
  `sp` and `hp` both have at least `62` headroom, draining a target at `pleasure=62`
- **THEN** the caster's `mp` increases by exactly `5` (clamped at its maximum) while `sp` and `hp` each
  increase by the full `62`

#### Scenario: Draining a target at zero pleasure is a harmless no-op transfer
- **WHEN** `神域搾取` is cast at a target whose `pleasure` is already `0`
- **THEN** the caster's `mp`, `sp`, and `hp` are each unchanged, and the target's `pleasure` remains `0`

#### Scenario: A successful resist empties the sole target and the cast still succeeds, not rejects
- **WHEN** `神域搾取` is cast at a target whose resist contest resolves `resisted=True`, leaving
  `targets` empty by the time the drain handler runs
- **THEN** the cast succeeds (the resist verdict is logged), the caster's `mp`/`sp`/`hp` are unchanged,
  and no `RejectedAction` is raised

#### Scenario: Neither participant receives a pleasure effect
- **WHEN** `神域搾取`'s effects are declared
- **THEN** neither participant receives a `pleasure:` effect from this act

#### Scenario: An empty targets list is an ordinary no-op, never a rejection
- **WHEN** the drain handler runs with an empty `targets` list (a successfully-resisted sole target)
- **THEN** because `TargetSpec.SINGLE`'s "exactly one target" guarantee is enforced only at targeting time, before the resist gate runs, the empty list is treated as an ordinary no-op — never a rejection

#### Scenario: Rejection happens only for more than one entity
- **WHEN** the drain handler sees its `targets` list
- **THEN** it rejects only if `targets` contains more than one entity

### Requirement: The three new effect prefixes are line-agnostic dispatch-table entries
`action.py`'s `_EFFECT_HANDLERS` SHALL register `divine_pleasure_max:`, `divine_climax_extension_stage:`,
and `divine_drain:` as ordinary prefixes. Neither handler SHALL read the calling skill's identity eligibility or
otherwise branch on the calling `SkillDef`'s line.

#### Scenario: A hypothetical non-divine SkillDef naming one of the three prefixes is handled identically
- **WHEN** a hypothetical `SkillDef` outside the 神之秘法 line declares
  `effects=["divine_pleasure_max:test"]` and is cast
- **THEN** the handler applies the same two-call `_apply_pleasure_gain` sequence to its targets as it
  would for `絕頂律令`, without rejecting the cast for having no required divine race capability
