# sexual-act-effects Specification

## Purpose

Define the runtime machinery that turns a catalog act's metadata into actual state mutation:
the pure helpers (`resolve_part`, `participants`, `compute_pleasure_gain`, the counter-to-mutator
table), the two new balance tables in `sexual_act_effects.yaml`, the `pleasure:`/`sexual_counter:`
effect prefixes and their `world/rules/action.py` handlers, and the direct replication of the two
arousal-coupled `sexual.yaml` cascade rules that `apply_event()`'s own snapshot cannot observe.

## Requirements

### Requirement: resolve_part collapses a Monster target or an undeclared part to the generic body-part channel
`world/rules/sexual_act_effects.py` SHALL define `resolve_part(entity, declared_part) ->
str`, returning `world.lore.sexual_vocab.GENERIC_BODY_PART` when `declared_part` is `None` or when
`entity` is a `Monster`, and returning `declared_part` unchanged otherwise.

#### Scenario: A non-Monster with a declared part resolves to that part
- **WHEN** `resolve_part(humanoid_entity, "乳房")` is called
- **THEN** it returns `"乳房"`

#### Scenario: A Monster resolves to the generic channel regardless of the declared part
- **WHEN** `resolve_part(monster_entity, "乳房")` is called
- **THEN** it returns `GENERIC_BODY_PART`

#### Scenario: An undeclared part resolves to the generic channel for any entity
- **WHEN** `resolve_part(humanoid_entity, None)` is called
- **THEN** it returns `GENERIC_BODY_PART`

### Requirement: participants resolves the actor-first, deduplicated participant list from an act's targets
`world/rules/sexual_act_effects.py` SHALL define `participants(actor, targets) -> list`, returning
the actor followed by every entity in `targets` not identical to the actor, in `targets`' order, with
no entity appearing twice.

#### Scenario: A solo act's targets already contain only the actor
- **WHEN** `participants(actor, [actor])` is called
- **THEN** it returns `[actor]`

#### Scenario: A two-person act's targets exclude the actor
- **WHEN** `participants(actor, [other])` is called
- **THEN** it returns `[actor, other]`

#### Scenario: An AREA act's targets never duplicate the actor even if included
- **WHEN** `participants(actor, [actor, ally, enemy])` is called
- **THEN** it returns `[actor, ally, enemy]` with `actor` appearing exactly once

### Requirement: compute_pleasure_gain scales base_pleasure by ratio, sensitivity, shame, and participant count
`world/rules/sexual_act_effects.py` SHALL define `compute_pleasure_gain(participant, part,
base_pleasure, ratio, participant_count) -> int`, returning `round(base_pleasure * ratio *
sensitivity_multiplier * shame_multiplier * participant_multiplier)`, where the sensitivity and shame
multipliers are read from `PLEASURE_CONFIG.sensitivity_multipliers`/`.shame_multipliers` (unchanged,
`pleasure-gauge`-owned) keyed by `participant.sexual.sensitivity[part].level` and
`participant.sexual.shame.level`, and the participant multiplier is read from this change's own
`sexual_act_effects.yaml` participant-count table.

#### Scenario: A neutral participant at 普通 sensitivity and 無 shame receives exactly the ratio-scaled base
- **WHEN** `compute_pleasure_gain(participant, part, base_pleasure=10, ratio=1.0, participant_count=1)`
  is called on a participant whose sensitivity for `part` is `普通` and whose `shame` is `無`
- **THEN** it returns `10` (both multipliers are `1.0` at their floor, per the shipped
  `sexual_pleasure.yaml`)

#### Scenario: Higher sensitivity increases the gain
- **WHEN** the same call is repeated with the participant's sensitivity for `part` raised to `極高`
- **THEN** the returned value is strictly greater than the 普通 case

#### Scenario: A ratio of zero returns zero regardless of multipliers
- **WHEN** `compute_pleasure_gain(participant, part, base_pleasure=10, ratio=0.0,
  participant_count=1)` is called
- **THEN** it returns `0`

### Requirement: sexual_act_effects.yaml declares the participant-count table and the climax extension threshold, validated at load
`world/rules/rulebook/sexual_act_effects.yaml` SHALL declare exactly `participant_multipliers`
(a mapping with exactly the keys `"1"`, `"2"`, and `"3+"`, each a positive finite number, in
non-descending order) and `climax_extension_threshold` (a positive integer). Loading SHALL fail
closed on any deviation.

#### Scenario: The shipped table loads without error
- **WHEN** `world/rules/rulebook/sexual_act_effects.yaml` is loaded at import
- **THEN** it succeeds and exposes both values

#### Scenario: A missing key fails closed
- **WHEN** a copy of the table omits `climax_extension_threshold`
- **THEN** loading it raises, naming the missing field

#### Scenario: A non-ascending participant multiplier table fails closed
- **WHEN** a copy of the table declares `"2"` lower than `"1"`
- **THEN** loading it raises

### Requirement: The pleasure effect handler resolves each participant's part and ratio by role, applies gain, and stages a climax extension when a 進行中 participant's computed gain meets threshold
`world/rules/action.py` SHALL register `pleasure:<act_key>` (surfaces `frozenset({"sexual"})`, no
required event context). `participant_count` SHALL be computed once per cast as
`len(participants(actor, targets))` and reused for every participant's gain computation. For the
acting entity, the handler SHALL compute gain using `part=resolve_part(actor,
SEXUAL_ACT_REGISTRY[act_key].actor_part)` and `ratio=SEXUAL_ACT_REGISTRY[act_key].
actor_pleasure_ratio`; for every other participant, using `part=resolve_part(participant,
SEXUAL_ACT_REGISTRY[act_key].target_part)` and `ratio=1.0`. For each entity in
`participants(actor, targets)`, the handler SHALL stage one `PendingEffect` that adds that
participant's computed gain to `entity.sexual.pleasure.base`. For any participant whose
`climax_phase.level` is `"進行中"` at apply time and whose **computed, pre-clamp** gain is at least
`climax_extension_threshold`, the same `PendingEffect` SHALL additionally call
`entity.sexual.stage_climax_extension()`.

#### Scenario: Every participant's pleasure increases by their own computed gain
- **WHEN** a `pleasure:<act_key>` effect resolves for an actor and one target
- **THEN** the actor's `pleasure` increases by the actor-ratio-scaled gain and the target's `pleasure`
  increases by the full gain, each independently

#### Scenario: The actor's gain uses actor_part; the target's gain uses target_part
- **WHEN** a `pleasure:<act_key>` effect resolves for an act declaring `actor_part="腰腹"` and
  `target_part="私處"`, against one target
- **THEN** the actor's gain is computed against `resolve_part(actor, "腰腹")` and the target's gain is
  computed against `resolve_part(target, "私處")` — never the other way around

#### Scenario: A qualifying gain on a 進行中 participant stages an extension
- **WHEN** a `pleasure:<act_key>` effect resolves against a participant whose `climax_phase.level` is
  `"進行中"` and whose computed gain is at least `climax_extension_threshold`
- **THEN** `entity.sexual.pending_climax_extension` increases by exactly one after the effect applies

#### Scenario: A qualifying gain that clamps at the pleasure ceiling still stages an extension
- **WHEN** the same participant's `pleasure` is already at `95` and the computed gain is `30` (which
  would clamp the applied delta to `5` at the `100` ceiling)
- **THEN** the extension still stages, because the trigger compares the uncapped computed gain, not
  the post-clamp applied delta

#### Scenario: A gain below threshold on a 進行中 participant does not stage an extension
- **WHEN** a `pleasure:<act_key>` effect resolves against a `進行中` participant whose computed gain
  is below `climax_extension_threshold`
- **THEN** `entity.sexual.pending_climax_extension` is unchanged

#### Scenario: A gain on a participant not currently in 進行中 never stages an extension
- **WHEN** a `pleasure:<act_key>` effect resolves against a participant whose `climax_phase.level` is
  not `"進行中"`, regardless of the computed gain's size
- **THEN** `entity.sexual.pending_climax_extension` is unchanged

### Requirement: The counter effect handler increments actor_counters on the actor and participant_counters on every other participant
`world/rules/action.py` SHALL register `sexual_counter:<act_key>` (surfaces
`frozenset({"sexual"})`, no required event context). For each name in
`SEXUAL_ACT_REGISTRY[act_key].actor_counters`, the handler SHALL stage one `PendingEffect` calling
the actor's corresponding sanctioned mutator (per the explicit attribute-to-mutator table, never a
derived string transform). For each name in `.participant_counters`, the handler SHALL stage one such
call for every entity in `participants(actor, targets)` other than the actor.

#### Scenario: An actor-only counter increments once on the actor and never on the target
- **WHEN** a `sexual_counter:<act_key>` effect resolves for an act whose `actor_counters` names one
  counter and whose `participant_counters` is empty, against one target
- **THEN** the actor's named counter increases by exactly one and the target's every counter is
  unchanged

#### Scenario: A symmetric counter increments on both sides through two independent grants
- **WHEN** a `sexual_counter:<act_key>` effect resolves for an act whose `actor_counters` and
  `participant_counters` both name the same counter, against one target
- **THEN** both the actor's and the target's named counter increase by exactly one

#### Scenario: A participant_counters entry applies to every non-actor participant in an AREA act
- **WHEN** a `sexual_counter:<act_key>` effect resolves for an AREA act against three targets
- **THEN** every one of the three targets' named `participant_counters` counters increases by exactly
  one, and the actor's copy of that counter is unaffected unless the same name also appears in
  `actor_counters`

### Requirement: The counter-to-mutator table is explicit and structurally verified against SexualState
`world/rules/sexual_act_effects.py` SHALL declare an explicit mapping from each of `SexualState`'s
eleven lifetime counter attribute names to its sanctioned mutator method name, and SHALL NOT derive a
mutator name from a counter attribute name by string transformation. A structural test SHALL assert
this table's key set equals the eleven counter attribute names exactly, and that every value names a
real, callable `SexualState` method.

#### Scenario: The table names the correct, non-mechanically-derivable mutator for climax_count
- **WHEN** the mutator table is inspected for the key `"climax_count"`
- **THEN** its value is `"record_climax_count"`, distinct from the pre-existing, unrelated
  `record_climax()` mutator for the separate `climax_today` counter

#### Scenario: Every table entry resolves to a real, callable method
- **WHEN** the structural test iterates every value in the mutator table
- **THEN** each names an attribute on `SexualState` that exists and is callable

#### Scenario: The table's key set matches SexualState's counters exactly
- **WHEN** the structural test compares the mutator table's keys against `SexualState`'s documented
  eleven counter attribute names
- **THEN** the two sets are identical

### Requirement: The pleasure handler replicates wetness_follows_arousal and the climax-phase progression directly, preserving the two-step 未達→接近→進行中 semantic
Applying a participant's computed pleasure gain SHALL, in the same `PendingEffect.apply()` call and in
this order: (1) capture the participant's arousal ordinal and whether `climax_phase.level` is
`"接近"`, both **before** mutating `pleasure`; (2) mutate `entity.sexual.pleasure.base`; (3) if the
arousal ordinal strictly increased, increment `entity.sexual.wetness.value` by exactly one; (4) if
`entity.sexual.arousal.level` is now `"極限"`, call `_apply_climax_phase_set(entity, "接近")`; (5) if
the pre-mutation capture found `climax_phase.level == "接近"`, call `_apply_climax_phase_set(entity,
"進行中")`. Neither call in steps 4-5 SHALL be gated by any condition beyond what
`_apply_climax_phase_set` itself already enforces (its own no-op on an invalid edge).

#### Scenario: A first-time crossing into 極限 moves climax_phase to 接近 only
- **WHEN** a participant's `climax_phase` is `"未達"` and a pleasure gain raises their arousal to the
  `極限` band for the first time
- **THEN** `climax_phase.level` becomes `"接近"` after the effect applies, not `"進行中"` — the
  進行中 transition requires a **separate**, later gain application while already at 接近

#### Scenario: A further gain while already at 接近 moves climax_phase to 進行中
- **WHEN** a participant's `climax_phase` is already `"接近"` (from a prior act) and a further
  pleasure gain resolves against them, regardless of whether arousal was already at `極限`
- **THEN** `climax_phase.level` becomes `"進行中"` after the effect applies

#### Scenario: An arousal-ordinal increase raises wetness by exactly one
- **WHEN** a pleasure gain raises a participant's arousal from one band to a higher band
- **THEN** `entity.sexual.wetness.value` increases by exactly one, clamped at its own configured
  bounds by `OrderedLevelTrait`'s own setter

#### Scenario: A gain that does not cross an arousal band leaves wetness unchanged
- **WHEN** a pleasure gain is applied but the participant's arousal ordinal is unchanged afterward
  (the gain was absorbed within the same band)
- **THEN** `entity.sexual.wetness.value` is unchanged by this effect

#### Scenario: The capture happens before mutation, not derived from post-mutation state
- **WHEN** `_apply_pleasure_gain`'s implementation is inspected
- **THEN** the arousal-ordinal and climax-phase captures are the first two statements, both reading
  `entity.sexual` before any line that mutates `entity.sexual.pleasure`

### Requirement: sexual_event:<name> entries in an act's effects reuse the existing handler and dispatch table unchanged
Every `sexual_event:<name>` string `_act_family()` appends to an act's `effects` (per
`sexual-act-registry`'s corresponding requirement) SHALL resolve through the existing
`_handle_sexual_event` handler and `SexualEventEffect` dispatch branch. The handler SHALL apply the
event to **every participant** of the cast — `participants(actor, targets)`, exactly like the
pleasure and counter handlers — except that an event name in `_builder.py`'s dedicated
`_LEGACY_TARGET_SCOPED_EVENTS` (initially exactly `{"stimulus_applied"}`, the legacy
`divine_sexual_arts` skill's declared event) SHALL remain target-scoped so a non-act skill's
declared event keeps its historic recipient semantics. `_LEGACY_TARGET_SCOPED_EVENTS` SHALL be a
set distinct from `_FORBIDDEN_SEXUAL_EVENTS`, which remains the act-catalog emission prohibition
alone.

#### Scenario: An act's declared event calls apply_event for every participant
- **WHEN** an act whose `sexual_events` includes `"breast_sex_performed"` is cast against one target
- **THEN** `apply_event` is invoked with event name `"breast_sex_performed"` for the actor and for
  the target — never the target alone

#### Scenario: The legacy skill's stimulus event stays target-scoped
- **WHEN** `divine_sexual_arts` (a non-registry skill declaring `sexual_event:stimulus_applied`)
  is cast against one target
- **THEN** `apply_event` is invoked with `"stimulus_applied"` for the target only, and the actor's
  sexual state is untouched by that event

#### Scenario: A SELF act's event still reaches exactly the actor
- **WHEN** a `TargetSpec.SELF` act whose `sexual_events` includes `"masturbation_climax"` is cast
- **THEN** `apply_event` is invoked with `"masturbation_climax"` for the actor exactly once

### Requirement: The pair-event handler resolves one sex-conditional event per cast and applies it to every participant
`world/rules/sexual_act_effects.py` SHALL define `pair_event_name(actor, targets, act) -> str |
None`: it reads each participant's `sex` (an absent or `None` value reading as
`world.lore.sex.DEFAULT_SEX`), builds the sorted two-member sex tuple, and returns the event name of
the first `act.pair_events` entry whose sex pair equals it, or `None` when no entry matches.
`world/rules/action.py` SHALL register the `act_pair_event:<act_key>` prefix (surfaces
`frozenset({"sexual"})`, no required event context): the handler SHALL look the act up in
`SEXUAL_ACT_REGISTRY` by the payload key, reject an absent act, resolve the event through
`pair_event_name`, stage no effect when the resolution is `None`, and otherwise stage one
`PendingEffect` calling `apply_event(participant, event)` for **every** participant of the cast.

#### Scenario: An opposite-sex cast resolves first_vaginal_penetration for both participants
- **WHEN** an act declaring the canonical three sex pairs is cast by an actor whose `sex` is
  `"female"` against a target whose `sex` is `"male"`
- **THEN** `pair_event_name` returns `"first_vaginal_penetration"`, and `apply_event` is invoked
  with that event for both the actor and the target

#### Scenario: A both-female cast resolves penetrative_sex_with_female
- **WHEN** the same act is cast by a `"female"` actor against a `"female"` target
- **THEN** `pair_event_name` returns `"penetrative_sex_with_female"`

#### Scenario: A cast involving an other/unknown party resolves no event
- **WHEN** the same act is cast by a `"male"` actor against a target whose `sex` is `"other"`
  (including any `Monster`, which defaults to `"other"`)
- **THEN** `pair_event_name` returns `None` and the handler stages no pending effect

#### Scenario: A pair-event effect naming an act absent from the registry is rejected defensively
- **WHEN** `act_pair_event:<key>` names an act absent from `SEXUAL_ACT_REGISTRY`
- **THEN** the action rejects with `RejectReason.EFFECT_RESOLUTION_FAILED` naming the effect string
