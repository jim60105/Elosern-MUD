# sexual-act-effects Delta Specification

## MODIFIED Requirements

### Requirement: The counter effect handler increments actor_counters on the actor and participant_counters on every other participant
`world/rules/action.py` SHALL register `sexual_counter:<act_key>` (surfaces
`frozenset({"sexual"})`, no required event context). For each name in
`SEXUAL_ACT_REGISTRY[act_key].actor_counters`, the handler SHALL stage one `PendingEffect` calling
the actor's corresponding sanctioned mutator (per the explicit attribute-to-mutator table, never a
derived string transform). For each name in `.participant_counters`, the handler SHALL stage one such
call for every entity in `participants(actor, targets)` other than the actor. A name in the
observer-gated counter set (`watched_count`, see the observer-gating requirement) SHALL be staged
only when `observers_present()` is true for the cast; a cast with no observer SHALL silently skip
that name while still staging every other declared counter.

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

#### Scenario: An unobserved cast skips the watched_count increment
- **WHEN** a `sexual_counter:<act_key>` effect resolves for an act declaring `watched_count` in
  `actor_counters` while no observer is present (an empty room, out of combat)
- **THEN** the actor's `watched_count` is unchanged and every other declared counter still
  increments

#### Scenario: An observed cast increments watched_count normally
- **WHEN** the same effect resolves while a co-located entity other than the actor is present
- **THEN** the actor's `watched_count` increases by exactly one

## ADDED Requirements

### Requirement: observers_present returns whether any entity besides the actor observes a cast
`world/rules/sexual_act_effects.py` SHALL define `observers_present(actor, targets, event_context)
-> bool`, a deterministic, no-create read: a cast whose target list contains an entity other than
the actor (an AREA cast's audience, or a SINGLE cast's partner) SHALL count as observed; otherwise
the co-located candidates SHALL be the battlefield roster's members when
`event_context["battlefield"]` is present, or the room's `LivingEntity` occupants when
`event_context["room"]` is present, and the cast SHALL be observed when any candidate is not the
actor. An event context carrying neither battlefield nor room SHALL read as unobserved.

#### Scenario: An AREA cast is observed by its audience
- **WHEN** `observers_present(actor, [target_a], event_context)` is called for an AREA cast with
  one non-actor target
- **THEN** it returns `True`

#### Scenario: A SELF cast alone in a room is unobserved
- **WHEN** `observers_present(actor, [actor], {"room": room})` is called for a room whose only
  `LivingEntity` occupant is the actor
- **THEN** it returns `False`

#### Scenario: A SELF cast with a co-located entity is observed
- **WHEN** the same call is made with one other `LivingEntity` in the room
- **THEN** it returns `True`

#### Scenario: A SELF cast on an empty battlefield is unobserved
- **WHEN** `observers_present(actor, [actor], {"battlefield": battlefield})` is called for a
  battlefield whose roster holds only the actor
- **THEN** it returns `False`

#### Scenario: A missing context reads as unobserved
- **WHEN** `observers_present(actor, [actor], {})` is called
- **THEN** it returns `False` without raising

### Requirement: watched_during_activity and watched_count are observer-gated; the gated names are declared as module constants
`world/rules/sexual_act_effects.py` SHALL declare `_OBSERVER_GATED_EVENTS` (containing exactly
`"watched_during_activity"`) and `_OBSERVER_GATED_COUNTERS` (containing exactly `"watched_count"`).
The actor-scoped event handler SHALL skip an event name in `_OBSERVER_GATED_EVENTS` when
`observers_present()` is false, and the counter handler SHALL skip a counter name in
`_OBSERVER_GATED_COUNTERS` under the same condition (see the modified counter requirement). A
structural test SHALL assert `_OBSERVER_GATED_EVENTS` is a subset of `_ACTOR_SCOPED_EVENTS` (the
actor-scoped event vocabulary in `world/skills/sexual_acts/_builder.py`), and separately that
`_OBSERVER_GATED_COUNTERS` is a subset of `SexualState`'s sanctioned lifetime counter attribute
names (the `_COUNTER_MUTATORS` key set).

#### Scenario: An unobserved cast skips the watched event
- **WHEN** an act declaring `watched_during_activity` is cast while no observer is present
- **THEN** `apply_event` is never invoked with `"watched_during_activity"` for that cast

#### Scenario: An observed cast emits the watched event
- **WHEN** the same act is cast while an observer is present
- **THEN** `apply_event` is invoked with `"watched_during_activity"` for the actor

### Requirement: sexual_event_actor:<name> applies the named event to the actor only
`world/rules/action.py` SHALL register the `sexual_event_actor:<name>` prefix (surfaces
`frozenset({"sexual"})`, no required event context). The handler SHALL stage one `PendingEffect`
calling `apply_event(actor, event_name, ...)` — never for any target — and SHALL apply the
observer-gating rule for a gated event name. The paired typed effect SHALL exist in
`world/skills/effects.py` and resolve through the same dispatch table.

#### Scenario: An actor-scoped event reaches the actor and no target
- **WHEN** an act declaring `sexual_event_actor:self_exposure` is cast against one target
- **THEN** `apply_event` is invoked with `"self_exposure"` for the actor exactly once and never for
  the target

#### Scenario: A gated actor-scoped event is skipped without an observer
- **WHEN** an act declaring `sexual_event_actor:watched_during_activity` is cast against one target
  in an empty room context
- **THEN** `apply_event` is never invoked with `"watched_during_activity"`
