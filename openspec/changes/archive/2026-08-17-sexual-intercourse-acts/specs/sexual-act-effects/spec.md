# sexual-act-effects Delta Specification

## MODIFIED Requirements

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

## ADDED Requirements

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
